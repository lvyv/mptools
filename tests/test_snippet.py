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

测试multiprocessing库的一些用法及python code snippet.
"""

# Author: Awen <26896225@qq.com>
# License: MIT

from multiprocessing import Pool

import time

work = [("A", 5), ("B", 2), ("C", 1), ("D", 3)]


def work_log(name, ts):
    print(f" Process {name} waiting {ts} seconds.")
    time.sleep(ts)
    print(f" Process {name} Finished.")


def pool_handler():
    p = Pool(2)
    p.starmap(work_log, [it for it in work])


def test_kwargs(**kwargs):
    for k, v in kwargs.items():
        print(k, v)


def test_arg(*args, **kwargs):
    test_kwargs(**kwargs)
    for it in args:
        print(it)
    return True


if __name__ == '__main__':
    # pool_handler()
    # test_arg('a', 1, key3=3, key5=5, key4=4)
    import ffmpeg

    in_file = ffmpeg.input('in.mp4')
    overlay_file = ffmpeg.input('overlay.png')
    (
        ffmpeg
            .concat(
            in_file.trim(start_frame=10, end_frame=20),
            in_file.trim(start_frame=30, end_frame=40),
        )
            .overlay(overlay_file.hflip())
            .drawbox(50, 50, 120, 120, color='red', thickness=5)
            .output('out.mp4')
            .run()
    )