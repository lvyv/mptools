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


def call_aimeter(contents):
    # print(contents)
    if contents:
        pass
    ret = [
        {'id': 1, 'key1': 31.2, 'loc': [14, 23]},
        {'id': 2, 'key2': 20, 'loc': [102, 538]}
    ]
    return ret


def call_objcounting(contents):
    if contents:
        pass
    ret = [
        {'id': 1, 'person': 12},
        {'id': 2, 'car': 1}
    ]
    return ret


def call_indicator_freq(contents):
    if contents:
        pass
    ret = [
        {'id': 1, '油泵指示灯': 3},  # 3 表示3Hz
        {'id': 2, '电源指示灯': -1},  # -1 表示常亮
        {'id': 3, '通信指示灯': 0}  # 0 表示常灭
    ]
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
        file.close()
    log.log(jsos)

    return {"reply": True}


# EIF5:REST PTZ CNTL 外部接口-视频调度管理软件
@app.get("/api/v1/ptz/streaminfo")
async def stream_info():
    """获取所有的视频通道列表"""
    item = {'version': '1.0.0',
            'channels': [
                {'deviceid': '34020000001320000001', 'channelid': '34020000001310000001', 'desc': '605房间前门',
                 'url': 'rtsp://127.0.0.1/live'},
                {'deviceid': '34020000001320000001', 'channelid': '34020000001310000001', 'desc': '605大厅',
                 'url': 'rtsp://127.0.0.1/live'},
                {'deviceid': '34020000001420000001', 'channelid': '34020000001410000001', 'desc': '608停车区',
                 'url': 'rtsp://127.0.0.1/live'}
            ]}
    return item


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
                {'presetid': 'preset4', 'presetname': '开机默认位置'},
                {'presetid': 'preset5', 'presetname': '看室内'},
                {'presetid': 'preset6', 'presetname': '看室外'}]
            }
    return item


@app.post("/api/v1/ptz/front_end_command/{deviceid}/{channelid}")
async def zoom_to_postion(deviceid: str, channelid: str, viewpoint: str = Form(...)):
    """模拟视频调度的跳转到预置点接口"""
    item = {"deviceid": deviceid, "channelid": channelid, "cmdCode": 130, "parameter1": 0, "parameter2": viewpoint}
    print(f"Zoom to: {item}")
    return item


# IF2 REST API  内部接口-智能识别
@app.post("/api/v1/ai/panel")
async def meter_recognization(files: UploadFile = File(...), cfg_info: str = Form(...)):
    log.log(f'{files.filename}, {files.content_type}, {cfg_info}')
    contents = files.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_aimeter(contents)
    return ret


@app.post("/api/v1/ai/person")
async def object_counting(files: UploadFile = File(...), cfg_info: str = Form(...)):
    log.log(f'{files.filename}, {files.content_type}, {cfg_info}')
    contents = files.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_objcounting(contents)
    return ret


@app.post("/api/v1/ai/plc")
async def indicator_frequency(files: UploadFile = File(...), cfg_info: str = Form(...), req_id: Optional[str] = None):
    log.log(f'{files.filename}, {files.content_type}, {cfg_info}')
    contents = files.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_indicator_freq(contents)
    return ret


if __name__ == '__main__':
    uvicorn.run(app,                # noqa
                host="0.0.0.0",
                port=7180,
                ssl_keyfile="cert.key",
                ssl_certfile="cert.cer"
                )
