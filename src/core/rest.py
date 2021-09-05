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
import cv2
import imutils
import io
import base64
import threading
import os
import xml.etree.ElementTree as xmlET
from matplotlib import pyplot as plt
# from imutils.video import VideoStream
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from os.path import isfile, join
from os import listdir

from utils import bus, comn, log
from utils.config import ConfigSet
from core.procworker import ProcWorker
from uvicorn.main import Server

# 猴子补丁：在退出本进程的时候，ctrl+c会等待较长时间关闭socket
original_handler = Server.handle_exit


class AppStatus:
    should_exit = False

    @staticmethod
    def handle_exit(*args, **kwargs):
        AppStatus.should_exit = True
        original_handler(*args, **kwargs)


Server.handle_exit = AppStatus.handle_exit

app_ = FastAPI(
    title="视频图像智能分析软件",
    description="视频图像智能分析软件对外发布的RESTful API接口",
    version="2.2.0", )

# 支持跨域
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
cfg_ = None
baseurl_of_nvr_samples_ = '/viewport'
# FIXME:这个地方应该改为从主进程获取配置，主进程是唯一来源，子进程避免直接操作文件系统
localroot_of_nvr_samples_ = ConfigSet.get_cfg()['nvr_samples']
ui_config_tpl_ = f'{ConfigSet.get_cfg()["ui_config_dir"]}ui.xml'
ai_url_config_file_ = f'{ConfigSet.get_cfg()["ui_config_dir"]}diagrameditor.xml'

# 这个是缓存cv2捕获nvr流的，因为打开一个nvr花费4秒以上太久
# 缓存cv2带来负效应：一旦视频捕获开始，需要在定时器中持续消费，否则下次api调用得到的是滞后较久的帧，因此又加了个伪锁
current_video_stream_ = {'url': None, 'videostream': None}
mutex_ = threading.Lock()

# EIF3:REST V2V C&M 外部接口-提供UI前端配置V2V需要的截图
# 本路由为前端ui的路径
app_.mount('/ui', StaticFiles(directory='../src/ui'), name='ui')
# 本路由为thumbnail预览图片保存位置，该位置下按nvr的deviceid建立文件夹，放置所有base64的采样图片
app_.mount(baseurl_of_nvr_samples_, StaticFiles(directory=localroot_of_nvr_samples_), name='nvr')


class Switch(BaseModel):
    cmd: str = 'start'


@app_.post("/api/v1/v2v/pipeline/")
async def pipeline(item: Switch):
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


class ViewPorts(BaseModel):
    rtsp_url: str = ''
    device_id: Optional[str] = ''
    channel_id: Optional[str] = ''
    name: Optional[str] = ''
    sample_rate: int = 1
    view_ports: str = ''


@app_.post("/api/v1/v2v/setup_single_channel")
async def setup_single_channel(cfg: ViewPorts):
    """C&M之C：设置配置文件，收到该配置文件后，v2v将更新单通道的配置文件"""
    """当前功能是接受一个单通道视频设置给到ai"""
    item = {'version': '1.0.0', 'reply': 'pending.'}
    ret = rest_proc_.call_rpc(bus.CB_SET_CFG, cfg.__dict__)  # noqa 调用主进程函数，传配置给它。
    item['reply'] = ret['reply']
    item['desc'] = ret['desc']
    return item


class Channels(BaseModel):
    version: str = '1.0.0'
    rtsp_urls: str = ''
    mqtt_svrs: str = ''
    micro_service: str = ''
    nvr_samples: str = ''


@app_.post("/api/v1/v2v/setup_all_channels")
async def setup_all_channels(cfg: Channels):
    """C&M之C：设置配置文件，收到该配置文件后，v2v将更新整个v2v的配置文件"""
    """当前功能是接受整个配置设置给到ai"""
    item = {'version': '1.0.0', 'reply': 'pending.'}
    rest_proc_.call_rpc(bus.CB_SET_CFG, cfg.__dict__)  # noqa 调用主进程函数，传配置给它。
    item['reply'] = True
    return item


class AiURL(BaseModel):
    plc: str = 'https://127.0.0.1:7180/api/v1/ai/plc'
    panel: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
    person: str = 'https://127.0.0.1:7180/api/v1/ai/person'


@app_.post("/api/v1/v2v/setup_ai_url")
async def setup_ai_url(cfg: AiURL):
    """C&M之C：设置ai微服务模型的url"""
    """当前功能是修改配置文件"""
    item = {'version': '1.0.0', 'reply': 'pending.'}
    tree = xmlET.parse(ui_config_tpl_)
    root = tree.getroot()

    panel = root.findall('./Array/add/Rect')
    if len(panel) == 1:
        panel[0].attrib['href'] = cfg.panel

    plc = root.findall('./Array/add/Roundrect')
    if len(plc) == 1:
        plc[0].attrib['href'] = cfg.plc

    person = root.findall('./Array/add[@as="actor"]/Shape')
    if len(person) == 1:
        person[0].attrib['href'] = cfg.person

    tree.write(ai_url_config_file_)
    item['reply'] = True
    return item


@app_.get("/api/v1/v2v/metrics")
async def provide_metrics(deviceid: str, channelid: str):
    """C&M之M：接受监控端比如promethus的调用，反馈自己是否在线和反馈各种运行时信息"""
    item = {'version': '1.0.0'}
    rest_proc_.log(deviceid)    # noqa
    rest_proc_.log(channelid)   # noqa

    return item


# EIF5:REST PTZ CNTL 代理视频调度管理软件，返回当前所有摄像头的描述
@app_.get("/api/v1/ptz/streaminfo")
async def stream_info():
    """获取所有的视频通道列表"""
    item = {'version': '1.0.0', 'reply': 'pending.'}
    streams = comn.get_urls()
    item['streams'] = streams
    item['reply'] = True
    return item


@app_.get("/api/v1/v2v/presets/{deviceid}/{channelid}")
async def get_presets(deviceid: str, channelid: str, refresh: bool = False):
    """获取该视频通道所有预置点，然后逐个预置点取图，保存为base64，加入流断处理，加入流缓存以及互斥锁保护全局缓存流"""
    item = {'version': '1.0.0', 'reply': 'pending.'}
    try:
        target = f'{localroot_of_nvr_samples_}{deviceid}/'
        if refresh:
            # 如果是刷新，这需要从nvr取图片保存到本地目录(nvr_samples目录下按设备号创建目录)
            url = comn.get_url(deviceid, channelid)
            presets = comn.get_presets(deviceid, channelid)
            # 如果是合法的设备号，并且配置有url则启动流，抓图，否则
            if url and presets:
                # 如果缓存过，就直接用缓存的流
                if url == current_video_stream_['url']:
                    vs = current_video_stream_['videostream']
                # 如果没有缓存就开新的流，但原来缓存的流要关闭
                else:
                    vs = cv2.VideoCapture(url)
                    opened = vs.isOpened()
                    if opened:
                        # 从未缓存
                        if current_video_stream_['url'] is None:
                            current_video_stream_['url'] = url
                            current_video_stream_['videostream'] = vs   # noqa
                        # 缓存了其他流
                        else:
                            current_video_stream_['videostream'].release()  # noqa
                            current_video_stream_['url'] = url
                            current_video_stream_['videostream'] = vs   # noqa
                    else:
                        item['reply'] = f'摄像头{deviceid}-{channelid}提供的流地址（{url}）无法访问。'
                        return item
                # 产生系列预置点图片
                try:
                    for prs in presets:
                        ret = comn.run_to_viewpoints(deviceid, channelid, prs['presetid'])
                        if ret:
                            mutex_.acquire()            # 防止流并发访问错误
                            grab, frame = vs.read()
                            mutex_.release()
                            # height, width, channels = frame.shape
                            # 保存原始图像
                            filename = f'{target}{prs["presetid"]}.png'
                            os.makedirs(os.path.dirname(filename), exist_ok=True)
                            cv2.imwrite(filename, frame)
                            # 保存缩略图，1920x1080的长宽缩小20倍
                            frame = imutils.resize(frame, width=96, height=54)
                            buf = io.BytesIO()
                            plt.imsave(buf, frame, format='png')
                            image_data = buf.getvalue()
                            image_data = base64.b64encode(image_data)
                            outfile = open(f'{target}{prs["presetid"]}', 'wb')
                            outfile.write(image_data)
                            outfile.close()
                except cv2.error as cve:
                    vs.release()
                    vs = cv2.VideoCapture(current_video_stream_['url'])
                    current_video_stream_['videostream'] = vs   # noqa
            else:
                item['reply'] = f'摄像头{deviceid}-{channelid}未设置流地址或预置点。'
                return item
        onlyfiles = [f'{baseurl_of_nvr_samples_}/{deviceid}/{f}'
                     for f in listdir(target) if isfile(join(target, f)) and ('.png' not in f)]
        # 返回视频的原始分辨率，便于在前端界面了解和载入

        # 有问题，如果没有初始化流（fresh=False）,为了获取png文件尺寸，选第一个文件来查询其尺寸
        pngfiles = [fn for fn in listdir(target) if isfile(join(target, fn)) and ('.png' in fn)]
        if len(pngfiles) > 0:
            item['reply'] = True
            item['presets'] = onlyfiles
            pngfile = f'{target}{pngfiles[0]}'
            item['width'], item['height'] = comn.get_picture_size(pngfile)
        else:
            item['reply'] = False
            item['desc'] = '没有生成可标注的图片。'
    except FileNotFoundError as fs:
        rest_proc_.log(f'{fs}')  # noqa
    else:
        rest_proc_.log(f'{fs}', level=log.LOG_LVL_ERRO)  # noqa
    finally:
        # current_video_stream_['consume_lock'] = True  # 允许定时器再同时消费视频流（grab）。
        return item


@app_.on_event("startup")
@repeat_every(seconds=1, wait_first=True)
def periodic():
    """周期性任务，用于读取系统状态和实现探针程序数据来源的提取，并在空闲时刻消费视频流"""
    # 消耗掉多余的帧
    if current_video_stream_['url']:
        cap = current_video_stream_['videostream']
        fps = cap.get(cv2.cv2.CAP_PROP_FPS) + 5 # noqa
        run = True
        while fps > 0 and run:
            mutex_.acquire()
            run = cap.grab()    # noqa
            mutex_.release()
            if not run:
                rest_proc_.log('Catch up the nvr play speed.')  # noqa
            fps -= 1
        # rest_proc_.log(current_video_stream_['url'])
    # rest_proc_.log(f'Ticker: {current_video_stream_["url"]}')


@app_.on_event("shutdown")
def shutdown():
    """关闭事件"""
    pass


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
        rest_proc_.call_rpc(bus.CB_STOP_REST, {})  # 好吧，优雅的退出
