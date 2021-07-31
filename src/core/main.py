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
main module
=========================

Entry point of the project.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import multiprocessing
import random
import os
from time import time, sleep
from rtsp import proc_rtsp
from ai import proc_ai
from utils import bus, log

if __name__ == '__main__':

    INTERVAL = 1
    PROC_RTSP_CNT = 3
    PROC_AI_CNT = 2

    mgr = multiprocessing.Manager()
    pic_que = mgr.Queue()   # Is JoinableQueue better?
    vec_que = mgr.Queue()
    ebs = mgr.dict()

    pool_rtsp = multiprocessing.Pool(processes=PROC_RTSP_CNT)
    pool_rtsp.starmap_async(proc_rtsp, [(1, ebs, None, pic_que), (2, ebs, None, pic_que)])

    pool_ai = multiprocessing.Pool(processes=PROC_AI_CNT)
    pool_ai.starmap_async(proc_ai, [(1, ebs, pic_que, vec_que), (2, ebs, pic_que, vec_que)])

    while True:
        sleep(INTERVAL - time() % INTERVAL)
        numb = random.randrange(1, 4)
        bus.send_cmd(ebs, bus.EBUS_TOPIC_RTSP, numb)
        log.logger(os.getpid(), log.LOG_LVL_INFO, f'messages in event bus: {len(ebs)}')
        log.logger(os.getpid(), log.LOG_LVL_INFO, f'pictures in pic_que: {pic_que.qsize()}')

    pool_rtsp.close()
    pool_ai.close()
    pool_rtsp.join()
    pool_ai.join()
