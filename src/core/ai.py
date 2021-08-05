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
ai module
=========================

Feed AI meter picture one by one and get recognized results.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

# import os
# from utils import bus, log
# from time import time, sleep
#
# INTERVAL = 1  # seconds
# PIC_QUEUE_LENGTH = 10
#
#
# def handle_instruction(cmd):
#     return True
#
#
# def proc_ai(name, ebs, iq=None, oq=None):
#     while True:
#         sleep(INTERVAL - time() % INTERVAL)
#         try:
#             # 1. get instruction from main process and handle it
#             handle_instruction(bus.recv_cmd(ebs, bus.EBUS_TOPIC_AI))
#             # 2. consume pictures
#             cnt = 0
#             pic = iq.get()
#             log.logger(os.getpid(), log.LOG_LVL_INFO, f'{pic}')
#         except KeyError as err:
#             log.logger(os.getpid(), log.LOG_LVL_ERRO, f'{err}')
#         except TypeError as err:
#             log.logger(os.getpid(), log.LOG_LVL_ERRO, f'{err}')
#         finally:
#             pass
import io
import requests
from matplotlib import pyplot as plt
from time import time
from utils import bus
from core.procworker import ProcWorker


class AiWorker(ProcWorker):
    def __init__(self, name, evt_bus, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, evt_bus, dicts, **kwargs)
        self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q

    def main_func(self, event, *args):
        if 'END' == event:
            self.break_out_ = True
        pic = self.in_q_.get()
        fn = time()
        # cv2.imwrite(f'{pic["channel"]}-{fn}.bmp', pic['frame'])
        buf = io.BytesIO()
        plt.imsave(buf, pic['frame'], format='png')
        image_data = buf.getvalue()

        # var_0 = requests.post('http://127.0.0.1:21800/up', params=params, headers=headers, data=image_data)
        var_0 = requests.post('http://127.0.0.1:21800/files/', data=image_data)



