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

test entry point.
"""

# Author: Awen <26896225@qq.com>
# License: MIT

from multiprocessing import Manager, Pool


def get_data(pageNo, q):
    print(q.get())


if __name__ == "__main__":
    m = Manager()
    q = m.Queue()
    p = {}
    no_pages = 5
    pool_tuple = [(x, q) for x in range(1, no_pages)]
    q.put(1)
    q.put(2)
    q.put(3)
    q.put(4)
    q.put(5)
    with Pool(processes=3) as pool:
        pool.starmap(get_data, pool_tuple)
    # for i in range(1, no_pages):
    #     print("result", i, ":", q.get())
    pool.close()
    pool.join()