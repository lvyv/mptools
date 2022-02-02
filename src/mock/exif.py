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
mock module
=========================

接口测试，用于视频调度软件的接口测试仿真.
"""

# Author: Awen <26896225@qq.com>
# License: MIT

from fastapi import FastAPI, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
# , List, Tuple
from utils import log
from typing import List
import uvicorn
import random
# import requests
# import json


def call_aimeter(contents):
    # print(contents)
    if contents:
        pass
    values = ['识别结果：0.223', '识别结果：0.328', '识别结果：1.226899']
    ret = {'req_id': None,
           'api_type': 'panel',
           'obj_info': [{'name': 'OCR_001', 'type': 'OCR', 'score': 0.889299750328064, 'pos': [26, 263, 416, 422],
                         'value': f'{random.choice(values)}',
                         'inter_type': None}],
           'stats_info': None,
           'ET': '(0.146s)'}
    return ret


def call_objcounting(contents):
    if contents:
        pass
    ret = {'req_id': None,
           'api_type': 'Person',
           'obj_info': [{'name': 'CNT_001', 'type': 'COMPUTER', 'score': 0.889299750328064,
                         'pos': (26, 263, 416, 422,  2, 3, 1, 1,    2, 3, 1, 1,),
                         'value': '3',
                         'inter_type': None}],
           'stats_info': None,
           'ET': '(0.146s)'}
    return ret


def call_indicator_freq(contents):
    if contents:
        pass
    ret = {'req_id': None,
           'api_type': 'plc',
           'obj_info': [{'name': 'PLC_001', 'type': 'plc', 'score': 0.889299750328064, 'pos': [26, 263, 416, 422],
                         'value': '0.27',
                         'inter_type': None}],
           'stats_info': None,
           'ET': '(0.146s)'}
    return ret


app = FastAPI()

# 支持跨越
origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# EIF4:REST IOT 外部接口-物联网文件服务器/WS服务（针对实时上传的图片）
# iot图片文件服务
app.mount('/viewport', StaticFiles(directory='upfiles'), name='local')
app.mount('/ui', StaticFiles(directory='../ui'), name='ui')
app.mount('/docs', StaticFiles(directory='../../docs'), name='docs')
app.mount('/static', StaticFiles(directory='../swagger_ui_dep/static'), name='static')


# iot登录
@app.post("/api/v1/auth/login")
async def post_iot_login():
    """模拟物联网登录获取访问令牌接口，有物联网服务器，暂未实现"""
    pass


# iot遥测数据写入
@app.post("/api/v1/{devicetoken}/telemetry")
async def post_iot_telemetry(devicetoken: str):
    """模拟物联网遥测数据推送接口，有物联网服务器，暂未实现"""
    log.log(devicetoken)
    pass


# iot 文件上传
@app.post("/api/v1/uploadfiles")
async def uploadfiles(files: List[UploadFile] = File(...)):
    """模拟物联网文件上传接口"""
    ret = []
    for upfile in files:
        contents = upfile.file.read()
        path = './upfiles/'
        outfile = open(f'{path}{upfile.filename}', 'wb')
        outfile.write(contents)
        outfile.close()
        item = {"id": upfile.filename,
                "url": f'/viewport/{upfile.filename}'}
        ret.append(item)
    return ret


@app.post("/api/v1/uploadfile_with_params")
async def uploadfile_with_params(file: bytes = File(...), jso: str = Form(...)):
    log.log(len(file))
    log.log(jso)
    return {"reply": True}


@app.post("/api/v1/uploadfiles_with_params")
async def uploadfiles_with_params(files: List[UploadFile] = File(...), jsos: str = Form(...)):
    # log.log(len(files[0]))
    for file in files:
        if file.filename == 'iobytes.png':
            with open("abc.png", "wb") as f:
                contents = await file.read()
                f.write(contents)
                f.close()
        # file.close()
    log.log(jsos)

    return {"reply": True}


# EIF5:REST PTZ CNTL 外部接口-视频调度管理软件
@app.get("/api/v1/ptz/streaminfo")
async def stream_info():
    """获取所有的视频通道列表"""
    item = {'version': '1.0.0',
            'channels': [
                {'deviceid': '34020000001320000001', 'channelid': '34020000001310000001', 'desc': '标准测试视频',
                 'url': 'rtsp://127.0.0.1:7554/person'},
                {'deviceid': '44020000001320000001', 'channelid': '44020000001310000001', 'desc': '人员识别',
                 'url': 'rtsp://127.0.0.1:7554/panel'},
                {'deviceid': '54020000001320000001', 'channelid': '54020000001310000001', 'desc': '测试静态仪表识别',
                 'url': 'rtsp://127.0.0.1:7554/plc'},
                {'deviceid': '64020000001320000001', 'channelid': '64020000001310000001', 'desc': 'PLC',
                 'url': 'rtsp://127.0.0.1:7554/main'},
                {'deviceid': '74020000001320000001', 'channelid': '74020000001310000001', 'desc': '前门摄像头',
                 'url': 'rtsp://127.0.0.1:7554/live'}
            ]}
    return item


# 不提供
@app.get("/api/v1/ptz/streaminfo/{desc}")
async def stream_info_by_desc(desc: str):
    """按照对用户有意义的名称，获取视频通道列表"""
    item = {'version': '1.0.0',
            'channels': [
                {'deviceid': '34020000001320000001', 'channelid': '34020000001310000001', 'desc': f'{desc}房间前门',
                 'url': 'rtsp://127.0.0.1/live'},
                {'deviceid': '34020000001420000001', 'channelid': '34020000001410000001', 'desc': f'{desc}大厅',
                 'url': 'rtsp://127.0.0.1/live'}
            ]}
    return item


@app.get("/api/v1/ptz/front_end_command/{deviceid}/{channelid}")
async def get_all_presets(deviceid: str, channelid: str):
    """模拟视频调度的获取某路视频的所有预置点接口"""
    log.log(channelid)
    item = {'version': '1.0.0',
            'deviceid': f'{deviceid}',
            'url': 'rtsp://127.0.0.1/live',
            'presetlist': [
                {'presetid': '1', 'presetname': '开机大门'},
                {'presetid': '2', 'presetname': '看室内'},
                {'presetid': '3', 'presetname': '看logo'},
                # {'presetid': '5', 'presetname': '其它'}
            ]
            }
    return item


@app.post("/api/v1/ptz/front_end_command/{deviceid}/{channelid}")
async def zoom_to_postion(deviceid: str, channelid: str, viewpoint: str = Form(...)):   # noqa
    """模拟视频调度的跳转到预置点接口"""
    # item = {"deviceId": deviceid, "channelId": channelid,
    # "cmdCode": 130, "parameter1": 0, "parameter2": int(viewpoint),
    #         "combindCode2": 0}
    # ret = {'version': '1.0.0',
    #     	   ’reply‘: False}
    # try:
    #     url = f'https://192.168.1.225:18180/api/ptz/front_end_command/{deviceid}/{channelid}'
    #     resp = requests.post(url, data=item, verify=False)
    #     if resp.status_code == 200:
    #         ret.update({'reply': True})
    # except KeyError:
    #     pass
    # finally:
    #     return ret
    return {'version': '1.0.0', 'reply': True}


# IF2 REST API  内部接口-智能识别
@app.post("/api/v1/ai/panel")
async def meter_recognization(files: UploadFile = File(...), cfg_info: str = Form(...), req_id: Optional[str] = None):
    log.log(f'{files.filename}, {files.content_type}, {cfg_info}')
    contents = files.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_aimeter(contents)
    ret.update({'req_id': int(req_id)})  # noqa
    return ret


@app.post("/api/v1/ai/person")
async def object_counting(files: UploadFile = File(...), cfg_info: str = Form(...), req_id: Optional[str] = None):
    log.log(f'{files.filename}, {files.content_type}, {cfg_info}')
    contents = files.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_objcounting(contents)
    ret.update({'req_id': int(req_id)})  # noqa
    return ret


@app.post("/api/v1/ai/plc")
async def indicator_frequency(files: UploadFile = File(...), cfg_info: str = Form(...), req_id: Optional[str] = None):
    log.log(f'{files.filename}, {files.content_type}, {cfg_info}, {req_id}')
    contents = files.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_indicator_freq(contents)
    ret.update({'req_id': int(req_id)})  # noqa
    return ret

if __name__ == '__main__':
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = log.get_v2v_logger_formatter()
    log_config["formatters"]["access"]["fmt"] = log.get_v2v_logger_formatter()
    log_config["loggers"]['uvicorn.error'].update({"propagate": False, "handlers": ["default"]})
    uvicorn.run(app,                # noqa
                host="0.0.0.0",
                port=7180,
                ssl_keyfile="cert.key",
                ssl_certfile="cert.cer",
                log_level='info',
                log_config=log_config
                )
