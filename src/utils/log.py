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

import time
import logging
import os

LOG_LVL_INFO = logging.INFO
LOG_LVL_DBG = logging.DEBUG
LOG_LVL_WARN = logging.WARNING
LOG_LVL_ERRO = logging.ERROR

# 创建一个日志器
lg_ = logging.getLogger('v2v')
# 清空以前的handler，避免重复打印
if lg_.hasHandlers():
    # Logger is already configured, remove all handlers
    lg_.handlers = []
# 构造一个handler，处理显示打印任务，需要调用方提供格式
log_format_ = '%(asctime)s - [v2v] - %(levelname)s - %(message)s'
formatter = logging.Formatter(log_format_)
file_handler = logging.StreamHandler()      # 可以使用RotatingFileHandler，或者UDP/TCP的handler
file_handler.setFormatter(formatter)

lg_.addHandler(file_handler)
lg_.setLevel(logging.INFO)                  # 发布的时候可以修改这个值以便于抑制过多日志

start_time = time.monotonic()


def logger(name, msg, level=LOG_LVL_INFO, exc_info=None):
    elapsed = time.monotonic() - start_time
    hours = int(elapsed // 60)
    seconds = elapsed - (hours * 60)
    lg_.log(level, f'{name:10} {msg}', exc_info=exc_info)


def log(msg, level=LOG_LVL_INFO):
    pid = os.getpid()
    logger(name=pid, msg=msg, level=level)


def get_v2v_logger():
    return lg_


def get_v2v_logger_formatter():
    return log_format_
