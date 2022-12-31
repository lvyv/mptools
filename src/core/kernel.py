#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 The CASICloud Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# pylint: disable=invalid-name
# pylint: disable=missing-docstring
import functools
import math
import multiprocessing
import os
import subprocess
import signal
import time
import json
import zmq

from core.ai import AiWorker
from core.mqtt import MqttWorker
from core.rest import RestWorker
from core.rtsp import RtspWorker
from core.tasks import TaskManage
from utils import bus, log, comn
from utils.config import ConfigSet
from utils.wrapper import proc_worker_wrapper, daemon_wrapper


def init_worker():
    # 忽略ctrl+c信号
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pass


class ProcSimpleFactory:
    """创建子进程对象工厂类.
    设置proc_worker_wrapper函数，作为所有子进程的入口.
    子进程分别在该函数中实例化进程对象，并启动主循环.
    """
    # 类变量，供类方法调用
    _web_process_handle = None  # rest 进程句柄
    _process_pool_handle = None  # rtsp,ai,mqtt 进程池句柄

    def __init__(self, nop):
        self.log = functools.partial(log.logger, f'ProcSimpleFactory')
        self._pool_size = nop
        if self._process_pool_handle is None:
            self._process_pool_handle = multiprocessing.Pool(processes=self._pool_size, initializer=init_worker)

    # 创建进程，每个进程的名称：NAME(PID)
    def create(self, worker_class, name, in_q=None, out_q=None, **kwargs):
        # 启用进程的数量
        _process_cnt = kwargs.get("cnt", 1)
        res = self._process_pool_handle.starmap_async(proc_worker_wrapper,
                                                      [(worker_class,
                                                        name,
                                                        in_q,
                                                        out_q,
                                                        kwargs)
                                                       for _ in range(_process_cnt)])
        return res

    @classmethod
    def teminate_rest(cls):
        if cls._web_process_handle:
            cls._web_process_handle.terminate()
            cls._web_process_handle.join()

    @classmethod
    def terminate(cls):
        if cls._process_pool_handle:
            cls._process_pool_handle.terminate()

    @classmethod
    def close(cls):
        if cls._process_pool_handle:
            cls._process_pool_handle.close()

    @classmethod
    def join(cls):
        if cls._process_pool_handle:
            cls._process_pool_handle.join()

    @classmethod
    def create_daemon(cls, worker_class, name, **kwargs):
        if cls._web_process_handle is None:
            name = f'{name}-{os.getpid()}'
            dp = multiprocessing.Process(target=daemon_wrapper, args=(worker_class, name), kwargs=kwargs)
            dp.daemon = True
            dp.start()
            cls._web_process_handle = dp
        return cls._web_process_handle


class FSM:
    """
    描述程序内部状态的有限状态机
    """
    STATUS_INITIAL = 0
    STATUS_FULL_SPEED = 1
    STATUS_ERROR = 2

    current_state_ = None

    def __init__(self):
        self.current_state_ = self.STATUS_INITIAL

    def test_status(self, criterion):
        return self.current_state_ == criterion

    def set_status(self, status):
        if status in [getattr(FSM, y) for y in [x for x in dir(self) if x.find('STATUS') == 0]]:
            self.current_state_ = status


class MainContext(bus.IEventBusMixin):
    """封装主进程模块类.
    完成所有子进程的创建，终止工作.
    完成对所有运行子进程的下发配置和查询状态（主要是事件总线和图片及向量队列）.
    """
    NUMBER_OF_PROCESSES = 12  # 进程池默认数量
    PIC_QUEUE_SIZE = 20  # 允许RTSP存多少帧图像给AI
    VEC_QUEUE_SIZE = 50  # 允许AI识别放多少结果到MQTT

    def __init__(self):
        # 日志输出偏函数
        self.log = functools.partial(log.logger, f'MAIN-{os.getpid()}')
        # 初始化MQ服务器句柄
        if MainContext.center_ is None:
            MainContext.center_ = bus.IEventBusMixin.get_center()
        # 初始化MQ服务器广播句柄
        if MainContext.broadcaster_ is None:
            MainContext.broadcaster_ = bus.IEventBusMixin.get_broadcaster()
        # call_rpc回调注册，供子进程调用
        MainContext.register(bus.CB_STARTUP_PPL, self.callback_start_pipeline)
        MainContext.register(bus.CB_STOP_PPL, self.callback_stop_pipeline)
        MainContext.register(bus.CB_GET_CFG, self.callback_get_cfg)
        MainContext.register(bus.CB_SET_CFG, self.callback_set_cfg)
        MainContext.register(bus.CB_SAVE_CFG, self.callback_save_cfg)
        MainContext.register(bus.CB_STOP_REST, self.callback_stop_rest)
        MainContext.register(bus.CB_SET_METRICS, self.callback_set_metrics)
        MainContext.register(bus.CB_GET_METRICS, self.callback_get_metrics)
        MainContext.register(bus.CB_PAUSE_RESUME_PIPE, self.callback_pause_resume_pipe)
        MainContext.register(bus.CB_UPDATE_PROCESS_STATE, self.callback_update_process_state)
        MainContext.register(bus.CB_MAPF_SOLVE, self.callback_mapf_solve)

        # 管理分配的任务：数据结构：{rtsp地址: 进程名称}，任务的粒度为一个通道
        # 数据示例: {'rtsp://127.0.0.1:7554/live/main': 'RTSP(23792)'}
        self._task_manage = TaskManage()
        # 进程间消息队列，供所有子进程消费
        self._queue_frame = multiprocessing.Manager().Queue(self.PIC_QUEUE_SIZE)
        self._queue_vector = multiprocessing.Manager().Queue(self.VEC_QUEUE_SIZE)
        # 保存所有进程（rest,rtsp,ai,mqtt）的所有监测指标数据：运行时间.rest基本能代表main自己.
        self._metrics = {}
        # 实例化工厂类
        self._factory = ProcSimpleFactory(self.NUMBER_OF_PROCESSES)
        # 初始化进程状态管理类
        self._status = FSM()

    def __enter__(self):
        self.log('********************  CASICLOUD V2V AI Dispatching Center  ********************')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.log(f'1.{exc_val}', level=log.LOG_LVL_ERRO, exc_info=(exc_type, exc_val, exc_tb))
        # -- Don't eat exceptions that reach here.
        return not exc_type

    def callback_start_pipeline(self, params):
        self.log(params, level=log.LOG_LVL_DBG)
        if self._status.test_status(FSM.STATUS_INITIAL):
            # 为了兼容旧接口，保留该函数
            self.start_v2v_pipeline_task()
            return {'reply': True}
        else:
            return {'reply': False}

    def callback_stop_pipeline(self, params):
        if params:
            pass
        if self._status.test_status(FSM.STATUS_FULL_SPEED):
            self.stop_v2v_pipeline_task()
            self._status.set_status(FSM.STATUS_INITIAL)
            return {'reply': True}
        else:
            return {'reply': False}

    def callback_set_channel_cfg(self, params):
        """
        对单个通道的配置文件进行更新，并通知指定的进程热加载配置
        params: {
          "rtsp_url": "rtsp://127.0.0.1:7554/live/main",
          "device_id": "34020000001320000001",
          "channel_id": "34020000001310000001",
          "name": "",
          "sample_rate": 1,
          "view_ports": ""
          }
        """
        _new_v2v_cfg_dict = ConfigSet.update_cfg(params)
        if _new_v2v_cfg_dict:
            # 配置更新事件发生，清空指定的任务.
            if self._task_manage:
                self._task_manage.clear_task(params['rtsp_url'])
            # 广播到流水线进程，指定的进程收到消息后，将重启.
            msg = bus.EBUS_SPECIAL_MSG_CHANNEL_CFG
            msg.update(params)
            # 广播配置信息给所有子进程
            self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)
            return {'reply': True, 'desc': f'已广播通知配置更新.{params["device_id"]}-{params["channel_id"]}'}
        else:
            return {'reply': False, 'desc': '不能识别的配置格式.'}

    def callback_set_cfg(self, params):
        """
        本函数为REST子进程设置配置信息而设计.

        Parameters
        ----------
        params:  Dict类型，可能是某单路视频通道配置，可能是全局配置.

        Returns
        -------
        Dict
            通用格式.
        Raises
        ----------
        RuntimeError
            待定.
        """
        _new_v2v_cfg_dict = ConfigSet.update_cfg(params)
        if _new_v2v_cfg_dict:
            # 暂存当前的进程数量
            _rtsp_num, _ai_num, _mqtt_num = self._task_manage.query_task_number()
            # 配置更新事件发生，需要对任务列表初始化，便于重新分配任务.
            if self._task_manage:
                self._task_manage.clear_task()
            # 广播到流水线进程，流水线上的所有进程将重启.
            msg = bus.EBUS_SPECIAL_MSG_CFG
            self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)

            # 检查配置文件中的RTSP通道数量
            _rtsp_list = _new_v2v_cfg_dict.get("rtsp_urls", None)
            _new_rtsp_num = 0 if _rtsp_list is None else len(_rtsp_list)
            self.fork_work_process(_new_rtsp_num, _rtsp_num, _ai_num, _mqtt_num)
            return {'reply': True, 'desc': '已广播通知配置更新.'}
        else:
            return {'reply': False, 'desc': '不能识别的配置格式.'}

    def callback_get_cfg(self, params):
        """
        本函数返回子进程对配置数据的请求.

        Parameters
        ----------
        params:  Dict类型.
            cmd键值为'get_cfg'或'get_task'.
            当为get_task时，assigned键值为子进程当前的任务(也是主进程以前派发的)，取值{}或v2v.cfg中rtsp_urls数组的1元素.
            source键值为子进程的名称唯一标识.
        Returns
        -------
        Dict
            通用格式.
        Raises
        ----------
        RuntimeError
            待定.
        """
        cmd = params.get('cmd', None)
        if cmd == 'get_cfg':  # 取v2v.cfg
            _cfg_dict = ConfigSet.get_v2v_cfg_obj()
            return _cfg_dict
        elif cmd == 'get_basecfg':  # 取baseconfig.cfg
            _cfg_dict = ConfigSet.get_base_cfg_obj()
            return _cfg_dict
        elif cmd == 'get_task':
            task = self._task_manage.assign_task(params['source'], params['assigned'])
            return task

    def callback_save_cfg(self, params):
        ret = False
        self.log(f"[MAIN] callback_save_cfg: {params}", level=log.LOG_LVL_DBG)
        cmd = params.get('cmd', None)
        if cmd == 'save_cfg':  # 取v2v.cfg
            ret = ConfigSet.save_v2v_cfg()
        elif cmd == 'save_basecfg':  # 取baseconfig.cfg
            ret = ConfigSet.save_base_cfg()
        return ret

    def callback_stop_rest(self, params):
        """
        本函数响应子进程对主进程的远程调用.

        Parameters
        ----------
        params:  在bus模块定义，Dict类型.

        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表.
        Raises
        ----------
        RuntimeError
            待定.
        """
        self.log(params)
        return {'reply': True, 'continue': False}

    def callback_set_metrics(self, params):
        """
        本函数响应子进程对所有监测指标的设置.
        把子进程上报的自己持续运行的时间等指标记录到一个数据结构中等备查.
        维护metrics的结构如下：
        :param : dict, {'application': 'RTSP(16380)','up': 39.5527503490448, ...}
        :return: dict, {'reply': True}
        """
        # 新的统计方案
        # 取pid
        _pid = comn.get_pid_from_process_name(params['application'])
        self._task_manage.update_process_info({'pid': _pid, 'up': params['up']})

        # 向下兼容
        pname = params['application']
        params.pop('application', None)
        if pname in self._metrics.keys():
            proc = self._metrics[pname]
            proc.update(params)
            self._metrics[pname] = proc
        else:
            self._metrics[pname] = params

        return {'reply': True}

    def callback_get_metrics(self, params):
        """
        本函数响应子进程对所有监测指标的获取.
        TODO:后续可选支持正则表达式查询.
        :param params: dict, {}或{'application': 'AI*'}
        :return: dict, {'reply': True, 'result_metrics': {'AI(0)-16380': {'up': 60},
                                                  'AI(2)-10104': {'up': 50.51580286026001, 'down': 1},
                                                  'AI(1)-16380': {'on': 0}},
                                       'result_tasks': {'rtsp://127.0.0.1/live': 'RTSP(0)-18368'}
                                                  }
        """
        if {} == params:
            ret = self._metrics
        else:
            ret = self._metrics
        return {'reply': True, 'result_metrics': ret, 'result_tasks': self._task_manage.dump_rtsp_list()}

    def callback_update_process_state(self, params):
        """
        响应子进程更新进程的状态
        :param: dict, {name: 'NAME(PID)', pid: pid, pre_state: ProcessState.number, new_state: ProcessState.number}
        """
        _ret = True
        self.log(f"callback_update_process_state: {params}", level=log.LOG_LVL_DBG)
        self._task_manage.update_process_info(params)
        return {'reply': _ret}

    def callback_mapf_solve(self, params):
        """
        调用外部MAPF算法库，求解最优路径。

        :param params: {'map_name': map_name,
                'tasks': '[{"s1":[1,1],"e1":[2,2]},{"s2":[10,10],"e2":[20,20]}]',
                'alg_name': alg_name }
        :return: {'reply': True, 'result': jsonobjects}
        """
        self.log(f"callback_mapf_solve: {params}", level=log.LOG_LVL_DBG)
        # 从操作系统层面调用MAPF算法，执行结果以json返回。
        tasks = params['tasks']
        task_list = json.loads(tasks)
        map_name = params['map_name']
        alg_name = params['alg_name']
        res = self.exec_cbs(alg_name, map_name, task_list)
        return {'reply': True, 'result': res}

    def callback_pause_resume_pipe(self, params):
        """
        本函数响应子进程rest停止或者重启某个管道的请求.
        :param params: dict, {'cmd': 'pause', 'deviceid': 'xxx', 'channelid': 'yyy'}
                             {'cmd': 'resume', 'deviceid': 'xxx', 'channelid': 'yyy'}
        :return: dict, {'reply': True}
        """
        msg = bus.EBUS_SPECIAL_MSG_STOP_RESUME_PIPE
        msg.update(params)
        self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)  # 广播启停某通道消息给所有子进程
        return {'reply': True, 'desc': f'广播启停某通道消息.{params["deviceid"]}-{params["channelid"]}'}

    def fork_restful_process(self, **kwargs):
        """
        本函数调用工厂类在主进程上下文环境启动rest子进程.
        rest子进程与其它子进程不一样，它与主进程是同生同死的，属于daemon子进程.

        Parameters
        ----------
        *kwargs:  port, ssl_keyfile, ssl_certfile.
            指定创建rest进程的端口，https.
        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表.
        Raises
        ----------
        RuntimeError
            待定.
        """
        res = self._factory.create_daemon(RestWorker, 'REST', **kwargs)
        return res

    def fork_work_process(self, expect_rtsp_num, now_rtsp_num, now_ai_num, now_mqtt_num) -> bool:
        """
        动态创建工作进程数量.
        expect_rtsp_num：配置文件中的RTSP通道数量
        now_rtsp_num：当前已经实例化的RTSP进程数量
        now_ai_num：当前已经实例化的AI进程数量
        now_mqtt_num：当前已经实例化的MQTT进程数量
        分配比例：
        rtsp:ai:mqtt = 1:0.5:0.1

        return true 创建成功，false 创建失败
        """
        _ret = False

        if expect_rtsp_num < 1:
            self.log(f"[MAIN] 需要创建的进程数量为0:{expect_rtsp_num}", level=log.LOG_LVL_WARN)
            return _ret
        # 读取配置文件
        _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
        # 读取当前的进程数量
        _rtsp_num, _ai_num, _mqtt_num = self._task_manage.query_task_number()
        # 根据策略，生成需要创建的工作进程数量
        _need_rtsp_num = expect_rtsp_num - now_rtsp_num
        _need_ai_num = math.ceil(expect_rtsp_num / 2) - now_ai_num
        _need_mqtt_num = math.ceil(expect_rtsp_num / 10) - now_mqtt_num
        # 校验
        if _need_rtsp_num < 0 or _need_ai_num < 0 or _need_mqtt_num < 0:
            self.log(f"[MAIN] 需要创建的进程数量值异常:{_need_rtsp_num},{_need_ai_num},{_need_mqtt_num}",
                     level=log.LOG_LVL_ERRO)
            return _ret

        # 创建工作进程
        for _ in range(_need_rtsp_num):
            self.__switch_on_process('RTSP')
        for _ in range(_need_ai_num):
            self.__switch_on_process('AI')

        mqtt = _v2v_cfg_dict['mqtt_svrs'][0]
        for _ in range(_need_mqtt_num):
            self.__switch_on_process('MQTT', mqtt_host=mqtt['mqtt_svr'], mqtt_port=mqtt['mqtt_port'],
                                     mqtt_cid=mqtt['mqtt_cid'], mqtt_usr=mqtt['mqtt_usr'], mqtt_pwd=mqtt['mqtt_pwd'],
                                     mqtt_topic=mqtt['mqtt_tp'], node_name=mqtt['node_name'])
        self.log(
            f'[MAIN] 创建RTSP进程数量: {_need_rtsp_num}, '
            f'创建AI进程数量: {_need_ai_num}, '
            f'创建MQTT进程数量: {_need_mqtt_num}')
        # 比对创建的进程数量和CPU核数量
        _cpu_core_num = os.cpu_count()
        _work_process_num = expect_rtsp_num + _need_ai_num + now_ai_num + _need_mqtt_num + now_mqtt_num
        self.log(f"[MAIN] CPU核数量:{_cpu_core_num}, 已创建进程数量:{_work_process_num}", level=log.LOG_LVL_INFO)
        return True

    def __switch_on_process(self, name, **kwargs):
        """
        本函数调用工厂类在主进程上下文环境启动所有子进程.
        创建包含指定数量进程的进程池，运行所有进程，并把所有进程执行结果合并为列表，返回.
        同时会将创建的进程池保存在列表中.

        Parameters
        ----------
        name : 区别不同子进程的名称.
            包括：RTSP，AI，MQTT.
        *kwargs: dict, None
            指定创建进程的数量，比如cnt=3, 表示创建和启动包含3个进程的进程池.
        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表.
        Raises
        ----------
        RuntimeError
            待定.
        """
        if 'RTSP' == name:
            res = self._factory.create(RtspWorker, name, None, self._queue_frame, **kwargs)
        elif 'AI' == name:
            res = self._factory.create(AiWorker, name, self._queue_frame, self._queue_vector, **kwargs)
        elif 'MQTT' == name:
            res = self._factory.create(MqttWorker, name, self._queue_vector, None, **kwargs)
        else:
            res = (None, None)
        return res

    def start_v2v_pipeline_task(self):
        # 标记工作状态
        self._status.set_status(FSM.STATUS_FULL_SPEED)

        _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
        # 读取当前的进程数量
        _rtsp_num, _ai_num, _mqtt_num = self._task_manage.query_task_number()
        # 获取配置文件中的RTSP通道数量
        _rtsp_list = _v2v_cfg_dict.get("rtsp_urls", None)
        _expect_rtsp_num = 0 if _rtsp_list is None else len(_rtsp_list)

        _ret = self.fork_work_process(_expect_rtsp_num, _rtsp_num, _ai_num, _mqtt_num)
        if _ret is True:
            self.log(f"[MAIN] start_v2v_pipeline_task success, expect rtsp: {_expect_rtsp_num}, now rtsp: {_rtsp_num}"
                     f" now ai: {_ai_num}, now mqtt: {_mqtt_num}",
                     level=log.LOG_LVL_DBG)
        else:
            self.log(f'[MAIN] start_v2v_pipeline_task failed', level=log.LOG_LVL_ERRO)

    def stop_v2v_pipeline_task(self):
        # 停止流水线子进程，需要对任务列表初始化，便于重新分配任务.
        if self._task_manage:
            self._task_manage.clear_task()
        # 微服务进程与主进程同时存在，不会停
        self.log("[MAIN] stop_v2v_pipeline_task()")
        msg = bus.EBUS_SPECIAL_MSG_STOP
        self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)
        return True

    def collect_procs_metrics(self, interval):
        """
        向子进程广播采集监测参数的要求.
        这个方式收集各子进程监测参数存在缺陷，一旦子进程暂停，会堆积大量的采集指令，造成后续命令排队.
        因此未启用该方法.
        :return:
        """
        while True:
            msg = bus.EBUS_SPECIAL_MSG_METRICS
            self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)  # 通知子进程
            time.sleep(interval)

    def exec_cbs(self, alg_name, map_name, tasks):
        """
        本函数调用操作系统函数subprocess，运行外部程序，并得到输出结果。

        :param alg_name: 算法程序的文件名称（操作系统层面）
        :param map_name: 地图文件名
        :param tasks: 任务的起点终点信息
        :return:
        """
        res = {}
        try:
            seed = time.time()
            cfgobj = ConfigSet.get_v2v_cfg_obj()
            map_dir = cfgobj['map_directory']
            command_dir = cfgobj['cmd_directory']
            tasksfile = f'{os.path.join(command_dir, "tasks", map_name)}.{seed}.scen'
            # 从tasks数据中，构造tasksfile
            os.makedirs(os.path.dirname(tasksfile), exist_ok=True)
            with open(tasksfile, 'w') as fi:
                fi.write(f'{len(tasks)}\r\n')
                for item in tasks:
                    fi.write(f'{item["s"][1]},{item["s"][0]},{item["e"][1]},{item["e"][0]},\r\n')

            shell_cmd = f'{command_dir}{alg_name} ' \
                        f'-m {map_dir}{map_name} ' \
                        f'-a {tasksfile} ' \
                        f'-o {command_dir}test-{seed}.csv ' \
                        f'--outputPaths={command_dir}paths-{seed}.json ' \
                        f'-k 5 -t 60'
            data = subprocess.check_output(shell_cmd)
            result = data.decode('utf-8').split('\r\n')
            if len(result) == 2:
                res = json.loads(result[1])
        except TypeError as err:
            self.log(err, level=log.LOG_LVL_ERRO)
        finally:
            return res

    def run(self):
        try:
            # 读取配置文件内容
            _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
            # 读取本地微服务的参数，也就是http服务
            _ms_cfg_dict = _v2v_cfg_dict['micro_service']
            (_ms_port, _ms_key, _ms_cer) = \
                (_ms_cfg_dict['http_port'], _ms_cfg_dict['ssl_keyfile'], _ms_cfg_dict['ssl_certfile'])
            # 创建工作进程
            # self.start_v2v_pipeline_task()
            # 启动1个Restful进程，提供微服务调用
            self.fork_restful_process(port=_ms_port, ssl_keyfile=_ms_key, ssl_certfile=_ms_cer)
            # 进入主循环，阻塞处理子进程之间的消息.
            self.log("[MAIN] Enter main event loop.", level=log.LOG_LVL_DBG)
            _main_start_time, _process_pool_time = time.time(), time.time()
            _log_interval = 15
            while True:
                # rpc远程调用服务启动，非阻塞等待外部事件出发状态改变
                try:
                    MainContext.rpc_service()
                except zmq.Again:
                    time.sleep(0.01)
                # 间隔输出程序运行状态
                if (time.time() - _main_start_time) >= _log_interval:
                    self.log(f"[MAIN DUMP] 视频截图队列:{self._queue_frame.qsize()}, "
                             f"识别结果队列:{self._queue_vector.qsize()}", level=log.LOG_LVL_INFO)
                    # 输出主进程管理的任务列表
                    _task_list = self._task_manage.dump_task_info()
                    self.log(f"[MAIN DUMP] 任务数量: {len(_task_list)}")
                    for _tk in _task_list:
                        self.log(f'     --> {_tk}', level=log.LOG_LVL_INFO)
                    # 各进程的详细数量
                    _rtsp, _ai, _mqtt = self._task_manage.query_task_number()
                    self.log(f"[MAIN DUMP] RTSP进程数量: {_rtsp}, AI进程数量: {_ai}, MQTT进程数量: {_mqtt}", level=log.LOG_LVL_INFO)
                    # 当没有任务时，加大日志输出间隔
                    _log_interval = 15 if len(_task_list) > 0 else 30
                    _main_start_time = time.time()
        except KeyboardInterrupt:
            self.log(f'[MAIN] Main process get ctrl+c', level=log.LOG_LVL_ERRO)
            self._factory.teminate_rest()
            self._factory.terminate()
        finally:
            self.log(f'[MAIN] Main process exit.')
            self._factory.close()
            self._factory.join()
