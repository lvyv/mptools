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

import os
from utils import bus, log
from time import time, sleep

INTERVAL = 1  # seconds
PIC_QUEUE_LENGTH = 10


def handle_instruction(cmd):
    return True


def proc_ai(name, ebs, iq=None, oq=None):
    while True:
        sleep(INTERVAL - time() % INTERVAL)
        try:
            # 1. get instruction from main process and handle it
            handle_instruction(bus.recv_cmd(ebs, bus.EBUS_TOPIC_AI))
            # 2. consume pictures
            cnt = 0
            pic = iq.get()
            log.logger(os.getpid(), log.LOG_LVL_INFO, f'{pic}')
        except KeyError as err:
            log.logger(os.getpid(), log.LOG_LVL_ERRO, f'{err}')
        except TypeError as err:
            log.logger(os.getpid(), log.LOG_LVL_ERRO, f'{err}')
        finally:
            pass
