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

import cv2
import imutils
from time import time, sleep
from utils import bus
from core.procworker import ProcWorker
from imutils.video import VideoStream


class RtspWorker(ProcWorker):
    def __init__(self, name, evt_bus, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, evt_bus, dicts, **kwargs)
        self.bus_topic_ = bus.EBUS_TOPIC_RTSP
        self.out_q_ = out_q
        self.vs_ = None
        self.rtsp_url_ = None
        for key, value in dicts.items():
            if key == 'rtsp_url':
                self.rtsp_url_ = value
                break

    def startup(self):
        self.vs_ = VideoStream(self.rtsp_url_).start()

    def main_func(self, event, *args):
        if 'END' == event:
            self.break_out_ = True
        # 1秒1帧
        sleep(3 - time() % 3)
        frame = self.vs_.read()
        if frame is not None:
            frame = imutils.resize(frame, width=1200)  # size changed from 6MB to 2MB
            # cv2.imshow('NVR realtime', frame)
            pic = {'channel': self.name, 'frame': frame}
            self.out_q_.put(pic)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            self.break_out_ = True

    def shutdown(self):
        cv2.destroyAllWindows()
        self.vs_.stop()
