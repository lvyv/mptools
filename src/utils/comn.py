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


def replace_non_ascii(x):
    return ''.join(i if ord(i) < 128 else '_' for i in x)


def run_to_viewpoints(devid, channelid, presetid, spdd_url, ptz_delay=30):
    """
    调用SPDD接口旋转预置位
    devid: 设备编号
    channelid: 通道编号
    presetid: 预置位编号
    spdd_url: SPDD接口地址
    ptz_delay: 旋转预置位后，等待时间
    """
    ret = None

    try:
        payload = {'viewpoint': presetid}
        _post_url = f'{spdd_url}/api/v1/ptz/front_end_command/{devid}/{channelid}'
        resp = requests.post(_post_url, data=payload, verify=False)
        if resp.status_code == 200:
            # 由调用者控制延时
            # time.sleep(ptz_delay)
            ret = True
    except KeyError:
        pass
    finally:
        return ret


def get_rtsp_url(devid, channelid, spdd_url):
    ret = None
    try:
        url = f'{spdd_url}/api/v1/ptz/streaminfo'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['channels']
        result = list(filter(lambda r: r['deviceid'] == devid and r['channelid'] == channelid, resp))
        if len(result) > 0:
            ret = result[0].get('url')
    except KeyError:
        pass
    finally:
        return ret


def get_urls(spdd_url):
    resp = None
    try:
        url = f'{spdd_url}/api/v1/ptz/streaminfo'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['channels']
    except KeyError:
        pass
    finally:
        return resp


def get_presets(devid, channelid, spdd_url):
    resp = None
    try:
        url = f'{spdd_url}/api/v1/ptz/front_end_command/{devid}/{channelid}'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['presetlist']
    except KeyError:
        pass
    finally:
        return resp
