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
unit test module
=========================

测试核心模块的主进程模块.
"""

# Author: Awen <26896225@qq.com>
# License: MIT

import unittest
import random
from core.main import MainContext
from time import sleep, time
from utils import bus, log


class TestMain(unittest.TestCase):
    """Tests for `phm` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_MainContext(self):
        """Test core.main.MainContext."""
        with MainContext() as main_ctx:
            main_ctx.log('started.')

            num = 1  # how many processes do I need?
            main_ctx.start_procs('RTSP', cnt=num, rtsp_url='rtsp://admin:admin123@192.168.101.114:554/cam/realmonitor'
                                                           '?channel=1&subtype=0')
            num = 1  # how many processes do I need?
            main_ctx.start_procs('RTSP', cnt=num, rtsp_url='rtsp://admin:admin123@192.168.101.114:554/cam/playback'
                                                           '?channel=1&subtype=0&starttime=2021_08_03_11_50_00')
            num = 3
            main_ctx.start_procs('AI', cnt=num)

            num = 3
            main_ctx.start_procs('MQTT', cnt=num, mqtt_host='192.168.1.225', mqtt_port=1886, mqtt_topic='/dt/devid-1',
                                 mqtt_cid='devid-1')

            # main_ctx.stop_procs()
            # main_ctx.start_procs('RTSP', cnt=2)

            interval = 1
            while True:
                sleep(interval - time() % interval)
                numb = random.randrange(1, 4)

            main_ctx.factory_.pool_.close()
            main_ctx.factory_.pool_.join()

            self.assertEqual(len(res), num)
            self.assertEqual(sum(res), 0)


if __name__ == "__main__":
    unittest.main()
