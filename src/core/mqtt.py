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


import cv2
import imutils
from time import time, sleep
from utils import bus
from core.procworker import ProcWorker
from imutils.video import VideoStream


class MqttWorker(ProcWorker):
    def __init__(self, name, evt_bus, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, evt_bus, dicts, **kwargs)
        self.bus_topic_ = bus.EBUS_TOPIC_MQTT
        self.in_q_ = in_q
        self.mqtt_host_ = None
        self.mqtt_port_ = None
        self.fsvr_url_ = None
        for key, value in dicts.items():
            if key == 'mqtt_host':
                self.mqtt_host_ = value
            elif key == 'mqtt_port':
                self.mqtt_port_ = value
            elif key == 'fsvr_url':
                self.fsvr_url_ = value

    # def startup(self):
    #     self.vs_ = VideoStream(self.rtsp_url_).start()

    def main_func(self, event, *args):
        if 'END' == event:
            self.break_out_ = True
        # 全速
        vec = self.in_q_.get()
        self.log(vec)

    # def shutdown(self):
    #     cv2.destroyAllWindows()
    #     self.vs_.stop()
