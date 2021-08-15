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
from utils import bus, log


# class RestWorker:
#     def __init__(self, name, evt_bus, in_q=None, out_q=None, up_evt=None, down_evt=None, **kwargs):
#         self.log = functools.partial(log.logger, f'{name}')
#
#     def run(self):
#         self.log(f'running...')
#         return 0


# -- Process Wrapper
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


class MainContext(bus.IEventBusMixin):
    """封装主进程模块类.

    完成所有子进程的创建，终止工作。
    完成对所有运行子进程的下发配置和查询状态（主要是事件总线和图片及向量队列）。
    """

    NUMBER_OF_PROCESSES = 20

    def __init__(self, bustopic):
        self.log = functools.partial(log.logger, f'MAIN')
        self.beeper_ = bus.IEventBusMixin.get_center(rtimeout=1)
        self.bus_topic_ = bustopic

        self.pic_q_ = multiprocessing.Manager().Queue()  # Is JoinableQueue better?
        self.vec_q_ = multiprocessing.Manager().Queue()

        self.queues_ = []  # 子进程间数据队列
        self.queues_.append(self.pic_q_)
        self.queues_.append(self.vec_q_)

        self.factory_ = ProcSimpleFactory(self.NUMBER_OF_PROCESSES)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.log(f"Exception: {exc_val}", level=log.LOG_LVL_ERRO, exc_info=(exc_type, exc_val, exc_tb))

        # self._stopped_procs_result = self.stop_procs()
        # self._stopped_queues_result = self.stop_queues()

        # -- Don't eat exceptions that reach here.
        return not exc_type

    def start_procs(self, name, **kwargs):
        """
        本函数调用工厂类在主进程上下文环境启动所有子进程。
        创建包含指定数量进程的进程池，运行所有进程，并把所有进程执行结果合并为列表，返回。
        同时会将创建的进程池保存在列表中。

        Parameters
        ----------
        name : 区别不同子进程的名称。
            包括：RTSP，REST，AI，MQTT。
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
        elif 'REST' == name:
            res = self.factory_.create(RestWorker, name, None, None, **kwargs)
        elif 'AI' == name:
            res = self.factory_.create(AiWorker, name, self.pic_q_, self.vec_q_, **kwargs)
        elif 'MQTT' == name:
            res = self.factory_.create(MqttWorker, name, self.vec_q_, None, **kwargs)
        else:
            res = (None, None)

        return res

    def stop_procs(self):
        msg = bus.EBUS_SPECIAL_MSG_STOP
        self.send_cmd(bus.EBUS_TOPIC_RTSP, msg)
        self.send_cmd(bus.EBUS_TOPIC_AI, msg)
        self.send_cmd(bus.EBUS_TOPIC_MQTT, msg)
        self.send_cmd(bus.EBUS_TOPIC_REST, msg)

        return True


# if __name__ == '__main__':
#
#     INTERVAL = 1
#     PROC_RTSP_CNT = 3
#     PROC_AI_CNT = 2
#
#     mgr = multiprocessing.Manager()
#     pic_que = mgr.Queue()  # Is JoinableQueue better?
#     vec_que = mgr.Queue()
#     ebs = mgr.dict()
#
#     pool_rtsp = multiprocessing.Pool(processes=PROC_RTSP_CNT)
#     pool_rtsp.starmap_async(proc_rtsp, [(1, ebs, None, pic_que), (2, ebs, None, pic_que)])
#
#     pool_ai = multiprocessing.Pool(processes=PROC_AI_CNT)
#     pool_ai.starmap_async(proc_ai, [(1, ebs, pic_que, vec_que), (2, ebs, pic_que, vec_que)])
#
#     while True:
#         sleep(INTERVAL - time() % INTERVAL)
#         numb = random.randrange(1, 4)
#         bus.send_cmd(ebs, bus.EBUS_TOPIC_RTSP, numb)
#         log.logger(os.getpid(), f'messages in event bus: {len(ebs)}', log.LOG_LVL_INFO)
#         log.logger(os.getpid(), f'pictures in pic_que: {pic_que.qsize()}', log.LOG_LVL_INFO)

    # pool_rtsp.close()
    # pool_ai.close()
    # pool_rtsp.join()
    # pool_ai.join()
