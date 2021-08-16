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
rest module
=========================

Provide web api access points.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0


import uvicorn
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every

from utils import bus
from core.procworker import ProcWorker


app_ = FastAPI(
    title="视频图像智能分析软件",
    description="视频图像智能分析软件对外发布的RESTful API接口",
    version="2.2.0", )
rest_proc_ = None
counter_ = 0


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


@app_.post("/items/")
async def create_item(item: Item):
    rest_proc_.send_cmd(bus.EBUS_TOPIC_MAIN, 'hello from rest!') # noqa
    return item


class Switch(BaseModel):
    cmd: str = 'start'


@app_.post("/subprocess/")
async def create_item(item: Switch):
    """统一关闭或启动rtsp，ai，mqtt子进程"""
    cmds = ['start', 'stop']
    if item.cmd in cmds:
        rest_proc_.send_cmd(bus.EBUS_TOPIC_MAIN, item.cmd) # noqa
    return item


@app_.on_event("startup")
@repeat_every(seconds=1, wait_first=True)
def periodic():
    """周期性任务，用于读取系统状态和实现探针程序数据来源的提取"""
    global counter_
    counter_ += 1
    # rest_proc_.log(f'{counter_}') # noqa


class RestWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_REST, dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q

        self.port_ = None
        self.ssl_keyfile_ = None
        self.ssl_certfile_ = None

        for key, value in dicts.items():
            if key == 'port':
                self.port_ = value
            elif key == 'ssl_keyfile':
                self.ssl_keyfile_ = value
            elif key == 'ssl_certfile':
                self.ssl_certfile_ = value

    def run(self, *kwargs):
        global rest_proc_
        rest_proc_ = self
        uvicorn.run(app_,       # noqa 标准用法
                    host="0.0.0.0",
                    port=self.port_,
                    ssl_keyfile=self.ssl_keyfile_,
                    ssl_certfile=self.ssl_certfile_,
                    log_level='info'
                    )
