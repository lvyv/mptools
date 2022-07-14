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

import datetime
import io
import json
import os
import queue
import time
from pathlib import Path

import cv2
import requests
from PIL import Image, ImageDraw, ImageFont
from matplotlib import cm, pyplot as plt
from numpy import array

from core.procworker import ProcWorker
from third_api.http_request import HttpRequest
from utils import bus, comn, log, V2VErr


class AiWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q
        # 识别结果保存到文件服务器
        self._fsvr_url = None
        self._nvr_samples_path = None
        # 是否显示窗体展示识别结果
        self.showimage_ = False
        # 加载字体文件
        _font_path_obj = Path(Path(__file__).parent).joinpath("../fonts/cf.ttf")
        self.font_ = ImageFont.truetype(str(_font_path_obj), size=24)

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
            filename = f'{self._nvr_samples_path}airesults/{prefix}/{reqid}.jpg'
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

    def startup(self, evt=None):
        self.log(f'[AI STARTUP] Enter startup.', level=log.LOG_LVL_INFO)
        # 从主进程获取配置参数
        _v2v_cfg_dict = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': self.name})

        # 校验
        _mqtt_srv_list = _v2v_cfg_dict.get("mqtt_svrs", None)
        if _mqtt_srv_list is None or len(_mqtt_srv_list) < 1:
            raise V2VErr.V2VConfigurationIllegalError("[AI STARTUP] 配置文件错误.")
        self._nvr_samples_path = _v2v_cfg_dict.get('nvr_samples', None)
        if self._nvr_samples_path is None:
            raise V2VErr.V2VConfigurationIllegalError("[AI STARTUP] _nvr_samples_path is None.")

        _mqtt_obj = _mqtt_srv_list[0]
        self._fsvr_url = _mqtt_obj.get('fsvr_url', None)
        if self._fsvr_url is None:
            raise V2VErr.V2VConfigurationIllegalError("[AI STARTUP] _fsvr_url is None.")

        # 从主进程获取配置参数
        _base_cfg_dict = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_basecfg', 'source': self.name})
        self.showimage_ = _base_cfg_dict.get('showimage', False)

    def main_func(self, event=None, *args) -> bool:
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
            pic = self.in_q_.get_nowait()
        except queue.Empty:
            time.sleep(0.01)
            return False

        _http_obj = HttpRequest()
        try:
            _fid = pic['fid']
            _fps = pic['fps']
            _aoi_dict = pic['task']
            _frame_data = pic['frame']
            _requestid = pic['requestid']
            _template_in = _aoi_dict['area_of_interest']
            _ai_http_api_url = f'{_aoi_dict["ai_service"]}'

            buf = io.BytesIO()
            # template = None
            if '/api/v1/ai/plc' in _ai_http_api_url:
                sub_image, template = self.plc_sub_image(_frame_data, _template_in)
                plt.imsave(buf, sub_image, format='jpg', cmap=cm.gray)  # noqa
                payload = {'cfg_info': str(template), 'req_id': _requestid}
            else:
                # 统一传给V2V_AI的图片格式为RGB，2022.3.7
                plt.imsave(buf, pic['frame'][:, :, ::-1], format='jpg')
                payload = {'cfg_info': str(_template_in), 'req_id': _requestid}
            _image_data = buf.getvalue()
            files = {'files': (comn.replace_non_ascii(f'{_fid}-{_fps}'), _image_data, 'image/jpg')}

            # 构造AI请求地址
            _ai_http_api_url = f'{_ai_http_api_url}/?req_id={_requestid}'

            _ai_resp = _http_obj.http_timeout_post(_ai_http_api_url, file=files, data=payload)
            # _ai_resp = requests.post(_ai_http_api_url, files=files, data=payload, verify=False)
            if _ai_resp is not None:
                # self.log(f'The size of vector queue between ai & mqtt is: {self.out_q_.qsize()}.')
                self.log(f'[AI RUN] 调用AI服务接口成功. --> {_ai_http_api_url}.', level=log.LOG_LVL_DBG)
                # 将识别结果放入队列，供MQTT进程消费
                self.out_q_.put_nowait(_ai_resp)
                # 后处理
                self.image_post_process(_frame_data, _requestid, _ai_resp)
            else:
                self.log(f'[AI RUN] 调用AI服务接口失败. --> {_ai_http_api_url}', level=log.LOG_LVL_WARN)
                time.sleep(1)
        except queue.Full:
            self.log("[AI RUN] Vector queue is [FULL], clear it, may lose data.", level=log.LOG_LVL_ERRO)
            self.out_q_.queue.clear()
        except Exception as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
        finally:
            return False

    def shutdown(self):
        pass
