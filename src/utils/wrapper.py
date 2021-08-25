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
wrapper module
=========================

wrapper function for multiprocessing pool.
multiprocessing的进程池库有一个问题：如果对象不在import的模块，它可能无法识别。
https://stackoverflow.com/questions/41385708/multiprocessing-example-giving-attributeerror
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import os


# -- Process Wrapper
def daemon_wrapper(proc_worker_class, name, **kwargs):
    ret = 0
    try:
        pid = os.getpid()
        proc_worker = proc_worker_class(f'{name}-{pid}', None, None, kwargs)
        ret = proc_worker.run()
    except KeyboardInterrupt:
        pass
    return ret


def proc_worker_wrapper(proc_worker_class, name, in_q=None, out_q=None, dicts=None, **kwargs):
    """
    子进程的入口点。

    :param proc_worker_class: 类名。
    :param name: 对象名。
    :param in_q: 输入数据队列，子进程之间数据通道。
    :param out_q: 输出数据队列，子进程之间数据通道。
    :param dicts: 额外参数。
    :param kwargs: 其它参数。
    :return: 子进程退出码：0为正常，-1为错误。
    """
    ret = 0
    try:
        pid = os.getpid()
        proc_worker = proc_worker_class(f'{name}-{pid}', in_q, out_q, dicts, **kwargs)
        ret = proc_worker.run()
    except KeyboardInterrupt:
        pass
    return ret
