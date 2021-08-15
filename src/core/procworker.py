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
from utils import bus, log


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

    def run(self):
        try:
            self.startup()
            self.main_loop()
            return 0
        except BaseException as exc:
            # -- Catch ALL exceptions, even Terminate and Keyboard interrupt
            self.log(f"Exception Shutdown: {exc}", exc_info=True)
        finally:
            self.shutdown()


class ProcWorker(BaseProcWorker, bus.IEventBusMixin):

    def __init__(self, name, topic, dicts, **kwargs):
        super().__init__(name, dicts, **kwargs)
        self.beeper_ = bus.IEventBusMixin.get_beeper()  # Event bus initialized.
        self.bus_topic_ = topic

    def main_loop(self):
        while self.break_out_ is False:
            evt = self.recv_cmd(self.bus_topic_)
            if evt == bus.EBUS_SPECIAL_MSG_STOP:
                break
            else:
                self.main_func(evt)
        self.log("Leaving main_loop.")
