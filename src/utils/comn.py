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

import json
import time

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 下面二个为全局变量
_u_base_url = None
# 旋转预置位后，需要等待的时间。为了摄像头能自动对焦或旋转到位
_u_ptz_delay = 30


def set_common_cfg(cfg):
    global _u_base_url
    global _u_ptz_delay

    _u_base_url = cfg['media_service']
    _u_ptz_delay = cfg['ipc_ptz_delay']


def replace_non_ascii(x):
    return ''.join(i if ord(i) < 128 else '_' for i in x)


def run_to_viewpoints(devid, channelid, presetid, burl=None):
    global _u_base_url
    global _u_ptz_delay
    ret = None

    try:
        if burl:
            _u_base_url = burl
        payload = {'viewpoint': presetid}
        _post_url = f'{_u_base_url}/api/v1/ptz/front_end_command/{devid}/{channelid}'
        resp = requests.post(_post_url, data=payload, verify=False)
        if resp.status_code == 200:
            time.sleep(_u_ptz_delay)
            ret = True
    except KeyError:
        pass
    finally:
        return ret


def get_url(devid, channelid, burl=None):
    ret = None
    global _u_base_url
    try:
        if burl:
            _u_base_url = burl
        url = f'{_u_base_url}/api/v1/ptz/streaminfo'
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
    global _u_base_url
    try:
        if burl:
            _u_base_url = burl
        url = f'{_u_base_url}/api/v1/ptz/streaminfo'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['channels']
    except KeyError:
        pass
    finally:
        return resp


def get_presets(devid, channelid, burl=None):
    resp = None
    global _u_base_url
    try:
        if burl:
            _u_base_url = burl
        url = f'{_u_base_url}/api/v1/ptz/front_end_command/{devid}/{channelid}'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['presetlist']
    except KeyError:
        pass
    finally:
        return resp
