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

import multiprocessing
import functools
import os
from core.rtsp import RtspWorker
from core.ai import AiWorker
from core.mqtt import MqttWorker
from core.rest import RestWorker
from utils import bus, log, config


# class RestWorker:
#     def __init__(self, name, evt_bus, in_q=None, out_q=None, up_evt=None, down_evt=None, **kwargs):
#         self.log = functools.partial(log.logger, f'{name}')
#
#     def run(self):
#         self.log(f'running...')
#         return 0


# -- Process Wrapper
def daemon_wrapper(proc_worker_class, name, **kwargs):
    pid = os.getpid()
    proc_worker = proc_worker_class(f'{name}-{pid}', None, None, kwargs)
    return proc_worker.run()


def proc_worker_wrapper(proc_worker_class, name, in_q=None, out_q=None, dicts=None, **kwargs):
    """
    子进程的入口点。

    :param proc_worker_class: 类名。
    :param name: 对象名。
    :param in_q: 输入数据队列，子进程之间数据通道。
    :param out_q: 输出数据队列，子进程之间数据通道。
    :param dicts: 额外参数。
    :param kwargs: 其它参数。
    :return: 子进程退出码：0为正常，-1为错误。
    """
    pid = os.getpid()
    proc_worker = proc_worker_class(f'{name}-{pid}', in_q, out_q, dicts, **kwargs)
    return proc_worker.run()


class ProcSimpleFactory:
    """创建子进程对象工厂类.

    设置proc_worker_wrapper函数，作为所有子进程的入口。
    子进程分别在该函数中实例化进程对象，并启动主循环。
    """
    rest_ = None    # rest 进程句柄

    def __init__(self, nop):
        self.log = functools.partial(log.logger, f'ProcSimpleFactory')
        self.pool_ = multiprocessing.Pool(processes=nop)

    def create(self, worker_class, name, in_q=None, out_q=None, **kwargs):
        default_cnt = 1
        for key, value in kwargs.items():
            if key == 'cnt':
                default_cnt = value
                break

        res = self.pool_.starmap_async(proc_worker_wrapper,
                                       [(worker_class, f'{name}({idx})', in_q, out_q, kwargs)
                                        for idx in range(default_cnt)])
        return res

    @classmethod
    def create_daemon(cls, worker_class, name, **kwargs):
        if cls.rest_ is None:
            dp = multiprocessing.Process(target=daemon_wrapper, args=(worker_class, name), kwargs=kwargs)
            dp.daemon = True
            dp.start()
            cls.rest_ = dp
        return cls.rest_


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

    NUMBER_OF_PROCESSES = 20

    def callback_start_pipeline(self, params):
        self.log(params)
        if self.status_.test_status(FSM.STATUS_INITIAL):
            self.start_procs(self.cfg_)
            self.status_.set_status(FSM.STATUS_FULL_SPEED)
            return {'reply': True}
        else:
            return {'reply': False}

    def callback_stop_pipeline(self, params):
        self.log(params)
        if self.status_.test_status(FSM.STATUS_FULL_SPEED):
            self.stop_procs()
            self.status_.set_status(FSM.STATUS_INITIAL)
            return {'reply': True}
        else:
            return {'reply': False}

    def callback_get_cfg(self, params):
        self.log(params)
        if self.cfg_:
            return self.cfg_
        else:
            return {'reply: False'}

    def __init__(self, bustopic=bus.EBUS_TOPIC_BROADCAST):
        self.log = functools.partial(log.logger, f'MAIN')
        if MainContext.center_ is None:
            MainContext.center_ = bus.IEventBusMixin.get_center()
        if MainContext.broadcaster_ is None:
            MainContext.broadcaster_ = bus.IEventBusMixin.get_broadcaster()
        # call_rpc回调注册
        MainContext.register(bus.CB_STARTUP_PPL, self.callback_start_pipeline)
        MainContext.register(bus.CB_STOP_PPL, self.callback_stop_pipeline)
        MainContext.register(bus.CB_GET_CFG, self.callback_get_cfg)

        self.cfg_ = None                                            # 配置文件内容
        self.pic_q_ = multiprocessing.Manager().Queue()  # Is JoinableQueue better?
        self.vec_q_ = multiprocessing.Manager().Queue()

        self.queues_ = []                       # 子进程间数据传递队列
        self.queues_.append(self.pic_q_)        # 图片
        self.queues_.append(self.vec_q_)        # 识别结果

        self.factory_ = ProcSimpleFactory(self.NUMBER_OF_PROCESSES)
        self.status_ = FSM()

    def __enter__(self):
        self.log('********************  CASICLOUD AI METER services  ********************')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.log(f"Exception: {exc_val}", level=log.LOG_LVL_ERRO, exc_info=(exc_type, exc_val, exc_tb))
        # -- Don't eat exceptions that reach here.
        return not exc_type

    def rest_api(self, **kwargs):
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

    def switchon_procs(self, name, **kwargs):
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
            res = self.factory_.create(RtspWorker, name, None, self.pic_q_, **kwargs)
        elif 'AI' == name:
            res = self.factory_.create(AiWorker, name, self.pic_q_, self.vec_q_, **kwargs)
        elif 'MQTT' == name:
            res = self.factory_.create(MqttWorker, name, self.vec_q_, None, **kwargs)
        else:
            res = (None, None)

        return res

    def start_procs(self, cfg):
        # 'rtsp://admin:admin123@192.168.101.114:554/cam/realmonitor?channel=1&subtype=0'
        # 'rtsp://admin:admin123@192.168.101.114:554/cam/playback?channel=1&subtype=0&starttime=2021_08_03_11_50_00'
        # 启动进程
        for channel in cfg['rtsp_urls']:
            self.switchon_procs('RTSP', rtsp_url=channel, sample_rate=1)    # 不提供cnt=x参数，缺省1个通道启1个进程
            num = 3                                                         # AI比较慢，安排两个进程处理
            self.switchon_procs('AI', cnt=num)
            num = 2                                                         # MQTT比较慢，上传文件，安排两个进程处理
            mqtt = cfg['mqtt_svrs'][0]
            self.switchon_procs('MQTT', cnt=num,
                                mqtt_host=mqtt['mqtt_svr'], mqtt_port=mqtt['mqtt_port'], mqtt_topic=mqtt['mqtt_tp'])

    def stop_procs(self):
        msg = bus.EBUS_SPECIAL_MSG_STOP
        self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)   # 微服务进程与主进程同时存在，不会停

        return True

    def run(self, path2cfg):
        self.cfg_ = config.load_json(path2cfg)                                          # 读取配置文件内容
        api = self.cfg_['micro_service']
        (ap, key, cer) = (api['http_port'], api['ssl_keyfile'], api['ssl_certfile'])    # 配置微服务
        self.rest_api(port=ap, ssl_keyfile=key, ssl_certfile=cer)                       # 启动1个Rest进程，提供微服务调用

        loop = True
        while loop:
            # msg = self.recv_cmd(bus.EBUS_TOPIC_MAIN)
            MainContext.rpc_service()                               # rpc远程调用服务启动，阻塞等待外部事件出发状态改变
