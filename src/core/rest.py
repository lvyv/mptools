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
rest module
=========================

Provide web api access points.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0


import uvicorn
# import cv2
import imutils
import io
import base64
from matplotlib import pyplot as plt
from imutils.video import VideoStream
# from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from os.path import isfile, join
from os import listdir

from utils import bus, comn
from utils.config import ConfigSet
from core.procworker import ProcWorker

# from core.main import MainContext


app_ = FastAPI(
    title="视频图像智能分析软件",
    description="视频图像智能分析软件对外发布的RESTful API接口",
    version="2.2.0", )

# 支持跨越
origins = ['*']
app_.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# 全局变量
rest_proc_ = None
counter_ = 0
cfg_ = None
baseurl_of_nvr_samples_ = '/viewport'
localroot_of_nvr_samples_ = ConfigSet.get_cfg()['nvr_samples']

# EIF3:REST V2V C&M 外部接口-提供UI前端配置V2V需要的截图
# 本路由为前端ui的路径
app_.mount('/ui', StaticFiles(directory='../src/ui'), name='ui')
# 本路由为thumbnail预览图片保存位置，该位置下按nvr的deviceid建立文件夹，放置所有base64的采样图片
app_.mount(baseurl_of_nvr_samples_, StaticFiles(directory=localroot_of_nvr_samples_), name='nvr')


@app_.get("/api/v1/v2v/presets/{deviceid}/{channelid}")
async def label_picture(deviceid: str, channelid: str, refresh: bool = False):
    """获取该视频通道所有预置点，然后逐个预置点取图，保存为base64"""
    item = {'version': '1.0.0'}
    try:
        target = f'{localroot_of_nvr_samples_}{deviceid}/'
        if refresh:
            # 如果是刷新，这需要从nvr取图片保存到本地目录
            url = comn.get_url(deviceid, channelid)
            presets = comn.get_presets(deviceid, channelid)
            if url and presets:
                vs = VideoStream(src=url).start()
                for prs in presets:
                    ret = comn.run_to_viewpoints(deviceid, channelid, prs['presetid'])
                    if ret:
                        frame = vs.read()
                        frame = imutils.resize(frame, width=680)
                        buf = io.BytesIO()
                        plt.imsave(buf, frame, format='png')
                        image_data = buf.getvalue()
                        image_data = base64.b64encode(image_data)
                        outfile = open(f'{target}{prs["presetid"]}', 'wb')
                        outfile.write(image_data)
                        outfile.close()
                # vs.stop()
                # vs.release()
        onlyfiles = [f'{baseurl_of_nvr_samples_}/{deviceid}/{f}' for f in listdir(target) if isfile(join(target, f))]
        item['presets'] = onlyfiles
    except FileNotFoundError as fs:
        rest_proc_.log(f'{fs}')  # noqa
    finally:
        return item


class Switch(BaseModel):
    cmd: str = 'start'


@app_.post("/api/v1/v2v/pipeline/")
async def create_item(item: Switch):
    """统一关闭或启动rtsp，ai，mqtt子进程"""
    cmds = ['start', 'stop']
    if item.cmd in cmds:
        # rest_proc_.send_cmd(bus.EBUS_TOPIC_MAIN, item.cmd) # noqa
        if item.cmd == 'start':
            ret = rest_proc_.call_rpc(bus.CB_STARTUP_PPL, {'cmd': item.cmd})  # noqa
        else:
            ret = rest_proc_.call_rpc(bus.CB_STOP_PPL, {'cmd': item.cmd})  # noqa
    else:
        ret = {'reply': 'unrecognized command.'}
    return ret


# @app_.on_event("startup")
# def startup():
#     """周期性任务，用于读取系统状态和实现探针程序数据来源的提取"""
#     global localroot_of_nvr_samples_
#     ret = rest_proc_.call_rpc(bus.CB_GET_CFG, {})
#     localroot_of_nvr_samples_ = ret['nvr_samples']


@app_.on_event("startup")
@repeat_every(seconds=1, wait_first=True)
def periodic():
    """周期性任务，用于读取系统状态和实现探针程序数据来源的提取"""
    global counter_
    counter_ += 1


class RestWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_REST, dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q

        self.port_ = None
        self.ssl_keyfile_ = None
        self.ssl_certfile_ = None

        for key, value in dicts.items():
            if key == 'port':
                self.port_ = value
            elif key == 'ssl_keyfile':
                self.ssl_keyfile_ = value
            elif key == 'ssl_certfile':
                self.ssl_certfile_ = value

    def run(self, *kwargs):
        global rest_proc_
        rest_proc_ = self
        uvicorn.run(app_,  # noqa 标准用法
                    host="0.0.0.0",
                    port=self.port_,
                    ssl_keyfile=self.ssl_keyfile_,
                    ssl_certfile=self.ssl_certfile_,
                    log_level='info'
                    )
