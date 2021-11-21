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
from utils import bus, comn, log
from core.procworker import ProcWorker


class UrlStatisticsHelper:
    def __init__(self, criterion=100):
        self.urls_ = []
        self.criterion_ = criterion     # 连续几次（比如3）访问失败，就不再允许访问，直到发现请求持续超过（100）次，重新放行。

    def add(self, url):
        found = False
        for it in self.urls_:
            if it['url'] == url:
                it['cnt'] += 1
                found = True
                break
        if not found:
            self.urls_.append({'url': url, 'cnt': 1})

    def get_cnts(self, url):
        ret = -1
        for it in self.urls_:
            if it['url'] == url:
                ret = it['cnt']
        return ret

    def waitforrecover(self, url):
        cnt = self.get_cnts(url)
        if cnt < self.criterion_:
            self.add(url)
        else:
            self.freeup(url)

    def freeup(self, url):
        for it in self.urls_:
            if it['url'] == url:
                it['cnt'] = 0   # 刑满释放
                break


class AiWorker(ProcWorker):
    @classmethod
    def plc_sub_image(cls, image_data, template):
        image_scale = (64, 64)
        # image_data = plt.imread(buf, format='jpg')
        image_size = image_data.shape
        image_list = []
        # 彩色图像转灰度图像

        # import joblib
        # joblib.dump(image_data, 'image_data.pkl')
        # joblib.dump(template, 'template.pkl')

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

    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q
        # 出现调用连接失败等的url需要被记录，下次再收到这样的url要丢弃
        self.badurls_ = UrlStatisticsHelper()

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
        try:
            # 全速
            pic = self.in_q_.get()

            task = pic['task']
            fid = pic['fid']
            fps = pic['fps']
            frame = pic['frame']

            rest = task['ai_service']
            template_in = task['area_of_interest']

            if self.badurls_.get_cnts(rest) < 3:    # 事不过三。
                buf = io.BytesIO()
                template = None
                if '/api/v1/ai/plc' in rest:
                    # self.log(f'in:{template_in}')
                    sub_image, template = self.plc_sub_image(frame, template_in)
                    plt.imsave(buf, sub_image, format='jpg', cmap=cm.gray)  # noqa
                    cv2.imwrite(f'{self.name}-plc-extract.jpg', sub_image)
                    self.log(f'plc:{template}--{rest}')
                    payload = {'cfg_info': str(template), 'req_id': None}
                else:
                    plt.imsave(buf, pic['frame'], format='jpg')
                    self.log(f'panel & others:{template_in}')
                    payload = {'cfg_info': str(template_in), 'req_id': None}

                image_data = buf.getvalue()
                files = {'files': (comn.replace_non_ascii(f'{fid}-{fps}'), image_data, 'image/jpg')}

                resp = requests.post(rest, files=files, data=payload, verify=False)
                if resp.status_code == 200:
                    # result = resp.content.decode('utf-8')
                    self.out_q_.put(resp.content)
                else:
                    self.log(f'[{__file__}]{resp.status_code}', level=log.LOG_LVL_ERRO)
            else:
                self.badurls_.waitforrecover(rest)     # 并不真的去访问该rest，而是要等累计若干次以后再说。

        except requests.exceptions.ConnectionError as err:
            self.badurls_.add(rest)     # noqa
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
        except Exception as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
        finally:
            return False
