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
unit test module
=========================

测试进程之间事件总线功能.
构造Mediator设计模式。
Mediator是主进程，负责启动子进程。
ChildA，ChildB，ChildC是独立子进程。
需要测试A，B，C与Mediator的双向通信。
"""

# Author: Awen <26896225@qq.com>
# License: MIT

import os
import unittest
import multiprocessing
import functools
# import time
from core.procworker import ProcWorker
from utils import bus, log


def worker_wrapper(proc_worker_class, name, dicts=None):
    pid = os.getpid()
    proc_worker = proc_worker_class(f'{name}-{pid}', dicts)
    return proc_worker.run()


class ChildA(ProcWorker, bus.IEventBusMixin):
    cnt_ = 0

    def __init__(self, name, dicts=None, **kwargs):
        super().__init__(name, 'ChildA', dicts, **kwargs)

    def main_func(self, event=None, **kwargs):
        # 返回False，继续循环，返回True，停止循环。
        retobj = self.call_rpc('TestBus', {'p1': 1, 'p2': 'hello'})
        self.log(f'{retobj}({ChildA.cnt_})')
        ChildA.cnt_ += 1
        if ChildA.cnt_ <= 2:
            return False
        else:
            return True


class ChildB(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, 'ChildB', dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q

    def run(self, **kwargs):
        cnt = 3
        while cnt > 0:
            self.call_rpc('testbus', {'p1': 0, 'p2': 'hello'})
            cnt -= 1


class ChildC(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, 'CTOPIC', dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.cnt_ = 0

    def startup(self):
        self.log('startup called.')
        self.call_rpc('gotchild', {'up': True})

    def main_func(self, event=None, *args):
        # 返回False，继续循环，返回True，停止循环。
        retobj = self.subscribe()
        if retobj:
            self.log(f'subscribed msg:{retobj}')
            self.cnt_ += 1
            if self.cnt_ < 3:
                return False
        else:
            return False

    def shutdown(self):
        self.log('shutdown called.')


class TestBus(unittest.TestCase, bus.IEventBusMixin):
    """Tests for `utils.bus` package."""
    # bus_topic_ = 'TestBus'
    children_ = 0

    @classmethod
    def init_svr(cls):
        if cls.center_ is None:
            cls.center_ = bus.IEventBusMixin.get_center()
            cls.broadcaster_ = bus.IEventBusMixin.get_broadcaster()
        return True

    def callback_testbus(self, params):
        self.log(params)
        return {'reply': True}

    def callback_gotchild(self, params):
        self.log(params)
        TestBus.children_ += 1
        return {'reply': True}

    def setUp(self):
        """Set up test fixtures, if any."""
        self.log = functools.partial(log.logger, 'TestBus')
        # self.bus_topic_ = 'TestBus'
        TestBus.init_svr()  # init as server
        TestBus.register('testbus', self.callback_testbus)
        TestBus.register('gotchild', self.callback_gotchild)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_Bus_RPC(self):
        """Test receive: ChildB will send 3 messages to TestBus once it has started."""
        callcounts = 6
        pool = multiprocessing.Pool(processes=10)
        pool.apply_async(worker_wrapper, (ChildB, f'B1'))
        pool.apply_async(worker_wrapper, (ChildB, f'B1'))
        cnt = 0
        while cnt < callcounts:
            # svr wait for calling and reply
            TestBus.rpc_service()
            cnt += 1

        pool.close()
        pool.join()
        self.assertEqual(cnt, callcounts)

    def test_Bus_RPC2(self):
        """Test receive: ChildB will send 3 messages to TestBus once it has started."""
        callcounts = 3
        pool = multiprocessing.Pool(processes=10)
        pool.apply_async(worker_wrapper, (ChildB, f'B1'))
        cnt = 0
        while cnt < callcounts:
            # svr wait for calling and reply
            TestBus.rpc_service()
            cnt += 1

        pool.close()
        pool.join()
        self.assertEqual(cnt, callcounts)

    def test_Bus_ClientCall(self):
        """Test ChildA will make 3 rpc calls and exit."""
        callcounts = 3
        pool = multiprocessing.Pool(processes=10)
        pool.apply_async(worker_wrapper, (ChildA, f'A1'))
        cnt = 0
        while cnt < callcounts:  # 响应三次调用
            # svr wait for calling and reply
            TestBus.rpc_service()
            cnt += 1

        pool.close()
        pool.join()
        self.assertEqual(cnt, callcounts)

    def test_Bus_PubSub(self):
        """Test ChildC will subscribe broadcasting message, we broadcast three times."""
        pool = multiprocessing.Pool(processes=10)
        pool.apply_async(worker_wrapper, (ChildC, f'C1'))
        pool.apply_async(worker_wrapper, (ChildC, f'C2'))
        pool.apply_async(worker_wrapper, (ChildC, f'C3'))
        # time.sleep(1)   # 等待订阅进程都建立连接
        while True:
            TestBus.rpc_service()                               # rpc远程调用服务启动，阻塞等待外部事件出发状态改变
            if TestBus.children_ == 3:                          # ChildC每个子进程启动会调用rpc通知主进程一次
                # 3个子进程都连接上了，可以接收广播消息了
                TestBus.broadcast('CTOPIC', {'msg': 1})
                TestBus.broadcast('CTOPIC', {'msg': 2})
                TestBus.broadcast('CTOPIC', {'msg': 3})
                break

        pool.close()
        pool.join()
        self.assertEqual(1, 1)


if __name__ == "__main__":
    unittest.main()
