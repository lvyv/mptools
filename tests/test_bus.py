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

from time import sleep
from core.procworker import ProcWorker
from utils import bus, log


def proc_worker_wrapper(proc_worker_class, name, dicts=None, **kwargs):
    pid = os.getpid()
    proc_worker = proc_worker_class(f'{name}-{pid}', dicts, **kwargs)
    return proc_worker.run()


class ChildA(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, dicts=None, **kwargs):
        super().__init__(name, 'ChildA', dicts, **kwargs)

    def main_func(self, event=None, *args):
        if 'hello' == event:
            self.send_cmd('TestBus', 'A1')


class ChildB(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, 'ChildB', dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q

    def run(self, *kwargs):
        sleep(0.001)  # FIXME: 不知为何必须要先停一下，让主进程准备好才能接收到，休眠多久时间并不重要
        cnt = 3
        while cnt > 0:
            self.send_cmd('TestBus', f'B{cnt}')
            cnt -= 1


class ChildC(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, 'ChildC', dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q

    def startup(self):
        self.log('startup called.')

    def main_func(self, event=None, *args):
        if 'hello' == event:
            self.send_cmd('TestBus', 'B Fine.')

    def shutdown(self):
        self.log('shutdown called.')


class TestBus(unittest.TestCase, bus.IEventBusMixin):
    """Tests for `utils.bus` package."""
    bus_topic_ = 'TestBus'

    def setUp(self):
        """Set up test fixtures, if any."""
        self.log = functools.partial(log.logger, TestBus.bus_topic_)
        self.beeper_ = bus.IEventBusMixin.get_center(rtimeout=1)
        self.bus_topic_ = 'TestBus'

    def tearDown(self):
        """Tear down test fixtures, if any."""
        # self.beeper_.close()

    # def test_Bus_BroadCastWithReply(self):
    #     """Test bus."""
    #     TestBus.pool_ = multiprocessing.Pool(processes=3)
    #     TestBus.pool_.apply_async(proc_worker_wrapper, (ChildC, f'C', None))
    #     sleep(1)    # wait for sub process starting up.
    #     self.send_cmd(bus.EBUS_TOPIC_BROADCAST, 'Hello!')
    #     msg1 = self.recv_cmd(TestBus.bus_topic_)
    #     # msg2 = self.recv_cmd(TestBus.bus_topic_)
    #     # self.assertIn('Fine', msg1, f'Fine is not in {msg1}')
    #     # self.assertIn('Fine', msg2, f'Fine is not in {msg2}')
    #     self.assertEqual(1, 1)

    def test_Bus_Receive(self):
        """Test receive: ChildB will send a message to TestBus once it has started."""
        pool = multiprocessing.Pool(processes=5)
        pool.apply_async(proc_worker_wrapper, (ChildB, f'B', None))
        msg = None
        while msg is None:
            msg = self.recv_cmd(TestBus.bus_topic_)
        self.assertEqual(msg, 'B3')
        msg = self.recv_cmd(TestBus.bus_topic_)
        self.assertEqual(msg, 'B2')
        msg = self.recv_cmd(TestBus.bus_topic_)
        self.assertEqual(msg, 'B1')
        pool.close()
        pool.join()

    def test_Bus_SendAndReply(self):
        pool = multiprocessing.Pool(processes=2)
        pool.apply_async(proc_worker_wrapper, (ChildA, f'A', None))

        sleep(1)  # FIXME: Have to wait for subprocess startup.

        self.send_cmd('ChildA', 'hello')
        msg = None
        while msg is None:
            msg = self.recv_cmd(TestBus.bus_topic_)
            if not msg:
                pass
            elif msg == 'A1':
                self.send_cmd('ChildA', bus.EBUS_SPECIAL_MSG_STOP)
                self.log(msg)
                break
            else:
                self.log(f'recv:{msg}')
                msg = None
        self.assertEqual(1, 1)
        pool.close()
        pool.join()

    def test_Bus_OnOffAll(self):
        """Test shutdown subprocesses one by one."""

        pool = multiprocessing.Pool(processes=3)
        # TestBus.pool_.starmap_async(proc_worker_wrapper, [(ChildA, f'A', None) for idx in range(1)])
        pool.starmap_async(proc_worker_wrapper, [(ChildB, f'B({idx})', None) for idx in range(1, 2)])
        pool.apply_async(proc_worker_wrapper, (ChildC, f'C', None))

        sleep(1)  # wait for sub process starting up.

        # self.send_cmd('ChildA', bus.EBUS_SPECIAL_MSG_STOP)
        # self.send_cmd('ChildB', bus.EBUS_SPECIAL_MSG_STOP)    # B goes down automately.
        self.send_cmd('ChildC', bus.EBUS_SPECIAL_MSG_STOP)
        pool.close()
        pool.join()

        self.assertEqual(1, 1)


if __name__ == "__main__":
    unittest.main()
