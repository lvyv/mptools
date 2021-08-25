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
ai module
=========================

Feed AI meter picture one by one and get recognized results.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import io
import requests
from matplotlib import pyplot as plt
from utils import bus, comn
from core.procworker import ProcWorker


class AiWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q

    def main_func(self, event=None, *args):
        # 全速
        pic = self.in_q_.get()
        buf = io.BytesIO()
        plt.imsave(buf, pic['frame'], format='png')
        image_data = buf.getvalue()
        vp = pic['channel']
        name = vp['name']
        rest = vp['ai_service']
        files = {'upfile': (comn.replace_non_ascii(name), image_data, 'image/png')}
        resp = requests.post(rest, files=files, verify=False)  # data=image_data)
        self.out_q_.put(resp.content)

        return False
