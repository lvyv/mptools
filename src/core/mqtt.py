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
mqtt module
=========================

Publish recognized results to iot gateway.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import paho.mqtt.client as mqtt_client
from utils import bus
from core.procworker import ProcWorker


class MqttWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.mqtt_cid_ = name   # 这个名字无所谓，在网关处会重新mapping key-value到正确的设备号
        self.mqtt_host_ = None
        self.mqtt_port_ = None
        self.mqtt_topic_ = None
        self.fsvr_url_ = None
        for key, value in dicts.items():
            if key == 'mqtt_host':
                self.mqtt_host_ = value
            elif key == 'mqtt_port':
                self.mqtt_port_ = value
            elif key == 'mqtt_topic':
                self.mqtt_topic_ = value
            elif key == 'fsvr_url':
                self.fsvr_url_ = value
        self.client_ = None

    def startup(self):
        self.client_ = mqtt_client.Client()
        self.client_.username_pw_set(self.mqtt_cid_)
        self.client_.connect(self.mqtt_host_, self.mqtt_port_)
        self.client_.loop_start()

    def main_func(self, event=None, *args):
        # 全速
        # self.log('mqtt begin get data.')
        vec = self.in_q_.get()
        self.client_.publish(self.mqtt_topic_, vec, 1)
        self.log(vec)

        return False

    def shutdown(self):
        self.client_.loop_stop()
        self.client_.disconnect()
        self.client_ = None
