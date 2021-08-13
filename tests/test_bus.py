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

from time import time, sleep
from core.procworker import ProcWorker
from utils import bus, log
from pynng import Timeout


def proc_worker_wrapper(proc_worker_class, name, dicts=None, **kwargs):
    pid = os.getpid()
    proc_worker = proc_worker_class(f'{name}-{pid}', dicts, **kwargs)
    # sleep(1)
    return proc_worker.run()


class ChildA(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, dicts=None, **kwargs):
        super().__init__(name, 'ChildA', dicts, **kwargs)

    def main_func(self, event=None, *args):
        if 'END' == event:
            self.break_out_ = True
        sleep(1 - time() % 1)
        # self.log('main_func called.')


class ChildB(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, 'ChildB', dicts, **kwargs)

    def run(self, *kwargs):
        self.log(f'Run method called.')


class ChildC(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, 'ChildC', dicts, **kwargs)

    def startup(self):
        self.log('startup called.')

    def main_func(self, event=None, *args):
        sleep(1 - time() % 1)
        self.log(f'Received: {event}')
        self.send_cmd('TestBus', 'bye.')

    def shutdown(self):
        self.log('shutdown called.')


class TestBus(unittest.TestCase, bus.IEventBusMixin):
    """Tests for `utils.bus` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.beeper_ = bus.IEventBusMixin.get_center(rtimeout=1)
        self.log = functools.partial(log.logger, 'TestBus')

    def tearDown(self):
        """Tear down test fixtures, if any."""
        self.center_.close()

    def test_Bus(self):
        """Test bus."""
        pool = multiprocessing.Pool(processes=10)
        pool.starmap_async(proc_worker_wrapper, [(ChildA, f'A', None) for idx in range(1)])
        pool.starmap_async(proc_worker_wrapper, [(ChildB, f'B', None) for idx in range(1)])
        pool.apply_async(proc_worker_wrapper, (ChildC, f'C', None))
        while True:
            try:
                self.send_cmd('ChildC', 'hello')
                sleep(3 - time() % 3)
                msg = self.recv_cmd('TestBus')
                self.log(f'Received:{msg}')
            except Timeout as te:
                self.log(te, level=log.LOG_LVL_ERRO)
            except KeyboardInterrupt as be:
                break

        pool.close()
        pool.join()
        self.assertEqual(1, 1)


if __name__ == "__main__":
    unittest.main()

