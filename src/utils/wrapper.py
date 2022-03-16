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
import cv2
import time
import threading
from utils import log


# -- Process Wrapper
def daemon_wrapper(proc_worker_class, name, **kwargs):
    ret = 0
    try:
        pid = os.getpid()
        proc_worker = proc_worker_class(f'{name}-{pid}', None, None, kwargs)
        ret = proc_worker.run()
    except KeyboardInterrupt:
        pass
    except RuntimeError as err:
        log.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
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
        proc_worker = proc_worker_class(f'{name}({pid})', in_q, out_q, dicts, **kwargs)
        ret = proc_worker.run()
    except KeyboardInterrupt:
        pass
    except RuntimeError as err:
        log.log(f'{err}', level=log.LOG_LVL_ERRO)
    return ret


class MyThread(threading.Thread):
    def __init__(self, target, args=()):
        super(MyThread, self).__init__()
        self.func = target
        self.args = args
        self.result = None

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception as err:
            return None


# Decorator to limit the actual request time or function execution time
def limit_decor(limit_time):
    """
    :param limit_time: Set the maximum allowable execution time, unit: second
    :return: Untimed returns the value of the decorated function; timed out returns None
    """
    def functions(func):
        def run(*params):
            thre_func = MyThread(target=func, args=params)
            # The thread method terminates when the main thread terminates (exceeds its length)
            thre_func.setDaemon(True)
            thre_func.start()
            # Count the number of segmental slumbers
            sleep_num = int(limit_time // 1)
            sleep_nums = round(limit_time % 1, 1)
            # Sleep briefly several times and try to get the return value
            for i in range(sleep_num):
                time.sleep(1)
                infor = thre_func.get_result()
                if infor:
                    return infor
            time.sleep(sleep_nums)
            # Final return value (whether or not the thread has terminated)
            if thre_func.get_result():
                return thre_func.get_result()
            else:
                return False, None  # Timeout returns can be customized

        return run

    return functions


TIME_LIMITED: int = 10


def get_picture_size(path2pic):
    # width, height = (0, 0)
    height, width, channel = cv2.imread(path2pic).shape
    return width, height
