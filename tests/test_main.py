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


class TestMain(unittest.TestCase):
    """Tests for `phm` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_MainContext(self):
        """Test core.main.MainContext."""
        with MainContext() as main_ctx:
            num = 3     # how many processes do I need?
            main_ctx.log('started.')

            res = main_ctx.start_procs('RTSP', cnt=num)
            for pool in main_ctx.pools_:
                pool.close()
                pool.join()
            self.assertEqual(len(res), num)
            self.assertEqual(sum(res), 0)

            num = 2
            res = main_ctx.start_procs('MQTT', cnt=num)
            for pool in main_ctx.pools_:
                pool.close()
                pool.join()
            self.assertEqual(len(res), num)
            self.assertEqual(sum(res), 0)


if __name__ == "__main__":
    unittest.main()
