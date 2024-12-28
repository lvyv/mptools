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
from src.core.kernel import MainContext
# from utils import config, bus


class TestMain(unittest.TestCase):
    """
    Tests for `v2v` entrypoint.
    本测试案例启动整个v2v程序（前提需要启动Mock提供仿真接口，并启动obs的rtsp服务器）
    访问运行本案例的URL：
    https://IP:29080/docs，执行POST /subprocess，发送start/stop命令启停视频识别流水线。
    注意
    """
    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_MainContext(self):
        """Test core.main.MainContext."""
        p2c = 'conf/v2v.cfg'
        with MainContext() as main_ctx:
            main_ctx.run(p2c)


if __name__ == "__main__":
    unittest.main()
