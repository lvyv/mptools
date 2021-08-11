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
mock module
=========================

接口测试，用于视频调度软件的接口测试仿真.
"""

# Author: Awen <26896225@qq.com>
# License: MIT

from fastapi import FastAPI, Form, UploadFile, File
import uvicorn


def call_aimeter(contents):
    # print(contents)
    ret = [
        {'id': 1, 'key1': 31.2, 'loc': [14, 23]},
        {'id': 2, 'key2': 20, 'loc': [102, 538]}
    ]
    return ret


def call_objcounting(contents):
    # print(contents)
    ret = [
        {'id': 1, 'person': 12},
        {'id': 2, 'car': 1}
    ]
    return ret


def call_indicator_freq(contents):
    # print(contents)
    ret = [
        {'id': 1, 'error_led': 3},          # 3 表示3Hz
        {'id': 2, 'power_led': -1},         # -1 表示常亮
        {'id': 3, 'communicate_led': 0}     # 0 表示常灭
    ]
    return ret


app = FastAPI()


# router functions section
@app.post("/api/ptz/front_end_command/{deviceid}/{channelid}")
async def zoom_to_postion(deviceid: str, channelid: str, viewpoint: str = Form(...)):
    """模拟视频调度的跳转到预置点接口"""
    item = {"deviceid": deviceid, "channelid": channelid, "cmdCode": 130, "parameter1": 0, "parameter2": viewpoint}
    print(f"Zoom to: {item}")
    return item


@app.post("/meter_recognization/")
async def meter_recognization(upfile: UploadFile = File(...)):
    print(upfile.filename, upfile.content_type)
    contents = upfile.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_aimeter(contents)
    return ret


@app.post("/object_counting/")
async def object_counting(upfile: UploadFile = File(...)):
    print(upfile.filename, upfile.content_type)
    contents = upfile.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_objcounting(contents)
    return ret


@app.post("/indicator_frequency/")
async def indicator_frequency(upfile: UploadFile = File(...)):
    print(upfile.filename, upfile.content_type)
    contents = upfile.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_indicator_freq(contents)
    return ret


if __name__ == '__main__':
    # uvicorn.run(app, host="0.0.0.0", port=21900)
    uvicorn.run(app,
                host="0.0.0.0",
                port=21900,
                ssl_keyfile="localhost.key",
                ssl_certfile="localhost.crt"
                )
