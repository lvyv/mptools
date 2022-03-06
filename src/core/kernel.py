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

"""
=========================
main module
=========================

Entry point of the project.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0
import copy
import multiprocessing
import functools
import signal
import os
import time

import zmq

from core.rtsp import RtspWorker
from core.ai import AiWorker
from core.mqtt import MqttWorker
from core.rest import RestWorker
from utils import bus, log
from utils.config import ConfigSet
from utils.wrapper import proc_worker_wrapper, daemon_wrapper


def init_worker():
    # 忽略ctrl+c信号
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pass


class ProcSimpleFactory:
    """创建子进程对象工厂类.
    设置proc_worker_wrapper函数，作为所有子进程的入口。
    子进程分别在该函数中实例化进程对象，并启动主循环。
    """
    # 类变量，供类方法调用
    _web_process_handle = None  # rest 进程句柄
    _process_pool_handle = None  # rtsp,ai,mqtt 进程池句柄

    def __init__(self, nop):
        self.log = functools.partial(log.logger, f'ProcSimpleFactory')
        self._pool_size = nop

    # 创建进程，每个进程的名称：NAME(PID)
    def create(self, worker_class, name, in_q=None, out_q=None, **kwargs):
        if self._process_pool_handle is None:
            self._process_pool_handle = multiprocessing.Pool(processes=self._pool_size, initializer=init_worker)
        # 默认启用进程的数量
        default_cnt = 1
        for key, value in kwargs.items():
            if key == 'cnt':
                default_cnt = value
                break
        res = self._process_pool_handle.starmap_async(proc_worker_wrapper,
                                                      [(worker_class,
                                                        f'{name}',
                                                        in_q, out_q,
                                                        kwargs)
                                                       for idx in range(default_cnt)])
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
    完成所有子进程的创建，终止工作。
    完成对所有运行子进程的下发配置和查询状态（主要是事件总线和图片及向量队列）。
    """
    NUMBER_OF_PROCESSES = 12    # 进程池默认数量
    PIC_QUEUE_SIZE = 20  # 允许RTSP存多少帧图像给AI，避免AI算不过来，RTSP把内存给撑死
    VEC_QUEUE_SIZE = 50  # 允许AI识别放多少结果到MQTT，避免MQTT死了，AI撑死内存

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

        # 管理分配的任务：数据结构：{rtsp地址: 进程名称}，任务的粒度为一个通道
        # 数据示例: {'rtsp://127.0.0.1:7554/live/main': 'RTSP(23792)'}
        self._task_dict = {}
        # 进程间消息队列
        self._queue_frame = multiprocessing.Manager().Queue(self.PIC_QUEUE_SIZE)  # Is JoinableQueue better?
        self._queue_vector = multiprocessing.Manager().Queue(self.VEC_QUEUE_SIZE)  # mqtt阻塞
        # 进程间共享数据，用于标记是否该退出子进程，[False, False],第一个元素有效，第二个元素备用.
        # 各个子进程中读取该状态，判断是否该立即退出进程
        self._process_share_data = multiprocessing.Manager().list([False, False])

        # 保存所有进程（rest,rtsp,ai,mqtt）的所有监测指标数据：运行时间。rest基本能代表main自己。
        self.metrics_ = {}
        # 实例化工厂类
        self.factory_ = ProcSimpleFactory(self.NUMBER_OF_PROCESSES)
        # 初始化进程状态管理类
        self.status_ = FSM()

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
        if self.status_.test_status(FSM.STATUS_INITIAL):
            _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
            self.start_v2v_pipeline_task(_v2v_cfg_dict)
            self.status_.set_status(FSM.STATUS_FULL_SPEED)
            return {'reply': True}
        else:
            return {'reply': False}

    def callback_stop_pipeline(self, params):
        self.log(params, level=log.LOG_LVL_DBG)
        if self.status_.test_status(FSM.STATUS_FULL_SPEED):
            self.stop_v2v_pipeline_task()
            self.status_.set_status(FSM.STATUS_INITIAL)
            return {'reply': True}
        else:
            return {'reply': False}

    def callback_set_cfg(self, params):
        """
        本函数为REST子进程设置配置信息而设计。

        Parameters
        ----------
        params:  Dict类型，可能是某单路视频通道配置，可能是全局配置。

        Returns
        -------
        Dict
            通用格式。
        Raises
        ----------
        RuntimeError
            待定.
        """
        _new_v2v_cfg_dict = ConfigSet.update_cfg(params)
        if _new_v2v_cfg_dict:
            # 配置更新事件发生，需要对任务列表初始化，便于重新分配任务。
            self.clear_tasks()
            # FIXME: 最好支持单个通道重启
            # 广播到流水线进程，所有流水线上的所有进程将重启。
            msg = bus.EBUS_SPECIAL_MSG_CFG
            self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)  # 广播配置信息给所有子进程
            return {'reply': True, 'desc': '已广播通知配置更新。'}
        else:
            return {'reply': False, 'desc': '不能识别的配置格式。'}

    def callback_get_cfg(self, params):
        """
        本函数返回子进程对配置数据的请求。

        Parameters
        ----------
        params:  Dict类型。
            cmd键值为'get_cfg'或'get_task'。
            当为get_task时，assigned键值为子进程当前的任务(也是主进程以前派发的)，取值{}或v2v.cfg中rtsp_urls数组的1元素.
            source键值为子进程的名称唯一标识。
        Returns
        -------
        Dict
            通用格式。
        Raises
        ----------
        RuntimeError
            待定.
        """
        cmd = params['cmd']
        if cmd == 'get_cfg':    # 取v2v.cfg
            _cfg_dict = ConfigSet.get_v2v_cfg_obj()
            return _cfg_dict
        elif cmd == 'get_basecfg':  # 取baseconfig.cfg
            _cfg_dict = ConfigSet.get_base_cfg_obj()
            return _cfg_dict
        elif cmd == 'get_task':
            task = self.assign_task(params['source'], params['assigned'])
            return task

    def callback_save_cfg(self, params):
        ret = False
        self.log(f"Save cfg cb: {params}", level=log.LOG_LVL_DBG)
        cmd = params['cmd']
        if cmd == 'save_cfg':    # 取v2v.cfg
            ret = ConfigSet.save_v2v_cfg()
        elif cmd == 'save_basecfg':  # 取baseconfig.cfg
            ret = ConfigSet.save_base_cfg()
        return ret

    def callback_stop_rest(self, params):
        """
        本函数响应子进程对主进程的远程调用。

        Parameters
        ----------
        params:  在bus模块定义，Dict类型。

        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表。
        Raises
        ----------
        RuntimeError
            待定.
        """
        self.log(params)
        return {'reply': True, 'continue': False}

    def callback_set_metrics(self, params):
        """
        本函数响应子进程对所有监测指标的设置。
        把子进程上报的自己持续运行的时间等指标记录到一个数据结构中等备查。
        维护metrics的结构如下：
        {'RTSP(0)-16380': {'up': 60},
         'AI(2)-10104': {'up': 50.51580286026001, 'down': 1},
         'MQTT(1)-16380': {'on': 0}}

        :param params: dict, {'application': 'RTSP(0)-16380','up': 39.5527503490448, ...}, proc是固定的，除up外还可能增加其它键值。
        :return: dict, {'reply': True}
        """
        # self.log(f'callback_set_metrics: {params}')

        pname = params['application']
        params.pop('application', None)
        if pname in self.metrics_.keys():
            proc = self.metrics_[pname]
            proc.update(params)
            self.metrics_[pname] = proc
        else:
            self.metrics_[pname] = params
        return {'reply': True}

    def callback_get_metrics(self, params):
        """
        本函数响应子进程对所有监测指标的获取。
        TODO:后续可选支持正则表达式查询。
        :param params: dict, {}或{'application': 'AI*'}
        :return: dict, {'reply': True, 'result_metrics': {'AI(0)-16380': {'up': 60},
                                                  'AI(2)-10104': {'up': 50.51580286026001, 'down': 1},
                                                  'AI(1)-16380': {'on': 0}},
                                       'result_tasks': {'rtsp://127.0.0.1/live': 'RTSP(0)-18368'}
                                                  }
        """
        # self.log(f'callback_get_metrics: {params}')
        if {} == params:
            ret = self.metrics_
        else:
            ret = self.metrics_
        return {'reply': True, 'result_metrics': ret, 'result_tasks': self._task_dict}

    def callback_pause_resume_pipe(self, params):
        """
        本函数响应子进程rest停止或者重启某个管道的请求。
        :param params: dict, {'cmd': 'pause', 'deviceid': 'xxx', 'channelid': 'yyy'}
                             {'cmd': 'resume', 'deviceid': 'xxx', 'channelid': 'yyy'}
        :return: dict, {'reply': True}
        """
        # self.log(params)
        msg = bus.EBUS_SPECIAL_MSG_STOP_RESUME_PIPE
        msg.update(params)
        self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)  # 广播启停某通道消息给所有子进程
        return {'reply': True, 'desc': '广播启停某通道消息给所有子进程。'}

    def fork_restful_process(self, **kwargs):
        """
        本函数调用工厂类在主进程上下文环境启动rest子进程。
        rest子进程与其它子进程不一样，它与主进程是同生同死的，属于daemon子进程。

        Parameters
        ----------
        *kwargs:  port, ssl_keyfile, ssl_certfile。
            指定创建rest进程的端口，https。
        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表。
        Raises
        ----------
        RuntimeError
            待定.
        """
        res = self.factory_.create_daemon(RestWorker, 'REST', **kwargs)
        return res

    def switch_on_process(self, name, **kwargs):
        """
        本函数调用工厂类在主进程上下文环境启动所有子进程。
        创建包含指定数量进程的进程池，运行所有进程，并把所有进程执行结果合并为列表，返回。
        同时会将创建的进程池保存在列表中。

        Parameters
        ----------
        name : 区别不同子进程的名称。
            包括：RTSP，AI，MQTT。
        *kwargs: dict, None
            指定创建进程的数量，比如cnt=3, 表示创建和启动包含3个进程的进程池。
        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表。
        Raises
        ----------
        RuntimeError
            待定.
        """
        if 'RTSP' == name:
            res = self.factory_.create(RtspWorker, name, None, self._queue_frame, **kwargs)
        elif 'AI' == name:
            res = self.factory_.create(AiWorker, name, self._queue_frame, self._queue_vector, **kwargs)
        elif 'MQTT' == name:
            res = self.factory_.create(MqttWorker, name, self._queue_vector, None, **kwargs)
        else:
            res = (None, None)
        return res

    def start_v2v_pipeline_task(self, cfg):
        # 复位子进程退出状态
        self._process_share_data[0] = False
        try:
            # 根据通道列表启动每个通道的rtsp->ai->mqtt处理进程
            for channel in cfg['rtsp_urls']:
                # 不提供cnt=x参数，缺省1个通道启1个取RTSP流进程
                self.switch_on_process('RTSP', rtsp_params=channel, share_list=self._process_share_data)
                # 取AI的识别结果比较慢，安排2个进程处理一个通道，实际AI子进程处理所有IPC的数据
                self.switch_on_process('AI', cnt=2, share_list=self._process_share_data)
                # 上传文件，安排1个进程处理，不要多个进程，防止服务器端互相踢，实际MQTT子进程处理所有的结果数据
                mqtt = cfg['mqtt_svrs'][0]
                self.switch_on_process('MQTT', cnt=1, mqtt_host=mqtt['mqtt_svr'], mqtt_port=mqtt['mqtt_port'],
                                       mqtt_cid=mqtt['mqtt_cid'], mqtt_usr=mqtt['mqtt_usr'], mqtt_pwd=mqtt['mqtt_pwd'],
                                       mqtt_topic=mqtt['mqtt_tp'], node_name=mqtt['node_name'], share_list=self._process_share_data)
            self.log(f"Start v2v pipeline, total channel: {len(cfg['rtsp_urls'])}", level=log.LOG_LVL_DBG)
        except KeyError as err:
            self.log(f'start_v2v_pipeline_task failed: {err}', level=log.LOG_LVL_ERRO)

    def stop_v2v_pipeline_task(self):
        # 停止流水线子进程，需要对任务列表初始化，便于重新分配任务。
        self.clear_tasks()
        # 标记退出状态，各个子进程可查询
        self._process_share_data[0] = True
        # 微服务进程与主进程同时存在，不会停
        self.log("Broadcast event: --> EBUS_SPECIAL_MSG_STOP")
        msg = bus.EBUS_SPECIAL_MSG_STOP
        self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)
        return True

    def collect_procs_metrics(self, interval):
        """
        向子进程广播采集监测参数的要求。
        这个方式收集各子进程监测参数存在缺陷，一旦子进程暂停，会堆积大量的采集指令，造成后续命令排队。
        因此未启用该方法。
        :return:
        """
        while True:
            msg = bus.EBUS_SPECIAL_MSG_METRICS
            self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)  # 通知子进程
            time.sleep(interval)

    def clear_tasks(self):
        """
        清除所有任务列表。在stop pipeline的时候，配置下发设置的时候，需要调用。

        Parameters
        ----------

        Returns
        -------

        Raises
        ----------
        """
        self._task_dict.clear()
        self._task_dict = {}

    def get_pre_assigned_cfg(self, source):
        """
        如果某个子进程被分派了任务又重新申请，则还是返回原来任务给它。
        如果这个子进程没有出现在任务注册表中，返回空。

        Parameters
        ----------
        source : 子进程的名称标识。

        Returns
        -------

        Raises
        ----------
        """
        _task_dict = None
        _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()  # 待分配任务表
        # 遍历主进程管理的任务列表
        for _rtsp_url, _process_name in self._task_dict.items():
            if _process_name == source:  # 这个子进程注册过吗？
                for _channel_dict in _v2v_cfg_dict['rtsp_urls']:
                    # 根据任务中的url地址重新取配置信息
                    if _channel_dict and _rtsp_url == _channel_dict['rtsp_url']:  # 注册的这个url对应的配置取出来
                        _task_dict = _channel_dict
                        break
        return _task_dict

    def assign_task(self, source, assigned=None):
        """
        根据子进程的请求，返回一个含url的任务配置信息。如果发现没有可分配的任务，则返回[]。

        Parameters
        ----------
        source:  子进程名称，可唯一标识子进程。
        assigned: 子进程此前分配的任务。

        Returns
        -------
        Dict
            带全部配置信息，但rtsp_urls数组中只有一个元素rtsp_url。
        Raises
        ----------
        RuntimeError
            待定.
        """
        _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
        _v2v_cfg_dict = copy.deepcopy(_v2v_cfg_dict)
        _new_task_dict = None
        # 遍历所有通道
        for channel in _v2v_cfg_dict['rtsp_urls']:
            if not channel:
                continue
            _rtsp_url = channel['rtsp_url']
            # 如果_task_dict中有这个值，说明有人先注册处理这个任务，再找下个待分配任务。
            if _rtsp_url in self._task_dict.keys():
                continue
            # 以前没分配过任务，或者分配过，但新的配置中没有那个任务了，均可以分配新的url
            _new_task_dict = self.get_pre_assigned_cfg(source)
            if _new_task_dict is None:
                _new_task_dict = channel
                self._task_dict.update({_rtsp_url: source})
                self.log(f'Assign new task --> :{_rtsp_url}: {source}', level=log.LOG_LVL_INFO)
                break
        if _new_task_dict:
            _v2v_cfg_dict['rtsp_urls'] = [_new_task_dict]
        else:
            _v2v_cfg_dict['rtsp_urls'] = []
        return _v2v_cfg_dict

    def run(self):
        """
        主进程入口 —— 读取配置，启动rest后台服务进程，数据采集线程，进入子进程之间通信机制的主事件循环。
        :return: 无。
        """
        try:
            # 读取配置文件内容
            _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
            _ms_cfg_dict = _v2v_cfg_dict['micro_service']
            (_ms_port, _ms_key, _ms_cer) = \
                (_ms_cfg_dict['http_port'], _ms_cfg_dict['ssl_keyfile'], _ms_cfg_dict['ssl_certfile'])

            # 启动1个Restful进程，提供微服务调用
            self.fork_restful_process(port=_ms_port, ssl_keyfile=_ms_key, ssl_certfile=_ms_cer)

            # 阻塞处理子进程之间的消息。
            self.log("Enter main event loop.", level=log.LOG_LVL_DBG)
            _main_start_time, _process_pool_time = time.time(), time.time()
            while True:
                # rpc远程调用服务启动，非阻塞等待外部事件出发状态改变
                try:
                    MainContext.rpc_service()
                except zmq.Again as e:
                    time.sleep(0.01)
                # 每隔10秒输出程序运行状态
                if (time.time() - _main_start_time) >= 10:
                    self.log(f"Frame queue size: {self._queue_frame.qsize()}", level=log.LOG_LVL_INFO)
                    self.log(f"Mqtt  queue size: {self._queue_vector.qsize()}", level=log.LOG_LVL_INFO)
                    # TODO: 监控进程池的运行情况，RTSP,AI,MQTT进程数量，以及所在阶段(startup, mainloop)
                    # 输出主进程管理的任务列表
                    self.log(f"Task list: {self._task_dict}", level=log.LOG_LVL_INFO)
                    _main_start_time = time.time()
        except KeyboardInterrupt as err:
            self.log(f'Main process get ctrl+c : {err}', level=log.LOG_LVL_ERRO)
            self.factory_.teminate_rest()
            self.factory_.terminate()
        finally:
            self.log(f'Main process exit.')
            self.factory_.close()
            self.factory_.join()
