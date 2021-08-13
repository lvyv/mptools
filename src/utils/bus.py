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
bus module
=========================

Event bus of all processes.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import os
import utils.log as log
from pynng import Bus0, Timeout
import time

# DEFAULT_POLLING_TIMEOUT = 0.02
EBUS_TOPIC_RTSP = 'rtsp'
EBUS_TOPIC_AI = 'ai'
EBUS_TOPIC_MQTT = 'mqtt'
EBUS_TOPIC_REST = 'rest'
EBUS_TOPIC_MAIN = 'main'
EBUS_TOPIC_PROC = 'procworker'    # base class topic


class IEventBusMixin:
    address_ = 'tcp://127.0.0.1:13131'
    center_ = None

    @classmethod
    def get_beeper(cls, rtimeout=1):
        return Bus0(dial=cls.address_, recv_timeout=rtimeout)

    @classmethod
    def get_center(cls, rtimeout=1):
        if cls.center_ is None:
            cls.center_ = Bus0(listen=cls.address_, recv_timeout=rtimeout)
        return cls.center_

    def recv_cmd(self, topic):
        """Mixin methods"""
        try:
            if self.beeper_ is None:
                raise Exception("evt_bus_ must be set.")
            ret = None
            bus = self.beeper_
            msg = bus.recv(block=True).decode('utf-8').split(':')
            if msg[0] == topic:
                ret = msg[1]
        except Timeout as te:
            # self.log(te, level=log.LOG_LVL_ERRO)
            pass
        return ret

    def send_cmd(self, topic, msg):
        """Mixin methods"""
        if self.beeper_ is None:
            raise Exception("evt_bus_ must be set.")
        bus = self.beeper_
        json = f'{topic}:{msg}'
        bus.send(json.encode('utf-8'))
        self.log(f'send {json} bytes.')


def send_cmd(bus, topic, msg):
    ret = False
    try:
        while bus[topic]:   # timeout should be taken into consideration
            pass
    except KeyError as err:
        bus['rtsp'] = msg
        log.logger(os.getpid(), log.LOG_LVL_INFO, f'send-->{msg}')
    finally:
        return ret


def recv_cmd(bus, topic):
    msg = None
    try:
        # pid = os.getpid()
        msg = bus.pop(topic)
        log.logger(os.getpid(), log.LOG_LVL_INFO, f'got events: {msg}')
    except KeyError as ke:
        pass
    finally:
        return msg
