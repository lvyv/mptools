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
from core.main import MainContext
from utils import config, bus


class TestMain(unittest.TestCase):
    """Tests for `phm` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_MainContext(self):
        """Test core.main.MainContext."""
        # 'rtsp://admin:admin123@192.168.101.114:554/cam/realmonitor?channel=1&subtype=0'
        # 'rtsp://admin:admin123@192.168.101.114:554/cam/playback?channel=1&subtype=0&starttime=2021_08_03_11_50_00'
        with MainContext(bus.EBUS_TOPIC_MAIN) as main_ctx:
            main_ctx.log('********************  CASICLOUD AI METER services  ********************')
            cfg = config.load_json('v2v.cfg')
            # 启动进程
            for channel in cfg['rtsp_urls']:
                main_ctx.start_procs('RTSP', rtsp_url=channel, sample_rate=1)   # 不提供cnt=x参数，缺省1个通道启1个进程
                num = 3                                                         # AI比较慢，安排两个进程处理
                main_ctx.start_procs('AI', cnt=num)
                num = 2                                                         # MQTT比较慢，上传文件，安排两个进程处理
                mqtt = cfg['mqtt_svrs'][0]
                main_ctx.start_procs('MQTT', cnt=num, mqtt_host=mqtt['mqtt_svr'], mqtt_port=mqtt['mqtt_port'],
                                     mqtt_topic=mqtt['mqtt_tp'])
            api = cfg['micro_service']
            (ap, key, cer) = (api['http_port'], api['ssl_keyfile'], api['ssl_certfile'])
            main_ctx.start_procs('REST', port=ap, ssl_keyfile=key, ssl_certfile=cer)    # 启动1个Rest进程，提供微服务调用

            loop = True
            while loop:
                msg = main_ctx.recv_cmd(bus.EBUS_TOPIC_MAIN)
                if msg:
                    main_ctx.log(msg)

            main_ctx.stop_procs()
            # 等待进程结束
            main_ctx.factory_.pool_.close()
            main_ctx.factory_.pool_.join()


if __name__ == "__main__":
    unittest.main()
