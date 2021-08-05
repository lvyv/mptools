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
rtsp module
=========================

Pull av stream from nvr and decode pictures from the streams.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

from time import time, sleep
import functools
from utils import bus, log
from core.procworker import ProcWorker

# class RtspWorker:
#     def __init__(self, name, evt_bus, in_q=None, out_q=None, up_evt=None, down_evt=None, **kwargs):
#         self.log = functools.partial(log.logger, f'{name}')
#         self.evt_bus_ = evt_bus
#         self.out_q_ = out_q
#
#     def run(self):
#         while True:
#             sleep(3 - time() % 3)
#             try:
#                 # 1. get instruction from main process and handle it
#                 msg = bus.recv_cmd(self.evt_bus_, bus.EBUS_TOPIC_RTSP)
#                 self.log(msg)
#                 if 'END' == msg:
#                     break
#
#             except KeyError as err:
#                 self.log(f'{err}', level=log.LOG_LVL_ERRO)
#             except TypeError as err:
#                 self.log(f'{err}', level=log.LOG_LVL_ERRO)
#             finally:
#                 pass


class RtspWorker(ProcWorker):
    def __init__(self, name, evt_bus, in_q=None, out_q=None, up_evt=None, down_evt=None, **kwargs):
        super().__init__(name, evt_bus, **kwargs)
        self.bus_topic_ = bus.EBUS_TOPIC_RTSP
        # self.log = functools.partial(log.logger, f'{name}')
        self.out_q_ = out_q

    def main_func(self, event, *args):
        # self.log("Entering main_func.")
        sleep(3 - time() % 3)
        self.log('rtsp doing works...')
        if 'END' == event:
            self.break_out_ = True

    # def run(self):
    #     while True:
    #         sleep(3 - time() % 3)
    #         try:
    #             # 1. get instruction from main process and handle it
    #             msg = bus.recv_cmd(self.evt_bus_, bus.EBUS_TOPIC_RTSP)
    #             self.log(msg)
    #             if 'END' == msg:
    #                 break
    #
    #         except KeyError as err:
    #             self.log(f'{err}', level=log.LOG_LVL_ERRO)
    #         except TypeError as err:
    #             self.log(f'{err}', level=log.LOG_LVL_ERRO)
    #         finally:
    #             pass
# import os
# from utils import bus, log
# from time import time, sleep
#
# INTERVAL = 5  # seconds
# PIC_QUEUE_LENGTH = 10
#
#
# def handle_instruction(cmd):
#     return True
#
#
# def proc_rtsp(name, ebs, iq=None, oq=None):
#     cnt = 0
#     while True:
#         sleep(INTERVAL - time() % INTERVAL)
#         try:
#             # 1. get instruction from main process and handle it
#             handle_instruction(bus.recv_cmd(ebs, bus.EBUS_TOPIC_RTSP))
#             # 2. decode pictures from av stream
#             # 3. put picture to pic_que
#             if not oq.full():
#                 cnt += 1
#                 oq.put({'pic': cnt, 'id': os.getpid()})
#         except KeyError as err:
#             log.logger(os.getpid(), log.LOG_LVL_ERRO, f'{err}')
#         except TypeError as err:
#             log.logger(os.getpid(), log.LOG_LVL_ERRO, f'{err}')
#         finally:
#             pass

