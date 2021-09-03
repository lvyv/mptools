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
# import json
import cv2
from matplotlib import cm, pyplot as plt
from numpy import array
from utils import bus, comn
from core.procworker import ProcWorker


class AiWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q

    def plc_sub_image(self, image_data, template):
        image_scale = (32, 32)
        # image_data = plt.imread(buf, format='jpg')
        image_size = image_data.shape
        image_list = []
        # 彩色图像转灰度图像
        image_gray = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY) if len(image_size) == 3 else image_data
        for index, res in enumerate(template):
            pos_int = [int(x) for x in res['pos']]
            crop_img = image_gray[pos_int[1]:pos_int[3], pos_int[0]:pos_int[2]]
            crop_img_normal = cv2.resize(crop_img, image_scale, cv2.INTER_LINEAR)
            image_list.extend(crop_img_normal)
            plc_det_adjust = [0, image_scale[1] * index, image_scale[0] - 1,
                              image_scale[1] * (index + 1) - 1]
            template[index]['pos'] = plc_det_adjust
        return array(image_list), template

    def main_func(self, event=None, *args):
        """
        ai进程主要工作函数，收取队列中图像和任务信息，并调用ai引擎进行处理。
        队列中的pic包含：task和frame数据。frame是图像原始ndarray，task项数据结构如下。
        {'seconds': 5,
         'area_of_interest': [{'name': 'xx', 'type': '', 'score': None, 'pos': [180, 80, 290, 150], 'value': None}],
         'ai_service': '/api/v1/ai/person'
        }

        :param event:
        :param args:
        :return:
        """
        # 全速
        pic = self.in_q_.get()

        task = pic['task']
        fid = pic['fid']
        fps = pic['fps']
        frame = pic['frame']

        rest = task['ai_service']
        template_in = task['area_of_interest']

        buf = io.BytesIO()

        template = None
        if '/api/v1/ai/plc' == rest:
            sub_image, template = self.plc_sub_image(frame, template_in)
            plt.imsave(buf, sub_image, format='jpg', cmap=cm.gray)
        else:
            plt.imsave(buf, pic['frame'], format='jpg')
        image_data = buf.getvalue()

        files = {'files': (comn.replace_non_ascii(f'{fid}-{fps}'), image_data, 'image/jpg')}
        payload = {'cfg_info': str(template)}

        resp = requests.post(rest, files=files, data=payload, verify=False)
        result = resp.content.decode('utf-8')
        self.out_q_.put(resp.content)
        self.log(result)

        return False
