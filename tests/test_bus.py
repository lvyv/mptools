#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 The OPTiDOCK Authors. All Rights Reserved.
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

import unittest
import multiprocessing
import functools

from utils import bus, log
from utils.wrapper import proc_worker_wrapper as worker_wrapper
from children import ChildB, ChildA, ChildC

# def worker_wrapper(proc_worker_class, name, dicts=None):
#     pid = os.getpid()
#     proc_worker = proc_worker_class(f'{name}-{pid}', dicts)
#     return proc_worker.run()


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
        callcounts = 6
        pool = multiprocessing.Pool(processes=10)
        # pool.apply_async(worker_wrapper, (ChildA, f'A1'))
        pool.starmap_async(worker_wrapper, [(ChildA, f'A1')])
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
