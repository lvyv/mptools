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

import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def replace_non_ascii(x): return ''.join(i if ord(i) < 128 else '_' for i in x)


def run_to_viewpoints(devid, channelid, presetid):
    ret = None
    try:
        payload = {'viewpoint': presetid}
        resp = requests.post(f'https://127.0.0.1:7180/api/ptz/front_end_command/{devid}/{channelid}',
                             data=payload, verify=False)
        if resp.status_code == 200:
            ret = True
    except KeyError:
        pass
    finally:
        return ret


def get_url(devid, channelid):
    resp = None
    try:
        url = f'https://127.0.0.1:7180/api/ptz/streaminfo'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['channels']
        for item in resp:
            if item['deviceid'] == devid and item['channelid'] == channelid:
                resp = item['url']
    except KeyError:
        pass
    finally:
        return resp


def get_presets(devid, channelid):
    resp = None
    try:
        url = f'https://127.0.0.1:7180/api/ptz/front_end_command/{devid}/{channelid}'
        resp = requests.get(url, verify=False)
        resp = json.loads(resp.content)['presetlist']
    except KeyError:
        pass
    finally:
        return resp
