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
common module
=========================

Some common function and tools of the project.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0
import time

import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from utils.config import ConfigSet

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# FIXME:这个地方应该改为从主进程获取配置，主进程是唯一来源，子进程避免直接操作文件系统
# baseurl_ = 'https://127.0.0.1:7180'
baseurl_ = ConfigSet.get_cfg()['media_service']
# how many seconds we should wait for ptz complete its operation.
ipc_ptz_delay_ = ConfigSet.get_cfg()['ipc_ptz_delay']


def set_common_cfg(cfg):
    global baseurl_
    global ipc_ptz_delay_
    baseurl_ = cfg['media_service']
    ipc_ptz_delay_ = cfg['ipc_ptz_delay']


def replace_non_ascii(x): return ''.join(i if ord(i) < 128 else '_' for i in x)


def run_to_viewpoints(devid, channelid, presetid, burl=None):
    ret = None
    global baseurl_
    try:
        if burl:
            baseurl_ = burl
        payload = {'viewpoint': presetid}
        resp = requests.post(f'{baseurl_}/api/v1/ptz/front_end_command/{devid}/{channelid}',
                             data=payload, verify=False)
        if resp.status_code == 200:
            time.sleep(ipc_ptz_delay_)
            ret = True
    except KeyError:
        pass
    finally:
        return ret


def get_url(devid, channelid, burl=None):
    ret = None
    global baseurl_
    try:
        if burl:
            baseurl_ = burl
        url = f'{baseurl_}/api/v1/ptz/streaminfo'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['channels']
        result = list(filter(lambda r: r['deviceid'] == devid and r['channelid'] == channelid, resp))
        if len(result) > 0:
            ret = result[0].get('url')
        # for item in resp:
        #     if item['deviceid'] == devid and item['channelid'] == channelid:
        #         resp = item['url']
    except KeyError:
        pass
    finally:
        return ret


def get_urls(burl=None):
    resp = None
    global baseurl_
    try:
        if burl:
            baseurl_ = burl
        url = f'{baseurl_}/api/v1/ptz/streaminfo'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['channels']
    except KeyError:
        pass
    finally:
        return resp


def get_presets(devid, channelid, burl=None):
    resp = None
    global baseurl_
    try:
        if burl:
            baseurl_ = burl
        url = f'{baseurl_}/api/v1/ptz/front_end_command/{devid}/{channelid}'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['presetlist']
    except KeyError:
        pass
    finally:
        return resp


# def frame_get(rtsp):
#     try:
#         cap_status, cap = video_capture_open(rtsp)
#         if not cap_status:
#             print(cap_status, cap)
#             return cap
#         while True:
#             ret, image_frame = cap.read()
#             cv2.imshow("res", image_frame)
#             cv2.waitKey(3)
#             if not ret:
#                 continue
#             image = cv2.imencode('.png', image_frame)[1]
#             image_base64_data = str(base64.b64encode(image))[2:-1]
#             return image_base64_data
#     except Exception as err:
#         print(err)
#         pass
