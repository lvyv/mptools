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
V2VErr module
=========================

V2VErr module defines all customer error classes.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0


class V2VConfigurationChangedError(Exception):
    """Raised when some configuration info is updated while the processes are running.

    Attributes:
        message -- explanation of what is going on.
    """
    def __init__(self, message):
        super().__init__(self)
        self.message_ = message

    def __str__(self):
        return self.message_


class V2VConfigurationIllegalError(Exception):
    """Raised when configuration items are illegal.

    Attributes:
        message -- explanation of what is going on.
    """

    def __init__(self, message):
        super().__init__(self)
        self.message_ = message

    def __str__(self):
        return self.message_


class V2VTaskNullRtspUrl(Exception):
    """Raised when no more rtsp task could be assigned.

    Attributes:
        message -- explanation of what is going on.
    """

    def __init__(self, message):
        super().__init__(self)
        self.message_ = message

    def __str__(self):
        return self.message_


class V2VTaskExitProcess(Exception):
    """Raised when need exit process.

    Attributes:
        message -- explanation of what is going on.
    """

    def __init__(self, message):
        super().__init__(self)
        self.message_ = message

    def __str__(self):
        return self.message_


if __name__ == '__main__':
    try:
        raise V2VConfigurationChangedError(f'进程运行时，相关配置文件更新错误触发')
    except V2VConfigurationChangedError as e:
        print(e)
    print('Normal exit.')
