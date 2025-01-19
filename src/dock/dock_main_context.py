#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OPTiDOCK
# The Main Context of the running processes.
#
#
# Awen. 2024.12
#
# 致谢
#
# Copyright (C) 2021 lvyu <lvyu@cxtc.edu.cn>
# Licensed under the GNU LGPL v2.1 - https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html

"""
Test with::
    with DockMainContext() as main_ctx:
        main_ctx.run('conf/v2v.cfg')
"""
import multiprocessing

from utils import log, bus
from core.kernel import MainContext, FSM


class DockMainContext(MainContext):
    # 生产/消费者模型
    QUEUE_COUNT = 3  # 工作进程之间的读写队列数量
    QUEUE_SIZE = 40  # 读写队列的容量大小

    def __init__(self):
        # 日志输出偏函数
        super().__init__()
        # 进程间消息队列，供所有子进程消费
        self._queues = [multiprocessing.Manager().Queue(self.QUEUE_SIZE) for _ in range(self.QUEUE_COUNT)]
        # call_rpc回调注册，供子进程调用
        MainContext.register(bus.CB_STARTUP_PPL, self.callback_start_pipeline)
        MainContext.register(bus.CB_STOP_PPL, self.callback_stop_pipeline)

    def callback_start_pipeline(self, params):
        self.log(params, level=log.LOG_LVL_DBG)
        if self._status.test_status(FSM.STATUS_INITIAL):
            # 为了兼容旧接口，保留该函数
            self.start_v2v_pipeline_task()
            return {'reply': True}
        else:
            return {'reply': False}

    def callback_stop_pipeline(self, params):
        if self._status.test_status(FSM.STATUS_FULL_SPEED):
            self.stop_v2v_pipeline_task()
            self._status.set_status(FSM.STATUS_INITIAL)
            return {'reply': True}
        else:
            return {'reply': False}

    def fork_work_process(self, **kwargs) -> bool:
        """
        动态创建工作进程数量.

        Parameters:
                **kwargs: 任意键值参数.
                    支持的键包含
                    - ‘worker_services’ (str): 所有需要实例化的工作进程。

        Returns:
            bool: True if the work processes are successfully forked;
                  False otherwise.
        """
        _ret = False
        workers = kwargs['worker_services']
        for idx, worker_dict in enumerate(workers):
            for key, value in worker_dict.items():
                if idx == 0:  # 第一项
                    self._factory.create_worker(key, f'WORK', None, self._queues[idx], **kwargs)
                elif idx == len(workers) - 1:  # 最后一项
                    self._factory.create_worker(key, f'WORK', self._queues[idx-1], None, **kwargs)
                else:
                    self._factory.create_worker(key, f'WORK', self._queues[idx-1], self._queues[idx], **kwargs)
                self.log(f'[{self.__class__.__name__}] '
                         f'{key} is instantiated into {value["cnt"]} processes.', level=log.LOG_LVL_INFO)
        self.log(f'[{self.__class__.__name__}] ObjTracker-->ReID-->D3Construct', level=log.LOG_LVL_INFO)
        return True

    def show_queues_status(self):
        """
        本函数显示进程间消息队列的状态。

        Returns:
            None
        """
        self.log(f'[{self.__class__.__name__}]  '
                 f'{" ".join([f"QUEUE_{i}：{val.qsize()}" for i, val in enumerate(self._queues)])}',
                 level=log.LOG_LVL_INFO)

    def run(self, rest='dock.dock_rest.DockRestWorker', **kwargs):
        super(DockMainContext, self).run(rest, **kwargs)
        pass

    def start_v2v_pipeline_task(self):
        # 标记工作状态
        self.log(f'[{self.__class__.__name__}] Got a start cmd.', level=log.LOG_LVL_INFO)

        self._status.set_status(FSM.STATUS_FULL_SPEED)
        pass

    def stop_v2v_pipeline_task(self):
        # 微服务进程与主进程同时存在，不会停
        self.log(f'[{self.__class__.__name__}] Got a stop cmd.', level=log.LOG_LVL_INFO)
        msg = bus.EBUS_SPECIAL_MSG_STOP
        self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)
        pass
