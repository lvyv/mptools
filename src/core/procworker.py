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
Sub process base class  module
=========================

All common behaviors of sub process.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import functools
import time
from utils import bus, log, V2VErr


class BaseProcWorker:

    def __init__(self, name, dicts, **kwargs):
        self.name = name
        self.log = functools.partial(log.logger, f'{name}')
        self.break_out_ = False
        if dicts:   # 扩展参数
            pass

    def main_loop(self):
        self.log("Entering main_loop.")
        raise NotImplementedError(f"{self.__class__.__name__}.main_loop is not implemented")

    def startup(self):
        self.log("Entering startup.")
        pass

    def shutdown(self):
        self.log("Entering shutdown.")
        pass

    def main_func(self, event=None, *args):
        self.log("Entering main_func.")
        raise NotImplementedError(f"{self.__class__.__name__}.main_func is not implemented")

    def running_logic(self):
        re_run = False
        try:
            self.startup()
            self.main_loop()
            self.shutdown()
        except (V2VErr.V2VConfigurationChangedError, V2VErr.V2VConfigurationIllegalError):
            # 发生运行时配置更新或配置不合法，并不停进程，而是等待配置下发正确
            re_run = True
        finally:
            return re_run

    def run(self):
        re_run = True
        while re_run:
            re_run = self.running_logic()


class ProcWorker(BaseProcWorker, bus.IEventBusMixin):
    def __init__(self, name, topic, dicts, **kwargs):
        super().__init__(name, dicts, **kwargs)
        self.startts_ = time.time()                                      # 记录进程启动的时间戳
        self.beeper_ = bus.IEventBusMixin.get_beeper()                   # req-rep客户端。
        self.subscriber_ = bus.IEventBusMixin.get_subscriber(topic)      # pub-sub订阅端。

    def call_rpc(self, method, param):
        self.send_cmd(method, param)
        ret = self.recv_cmd()
        return ret

    def main_loop(self):
        try:
            while self.break_out_ is False:
                evt = self.subscribe()
                if evt == bus.EBUS_SPECIAL_MSG_STOP:        # 共性操作：停止子进程
                    break
                elif evt == bus.EBUS_SPECIAL_MSG_CFG:       # 共性操作：配置发生更新
                    raise V2VErr.V2VConfigurationChangedError(evt)
                elif evt:                                   # 其它广播事件，比如停止某个通道
                    self.log(f'Got message: {evt}.')
                self.break_out_ = self.main_func(evt)
                # 在每次循环完毕上报一次运行时间。
                delta = time.time() - self.startts_
                self.call_rpc(bus.CB_SET_METRICS, {'up': delta, 'application': self.name})

            self.log('Leaving main_loop.')
        except KeyboardInterrupt:
            self.log(f'[{__file__}]----Caught KeyboardInterrupt----', level=log.LOG_LVL_ERRO)
            self.beeper_.disconnect()
            self.beeper_.close()
            self.subscriber_.disconnect()
            self.subscriber_.close()
