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
from fastapi import FastAPI
from pydantic import BaseModel

from utils import bus
from core.procworker import ProcWorker


app_ = FastAPI(
    title="视频图像智能分析软件",
    description="视频图像智能分析软件对外发布的RESTful API接口",
    version="2.2.0", )


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


@app_.post("/items/")
async def create_item(item: Item):
    return item


class RestWorker(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_REST, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.pt_ = 29080
        for key, value in kwargs.items():
            if key == 'port':
                self.pt_ = value
                break

    def run(self, *kwargs):
        uvicorn.run(app_, host="0.0.0.0", port=self.pt_)
