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


class ProcWorker:

    def __init__(self, name, evt_bus, **kwargs):
        self.name = name
        self.log = functools.partial(log.logger, f'{name}')
        self.evt_bus_ = evt_bus
        self.bus_topic_ = bus.EBUS_TOPIC_BASE
        # self.init_args(**kwargs)
        self.break_out_ = False

    def main_loop(self):
        # self.log("Entering main_loop.")
        while self.break_out_ is False:
            evt = bus.recv_cmd(self.evt_bus_, self.bus_topic_)
            self.main_func(evt)
        self.log("Leaving main_loop.")

    def startup(self):
        self.log("Entering startup.")
        # bus.send_cmd(self.evt_bus_, bus.EBUS_TOPIC_MAIN, {'src': self.name, 'content': 'UP'})
        pass

    def shutdown(self):
        self.log("Entering shutdown.")
        # bus.send_cmd(self.evt_bus_, bus.EBUS_TOPIC_MAIN, {'src': self.name, 'content': 'DOWN'})
        pass

    def main_func(self, event, *args):
        self.log("Entering main_func.")
        raise NotImplementedError(f"{self.__class__.__name__}.main_func is not implemented")

    def run(self):
        try:
            self.startup()
            # self.startup_event.set()
            self.main_loop()
            self.log("Normal Shutdown.")
            return 0
        except BaseException as exc:
            # -- Catch ALL exceptions, even Terminate and Keyboard interrupt
            self.log(f"Exception Shutdown: {exc}", exc_info=True)
        finally:
            self.shutdown()
