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
import os
import datetime
# import time
import io
import requests
import json
import cv2

from matplotlib import cm, pyplot as plt
from numpy import array
from utils import bus, comn, log
from core.procworker import ProcWorker
from utils.config import ConfigSet
from PIL import Image, ImageDraw, ImageFont


class UrlStatisticsHelper:
    """对于url地址失效的简单处理.

    如果ai进程的url服务暂时失效，会导致调用方阻塞很久，从而让整个流水线出现阻塞。
    因此加入一个处罚机制，如果连续多次（3）调用失败，将放入黑名单，等持续调用很多次J（20）后再放出来。
    """
    def __init__(self, criterion=20):
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
    def draw_text(self, img, pos, text):
        # write Chinese.
        img_pil = Image.fromarray(img)
        draw = ImageDraw.Draw(img_pil)
        draw.text(pos, text, font=self.font_, fill=(0, 0, 255, 5))
        return array(img_pil)

    def image_post_process(self, frame, reqid, res):
        """
        后处理图片，主要完成图片识别结果的标记和存盘。
        """
        if reqid:
            jso = json.loads(res.decode('utf-8'))
            aitype = jso['api_type']
            objs = jso['obj_info']
            if aitype == 'Person':
                ypos = 0
                for item in objs:
                    ypos = ypos + 50
                    cnt = None
                    if item['value']:
                        cnt = int(float(item["value"]))
                    if cnt is None:
                        continue
                    # cv2.putText(frame, f'{item["type"]}: {cnt}',
                    #             (10, ypos), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1, lineType=cv2.LINE_AA)
                    frame = self.draw_text(frame, (10, ypos), f'{item["type"]}: {cnt}')
                    pos = item['pos']
                    pts = [(int(float(pos[i])), int(float(pos[i + 1]))) for i in range(0, len(pos), 2)]
                    for iii in range(0, cnt*2, 2):
                        cv2.rectangle(frame, pts[iii], pts[iii+1], (255, 0, 0), 2)
            elif aitype == 'plc':
                ypos = 0
                for item in objs:
                    ypos = ypos + 50
                    # cv2.putText(frame, f'{item["name"]}: {item["value"]}',
                    #             (10, ypos), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1, lineType=cv2.LINE_AA)
                    frame = self.draw_text(frame, (10, ypos), f'{item["name"]}: {item["value"]}')
            elif aitype == 'panel':
                for item in objs:
                    pos = item['pos']
                    pts = [(int(float(pos[i])), int(float(pos[i+1]))) for i in range(0, len(pos), 2)]
                    cv2.rectangle(frame, pts[0], pts[1], (0, 0, 255), 2)
                    txtpos = [pts[1][0], pts[1][1]]
                    # cv2.putText(frame, f'{item["type"]}: {item["value"]}',
                    #             txtpos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, lineType=cv2.LINE_AA)  # pts[0]
                    frame = self.draw_text(frame, (txtpos[0], txtpos[1]), f'{item["type"]}: {item["value"]}')
            else:
                self.log(f'ai模型类型不支持：{aitype}', level=log.LOG_LVL_WARN)
            # buf = io.BytesIO()
            # plt.imsave(buf, frame, format='jpg', cmap=cm.gray)  # noqa
            # dt = datetime.datetime.fromtimestamp(reqid / 1000)
            # fn = dt.strftime('%Y-%m-%d-%H-%M-%S')
            # os.makedirs(os.path.dirname(filename), exist_ok=True)
            prefix = datetime.datetime.fromtimestamp(reqid / 1000).strftime('%Y-%m-%d')
            filename = f'{self.nvr_samples_}airesults/{prefix}/{reqid}.jpg'
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            if reqid % 50 == 0:    # 50抽1
                cv2.imwrite(f'{filename}', frame)
            if self.showimage_:
                cv2.imshow(self.name, frame)
                cv2.waitKey(50)

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
        # 识别结果保存到文件服务器
        self.fsvr_url_ = None
        self.nvr_samples_ = None
        # 是否显示窗体展示识别结果
        self.showimage_ = False
        # 出现调用连接失败等的url需要被记录，下次再收到这样的url要丢弃
        self.badurls_ = UrlStatisticsHelper()
        self.font_ = ImageFont.truetype('fonts/cf.ttf', size=24)

    def startup(self):
        self.log(f'{self.name} started......')
        cfg = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': self.name})
        mqttcfg = cfg['mqtt_svrs'][0]
        self.fsvr_url_ = mqttcfg['fsvr_url']
        self.nvr_samples_ = cfg['nvr_samples']

        self.showimage_ = ConfigSet.get_base_cfg_obj()['showimage']

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
            requestid = pic['requestid']
            rest = f'{task["ai_service"]}'
            template_in = task['area_of_interest']
            if self.badurls_.get_cnts(rest) < 3:    # 事不过三。
                buf = io.BytesIO()
                # template = None
                if '/api/v1/ai/plc' in rest:
                    # self.log(f'in:{template_in}')
                    sub_image, template = self.plc_sub_image(frame, template_in)
                    plt.imsave(buf, sub_image, format='jpg', cmap=cm.gray)  # noqa
                    # cv2.imwrite(f'{self.name}-plc-extract.jpg', sub_image)
                    # self.log(f'plc:{template}--{rest}')
                    payload = {'cfg_info': str(template), 'req_id': requestid}
                else:
                    plt.imsave(buf, pic['frame'], format='jpg')
                    # self.log(f'panel & others:{template_in}--{rest}')
                    payload = {'cfg_info': str(template_in), 'req_id': requestid}
                image_data = buf.getvalue()
                files = {'files': (comn.replace_non_ascii(f'{fid}-{fps}'), image_data, 'image/jpg')}
                rest = f'{rest}/?req_id={requestid}'
                self.log(f'Going to call {rest}.')  # by {template_in}.')
                resp = requests.post(rest, files=files, data=payload, verify=False)
                if resp.status_code == 200:
                    # result = resp.content.decode('utf-8')
                    self.log(f'The size of vector queue between ai & mqtt is: {self.out_q_.qsize()}.')
                    self.out_q_.put(resp.content)
                    self.image_post_process(frame, requestid, resp.content)
                else:
                    self.log(f'ai服务访问失败，错误号：{resp.status_code}', level=log.LOG_LVL_WARN)
            else:
                self.badurls_.waitforrecover(rest)     # 并不真的去访问该rest，而是要等累计若干次以后再说。
        except requests.exceptions.ConnectionError as err:
            # 把出错的url取出来记下，但是要去掉/?req_id
            self.badurls_.add(rest.split('/?req_id=')[0])     # noqa
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
        except Exception as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
        finally:
            return False
