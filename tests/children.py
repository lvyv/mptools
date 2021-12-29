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

from core.procworker import ProcWorker
from utils import bus
from utils import GrabFrame
import time
import os
import cv2


class ChildA(ProcWorker, bus.IEventBusMixin):
    cnt_ = 0

    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)

    def main_func(self, event=None, **kwargs):
        # 返回False，继续循环，返回True，停止循环。
        time.sleep(3)
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
        # retobj = self.subscribe()
        if event:
            self.log(f'subscribed msg:{event}')
            self.cnt_ += 1
            if self.cnt_ < 3:
                return False
            else:
                return True
        else:
            return False

    def shutdown(self):
        self.log('shutdown called.')


def sample_rtsp_frame(url, duration_ms):
    try:
        # print(f'In a worker process- {url}', os.getpid())
        cvobj = GrabFrame.GrabFrame()
        opened = cvobj.open_stream(url, 10)
        info = cvobj.get_stream_info()
        while True:
            frame = cvobj.read_frame()
            if frame is not None:
                cv2.imshow('sample_frame', frame)
                # filename = f'{url.split("/")[-1]}.png'
                # cv2.imwrite(filename, frame)
                cv2.waitKey(duration_ms)
        cvobj.stop_stream()
        cv2.destroyAllWindows()

    except KeyboardInterrupt:
        print("-------------------Caught KeyboardInterrupt, terminating workers-----------------")
