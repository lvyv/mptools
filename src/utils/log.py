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
log module
=========================

Log util for the project.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import os
import time
import logging

LOG_LVL_INFO = logging.INFO
LOG_LVL_ERRO = logging.ERROR

start_time = time.monotonic()
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


def logger(name, msg, level=LOG_LVL_INFO, exc_info=None):
    elapsed = time.monotonic() - start_time
    hours = int(elapsed // 60)
    seconds = elapsed - (hours * 60)
    logging.log(level, f'{hours:3}:{seconds:06.3f} {name:20} {msg}', exc_info=exc_info)