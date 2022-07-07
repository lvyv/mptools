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
spdd module
=========================

与视频调度管理软件的功能接口

"""

import json
from third_api.http_request import HttpRequest


def get_rtsp_url(deviceid, channelid, base_url) -> str or None:
    """
    根据设备ID和通道ID，获取对应的RTSP地址.
    deviceid: 设备编号
    channelid: 通道编号
    base_url: SPDD接口地址

    返回rtsp地址，或None.
    """
    _rtsp_url = None

    # 检验输入参数
    if deviceid is None or channelid is None or base_url is None:
        return _rtsp_url
    if len(deviceid) < 1 or len(channelid) < 1 or len(base_url) < 7:
        return _rtsp_url

    # 获取设备下的所有通道地址列表
    _url_list = get_urls(base_url, deviceid)
    if _url_list is None:
        return _rtsp_url
    # 根据传入的通道号进行匹配
    for _obj in _url_list:
        _cid = _obj.get("channelid", None)
        if _cid is None:
            continue
        if _cid == channelid:
            _rtsp_url = _obj.get("url", None)

    return _rtsp_url


def _get_channel_info(base_url, deviceid=None, limit=200) -> list or None:
    _url_list = None

    # 请求API接口
    _http_obj = HttpRequest()
    if deviceid is None:
        _url = f'{base_url}/api/channel/list?limit={limit}'
    else:
        _url = f'{base_url}/api/channel/list?deviceId={deviceid}&limit={limit}'
    _content = _http_obj.http_timeout_get(_url)
    if _content is None:
        return _url_list

    # 检验返回值
    try:
        _http_data = json.loads(_content)
    except json.decoder.JSONDecodeError:
        # 如果JSON数据格式错误
        return _url_list
    finally:
        _http_obj = None

    _url_data_list = _http_data.get("data", None)
    if _url_data_list is None or len(_url_data_list) < 1:
        return _url_list
    else:
        _url_list = _url_data_list
    return _url_list


def get_urls(base_url, deviceid=None) -> list or None:
    """
    返回所有摄像头的地址列表.如果带了deviceid，则只返回该设备下的所有摄像头地址，否则返回平台上所有有通道地址.
    注意：该接口可能返回大量无用的通道数据，尤其当SPDD对接了第三方监控系统的时候.
    deviceid: 设备编号
    base_url: SPDD接口地址

    接口返回数据格式：
    [
        {'deviceid': '34020000001320000001', 'channelid': '34020000001310000001', 'desc': '标准测试视频',
                 'url': 'rtsp://127.0.0.1:7554/live/main'}
    ]
    """
    _url_list = None

    # 检查输入参数
    if base_url is None or len(base_url) < 7:
        return _url_list

    # 请求API接口
    _url_data_list = _get_channel_info(base_url, deviceid)
    if _url_data_list is None:
        print("从SPDD通道接口返回的数据为空.")
        return _url_list

    print("从SPDD通道接口获取的通道数量：", len(_url_data_list))
    for _obj in _url_data_list:
        # 取值
        _did = _obj.get("deviceId", None)
        _cid = _obj.get("channelId", None)
        _desc = _obj.get("aliasName", None)
        _ip = _obj.get("ipAddress", None)
        _name = _obj.get("smartUsername", None)
        _pwd = _obj.get("smartPassword", None)
        # 校验值
        if _did is None or _cid is None:
            print("设置ID或通道ID错误.")
            continue
        if _ip is None or len(_ip) < 4:
            print("摄像头IP地址错误.")
            continue
        if _name is None or _pwd is None or len(_name) < 1 or len(_pwd) < 1:
            print("未配置用户名和密码.")
            continue
        # 优先使用别名，然后是name
        if _desc is None or len(_desc) < 1:
            _desc = _obj.get("name", '未命名')
        # {'deviceid': '34020000001320000001', 'channelid': '34020000001310000001', 'desc': '标准测试视频',
        #                  'url': 'rtsp://127.0.0.1:7554/live/main'}
        # 转换返回值
        if _url_list is None:
            _url_list = list()
        # rtsp构造：rtsp://username:pwd@ip/cam/realmonitor?channel=1&subtype=0
        _rtsp_url = f'rtsp://{_name}:{_pwd}@{_ip}/cam/realmonitor?channel=1&subtype=0'
        _url_list.append({"deviceid": _did, "channelid": _cid, "desc": _desc, "url": _rtsp_url})
    print("V2V解析后，生成的通道数量：", 0 if _url_list is None else len(_url_list))
    return _url_list


def get_presets(deviceid, channelid, base_url) -> list or None:
    """
    根据设备ID，通道ID查询预置位列表。
    deviceid: 设备编号
    channelid: 通道编号
    base_url: SPDD接口地址

    该接口返回的数据格式：
    [
        {'presetid': '1', 'presetname': '开机大门'},
    ]
    """
    _preset_list = None

    # 校验输入参数
    if deviceid is None or channelid is None or base_url is None:
        return _preset_list
    if len(deviceid) < 1 or len(channelid) < 1 or len(base_url) < 7:
        return _preset_list

    # 获取接口值，默认有超时
    _http_obj = HttpRequest()
    _url = f'{base_url}/api/ptz/preset/query/{deviceid}/{channelid}'
    _content = _http_obj.http_timeout_get(_url)
    if _content is None:
        return _preset_list

    # 解析返回值
    try:
        _http_data = json.loads(_content)
    except json.decoder.JSONDecodeError:
        # 如果JSON数据格式错误
        return _preset_list
    finally:
        _http_obj = None

    # 校验是否有data元素，并且数据不为空
    _data_list = _http_data.get("data", None)
    if _data_list is None or len(_data_list) < 1:
        return _preset_list

    # 如果全部正确，将spdd返回的数据结构转换为V2V需要的数据结构
    """
    视频调度管理软件接口返回的数据格式：
    [{
        "number": "1",
        "name": "拍显示器"
    }, {
        "number": "2",
        "name": "拍窗帘"
    }]
    """
    for _obj in _data_list:
        _id = _obj.get("number", None)
        _name = _obj.get("name", None)
        # 只使用number, name都具备的数据，否则认为脏数据
        if _id is None or _name is None:
            continue
        if _preset_list is None:
            _preset_list = list()
        _preset_list.append({"presetid": _id, "presetname": _name})
    return _preset_list


def run_to_viewpoints(deviceid, channelid, presetid, base_url, ptz_delay=30) -> bool:
    """
    调用SPDD接口旋转预置位。
    deviceid: 设备编号
    channelid: 通道编号
    presetid: 预置位编号
    base_url: SPDD接口地址
    ptz_delay: 旋转预置位后，等待时间，该参数弃用

    调用接口成功，返回true，否则false.
    """
    _ret = False

    # 检验输入参数
    if deviceid is None or channelid is None or presetid is None or base_url is None:
        return _ret
    if len(deviceid) < 1 or len(channelid) < 1 or len(presetid) < 1 or len(base_url) < 7:
        return _ret

    # 构造url
    _url = f'{base_url}/api/v1/ptz/front_end_command/{deviceid}/{channelid}?viewpoint={presetid}'

    # 调用api
    _http_obj = HttpRequest()
    _content = _http_obj.http_timeout_get(_url)
    if _content is None:
        return _ret

    # 校验返回值
    try:
        _http_data = json.loads(_content)
    except json.decoder.JSONDecodeError:
        # 如果JSON数据格式错误
        return _ret
    finally:
        _http_obj = None

    # 校验返回值是不是0
    _ret_val = _http_data.get("returnFlag", 1)
    if _ret_val == 0:
        _ret = True

    return _ret


if __name__ == "__main__":
    # 获取指定设备和通道的RTSP地址
    _r = get_rtsp_url("34020000001320000001", "34020000001310000001", "http://192.168.101.79:58068")
    print(_r)

    # 获取所有通道地址列表
    # _r = get_urls("http://192.168.101.79:58068")
    _r = get_urls("http://192.168.101.79:58068", "34020000001320000001")
    print(_r)

    # 获取所有预置位列表
    _r = get_presets("34020000001320000001", "34020000001310000001", "http://192.168.101.79:58068")
    print(_r)
    if _r is not None:
        _preset = _r[0]["presetid"]

    # 调用预置位列表
    # _r = run_to_viewpoints("34020000001320000001", "34020000001310000001", _preset, "http://192.168.101.79:58068")
    # print(_r)
