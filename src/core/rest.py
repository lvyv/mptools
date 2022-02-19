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
import logging

import uvicorn
import cv2
import imutils
import io
import base64
import os
import time
import psutil
import xml.etree.ElementTree as xmlET

from prometheus_fastapi_instrumentator.metrics import Info
from prometheus_client import Gauge
from typing import Callable
from prometheus_fastapi_instrumentator import Instrumentator
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

from utils import bus, comn, log, GrabFrame, wrapper as wpr
from simplegallery.gallery_init import gallery_create
from simplegallery.gallery_build import gallery_build
# from utils.config import ConfigSet
from core.procworker import ProcWorker
from uvicorn.main import Server

# rtsp url timeoff
OPEN_RTSP_TIMEOFF = 30

# 猴子补丁：在退出本进程的时候，ctrl+c会等待较长时间关闭socket
original_handler = Server.handle_exit


class AppStatus:
    should_exit = False

    @staticmethod
    def handle_exit(*args, **kwargs):
        AppStatus.should_exit = True
        original_handler(*args, **kwargs)


Server.handle_exit = AppStatus.handle_exit


# 添加全局指标监测，如cpu、mem等，不需要进程上下文信息
def cpu_rate() -> Callable[[Info], None]:
    metric = Gauge(
        "cpu_rate",
        "cpu占用率.",
        labelnames=("application", "host")
    )

    def instrumentation(info: Info) -> None:
        cpu = psutil.cpu_percent()
        metric.labels('main', 'localhost').set(cpu)     # 可以根据需要设置更多的label标签和值
        info.request.query_params.getlist('v2v')        # 可以获得url参数，http://127.0.0.1:7080/metrics?v2v=x&v2v=2

    return instrumentation


def mem_rate() -> Callable[[Info], None]:
    metric = Gauge(
        "mem_rate",
        "内存占用率.",
        labelnames=("application",)
    )

    def instrumentation(info: Info) -> None:
        mem = psutil.virtual_memory().percent
        metric.labels('main').set(mem)
        info.request.query_params.getlist('v2v')

    return instrumentation


class RestWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_REST, dicts, **kwargs)    # 不订阅rtsp、ai、mqtt等线程主题，避免被停等
        self.cached_cvobjs_ = {}     # 缓存opencv的封装对象
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

    def create_app(self) -> FastAPI:

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
        rest_proc_ = self
        # cfg_ = None
        baseurl_of_nvr_samples_ = '/viewport'
        # FIXME:这个地方应该改为从主进程获取配置，主进程是唯一来源，子进程避免直接操作文件系统
        cfgobj = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': self.name})
        localroot_of_nvr_samples_ = cfgobj['nvr_samples']
        ui_config_tpl_ = f'{cfgobj["ui_config_dir"]}ui.xml'
        ai_url_config_file_ = f'{cfgobj["ui_config_dir"]}diagrameditor.xml'

        # localroot_of_nvr_samples_ = ConfigSet.get_cfg()['nvr_samples']
        # ui_config_tpl_ = f'{ConfigSet.get_cfg()["ui_config_dir"]}ui.xml'
        # ai_url_config_file_ = f'{ConfigSet.get_cfg()["ui_config_dir"]}diagrameditor.xml'

        # EIF3:REST V2V C&M 外部接口-提供UI前端配置V2V需要的截图
        # 本路由为前端ui的路径
        app_.mount('/ui', StaticFiles(directory='../src/ui'), name='ui')
        app_.mount('/static', StaticFiles(directory='../src/swagger_ui_dep/static'), name='static')

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
            rtsp_urls: str = '[]'
            mqtt_svrs: str = '[]'
            micro_service: str = '{}'
            nvr_samples: str = ''
            ui_config_dir: str = ''
            media_service: str = ''
            ipc_ptz_delay: int = 3

        @app_.post("/api/v1/v2v/setup_all_channels")
        async def setup_all_channels(cfg: Channels):
            """C&M之C：设置配置文件，收到该配置文件后，v2v将更新整个v2v的配置文件"""
            """当前功能是接受整个配置设置给到ai"""
            item = {'version': '1.0.0', 'reply': 'pending.'}
            rest_proc_.call_rpc(bus.CB_SET_CFG, cfg.__dict__)  # noqa 调用主进程函数，传配置给它。
            item['reply'] = True
            return item

        class AiURL(BaseModel):
            person: str = 'https://127.0.0.1:7180/api/v1/ai/person'
            plc: str = 'https://127.0.0.1:7180/api/v1/ai/plc'
            ocr: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
            llm: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
            pointer: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
            switch: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
            indicator: str = 'https://127.0.0.1:7180/api/v1/ai/panel'

        @app_.post("/api/v1/v2v/setup_ai_url")
        async def setup_ai_url(cfg: AiURL):
            """C&M之C：设置ai微服务模型的url"""
            """当前功能是修改配置文件"""
            item = {'version': '1.0.0', 'reply': 'pending.'}
            tree = xmlET.parse(ui_config_tpl_)
            root = tree.getroot()

            person = root.findall('./Array/add/person')
            if len(person) == 1:
                person[0].attrib['href'] = cfg.person

            plc = root.findall('./Array/add/PLC')
            if len(plc) == 1:
                plc[0].attrib['href'] = cfg.plc

            ocr = root.findall('./Array/add/OCR')
            if len(ocr) == 1:
                ocr[0].attrib['href'] = cfg.ocr

            llm = root.findall('./Array/add/LLM')
            if len(llm) == 1:
                llm[0].attrib['href'] = cfg.llm

            pointer = root.findall('./Array/add/METER')
            if len(pointer) == 1:
                pointer[0].attrib['href'] = cfg.pointer

            switch = root.findall('./Array/add/SWITCH')
            if len(switch) == 1:
                switch[0].attrib['href'] = cfg.switch

            indicator = root.findall('./Array/add/IDL')
            if len(indicator) == 1:
                indicator[0].attrib['href'] = cfg.indicator

            tree.write(ai_url_config_file_)
            item['reply'] = True
            return item

        @app_.get("/api/v1/v2v/metrics")
        async def provide_metrics(deviceid: str, channelid: str):
            """C&M之M：接受监控端比如promethus的调用，反馈自己是否在线和反馈各种运行时信息"""
            item = {'version': '1.0.0'}
            rest_proc_.log(deviceid)  # noqa
            rest_proc_.log(channelid)  # noqa

            return item

        # EIF5:REST PTZ CNTL 代理视频调度管理软件，返回当前所有摄像头的描述
        @app_.get("/api/v1/ptz/streaminfo")
        async def stream_info():
            """获取所有的视频通道列表"""
            item = {'version': '1.0.0', 'reply': 'pending.'}
            cfg = rest_proc_.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': rest_proc_.name})
            comn.set_common_cfg(cfg)    # 只是设置全局变量，便于配置的热更新（视频调度管理软件的摄像头停留时间和视频调度服务器地址）
            streams = comn.get_urls()
            item['streams'] = streams
            item['reply'] = True
            return item

        @app_.get("/api/v1/v2v/presets/{deviceid}/{channelid}")
        async def get_presets(deviceid: str, channelid: str, refresh: bool = False):
            """获取该视频通道所有预置点，然后逐个预置点取图，保存为base64，加入流断处理，加入流缓存以及互斥锁保护全局缓存流"""
            item = {'version': '1.0.0', 'reply': 'pending.', 'rtsp_url': None}
            try:
                # 设置全局变量，便于热更新配置（视频调度管理软件的摄像头停留时间和视频调度服务器地址在comn中发挥作用。
                cfg = rest_proc_.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': rest_proc_.name})
                comn.set_common_cfg(cfg)
                target = f'{localroot_of_nvr_samples_}{deviceid}/'  # 不支持nvrsamples的热更新，因为启动程序需要mount本地目录
                if refresh:
                    # 如果是刷新，需要从nvr取图片保存到本地目录(nvr_samples目录下按设备号创建目录)。
                    url = comn.get_url(deviceid, channelid)
                    presets = None
                    if url:  # url都得不到，就不需要得presets了
                        presets = comn.get_presets(deviceid, channelid)
                    if url and presets:
                        # 通知主调度，暂停pipeline流水线对本摄像头的识别操作，让rtsp流水线rtsp进程sleep多少时间计算得出。
                        rest_p, rtsp_p = self.calculate_delay_time(cfg, url)
                        pipeline_cmd = {'cmd': 'pause', 'deviceid': deviceid, 'channelid': channelid,
                                        'timeout': rtsp_p}
                        isok = rest_proc_.call_rpc(bus.CB_PAUSE_RESUME_PIPE, pipeline_cmd)  # noqa 调用主进程函数，传配置给它。
                        if not isok['reply']:
                            raise RuntimeError(f'Cannot get the control of IPC: {deviceid}, {channelid}.')
                        # rest 需要等待一定时间，让rtsp进程停下来。
                        time.sleep(rest_p)

                        if url in rest_proc_.cached_cvobjs_:
                            # 如果缓存过，就直接用缓存的流。
                            cvobj = rest_proc_.cached_cvobjs_[url]
                        else:
                            # 如果这个url没配置过，则打开一个新的对象来取流。
                            cvobj = GrabFrame.GrabFrame()
                            opened = cvobj.open_stream(url, GrabFrame.GrabFrame.OPEN_RTSP_TIMEOFF)
                            if opened:
                                rest_proc_.cached_cvobjs_[url] = cvobj
                            else:
                                raise cv2.error(f'Failed to open {url}.')
                        # 产生系列预置点图片。
                        item['rtsp_url'] = url  # 前端需要了解是否有合法url，才方便下发配置的时候填入正确的配置值
                        for prs in presets:
                            ret = comn.run_to_viewpoints(deviceid, channelid, prs['presetid'])
                            if ret:
                                # mutex_.acquire()  # 防止流并发访问错误
                                frame = cvobj.read_frame()
                                if frame is None:
                                    cvobj.stop_stream()
                                    rest_proc_.cached_cvobjs_.pop(url, None)    # 如果没有读出数据，清空缓存
                                    raise cv2.error(f'Got null frame from cv2.')
                                # mutex_.release()
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
                    else:
                        # 不是合法的设备号
                        errmsg = f'摄像头{deviceid}-{channelid}查询流地址或预置点失败。'
                        item['reply'] = errmsg
                        raise ValueError(errmsg)
                    # # 通知主调度，恢复pipeline流水线对本摄像头的识别操作
                    # pipeline_cmd['cmd'] = 'resume'
                    # isok = rest_proc_.call_rpc(bus.CB_PAUSE_RESUME_PIPE, pipeline_cmd)  # noqa 调用主进程函数，传配置给它。
                    # if not isok['reply']:
                    #     raise RuntimeError(f'Cannot get the control of IPC: {deviceid}, {channelid}.')
                    #
                    # 不需要通知恢复，因为rest自己先停，等rtsp，然后rtsp停，再等rest，rest操作完，rtsp自动恢复（sleep超时）。
                onlyfiles = [f'{baseurl_of_nvr_samples_}/{deviceid}/{f}'
                             for f in listdir(target) if isfile(join(target, f)) and ('.png' not in f)]
                # 返回视频的原始分辨率，便于在前端界面了解和载入
                # 有问题，如果没有初始化流（fresh=False）,为了获取png文件尺寸，选第一个文件来查询其尺寸
                pngfiles = [fn for fn in listdir(target) if isfile(join(target, fn)) and ('.png' in fn)]
                if len(pngfiles) > 0:
                    item['reply'] = True
                    item['presets'] = onlyfiles
                    pngfile = f'{target}{pngfiles[0]}'
                    item['width'], item['height'] = wpr.get_picture_size(pngfile)
                else:
                    item['reply'] = False
                    item['desc'] = '没有生成可标注的图片。'
            except FileNotFoundError as fs:
                rest_proc_.log(f'{fs}')
            except ValueError as err:
                rest_proc_.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)  # noqa
            except RuntimeError as err:
                rest_proc_.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)  # noqa
            except cv2.error as cve:
                rest_proc_.log(f'[{__file__}]{cve}', level=log.LOG_LVL_ERRO)
            else:
                rest_proc_.log(f'Preset pictures done.')
            finally:
                return item

        class Directory(BaseModel):
            datedir: str = '2022-02-11'

        @app_.post("/api/v1/v2v/pixgallery")
        async def pixgallery(item: Directory):
            """把参数指定日期得视频识别结果打包为可访问的web服务，返回url地址"""
            ret = {'version': '1.0.0', 'reply': False}
            imagedir = f'{localroot_of_nvr_samples_}airesults/{item.datedir}'
            res = gallery_create(imagedir)
            if res:
                res = gallery_build(imagedir)
                if res:
                    visit_url = f'{baseurl_of_nvr_samples_}/airesults/{item.datedir}/public/index.html'
                    ret = {'version': '1.0.0', 'reply': res, 'url': visit_url}
            return ret

        @app_.on_event("startup")
        @repeat_every(seconds=1, wait_first=True)
        def periodic():
            """周期性任务，用于读取系统状态和实现探针程序数据来源的提取，并在空闲时刻消费视频流"""
            # 消耗掉多余的帧
            # if current_video_stream_['url']:
            #     cap = current_video_stream_['videostream']
            #     fps = cap.get(cv2.cv2.CAP_PROP_FPS) + 5  # noqa 消耗完后 grab会返回非真，退出循环。
            #     run = True
            #     while fps > 0 and run:
            #         mutex_.acquire()
            #         run = cap.grab()  # noqa
            #         mutex_.release()
            #         if not run:
            #             rest_proc_.log('Catch up the nvr play speed.')  # noqa
            #         fps -= 1
            pass

        @app_.on_event("shutdown")
        def shutdown():
            """关闭事件"""
            pass

        return app_

    def calculate_delay_time(self, cfgobj, url):
        """
        根据配置信息，计算某设备号，通道号对应视频要等多少时间。
        返回的等待时间有两个值，一个是rest，一个是rtsp。
        1.设想rest发广播消息，rtsp因为会在mainloop中过预置点，这个时间段A一直无法收到消息，需要rest等待。
        2.rest等待A时间后，获取摄像头控制权。
        3.rtsp在0~A时间段都可能收到广播，收到后等待rest操作广播的时间，重新运行。
        如果rtsp不存在，则rest_sleep_time = 0
        如果rtsp存在，
            则按照配置信息中：（seconds x 预置点个数）计时为需要停留的A时间。
            则按照配置信息中：（ipc_ptz_delay*预置点个数）计时为停留的B时间。
        """
        rest_sleep_time = 0
        rtsp_sleep_time = 0
        try:
            ret = self.call_rpc(bus.CB_GET_METRICS, {'cmd': 'get_metrics', 'desc': 'rest api is called.'})
            tasks = ret['result_tasks']
            ipc_ptz_delay = cfgobj['ipc_ptz_delay']
            if url in tasks.keys():
                for urlchannel in cfgobj['rtsp_urls']:
                    if urlchannel['rtsp_url'] == url:
                        presets_size = len(urlchannel['view_ports'])
                        # 多个viewports中第1个预置点的第1个aoi的
                        seconds = list(urlchannel['view_ports'][0].items())[0][1][0]['seconds']
                        rest_sleep_time = seconds * presets_size    # A时间
                        # 如果rtsp刚好rest发送就收到广播，它还是要等一个A时间
                        rtsp_sleep_time = ipc_ptz_delay * presets_size + rest_sleep_time
                        break
        except (KeyError, Exception) as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
        finally:
            return rest_sleep_time, rtsp_sleep_time

    def up_time(self) -> Callable[[Info], None]:
        metric = Gauge(
            "up_time",
            "开机持续运行时间.",
            labelnames=("application",)
        )
        sts_ = int(time.time())  # 秒为单位
        rest_ = self

        def instrumentation(info: Info) -> None:    # noqa
            # rest_.log(f'Promethues scrape request: {info.request.url}')
            # 主进程的运行时间累计
            nonlocal sts_
            current = int(time.time())
            delta = current - sts_
            metric.labels('main').set(delta)

            # 收集子进程监测数据(数据结构是{'result':{'AIxx':{'up': 1.1, 'xx': 2}, ... }})
            proc_metrics = rest_.call_rpc(bus.CB_GET_METRICS, {'cmd': 'get_metrics', 'desc': 'rest api is called.'})
            res = proc_metrics['result_metrics']
            for key in res.keys():
                item = res[key]
                if 'up' in item.keys():
                    metric.labels(key).set(item['up'])

        return instrumentation

    def run(self):
        localapp = self.create_app()
        # 只要有rest请求，就会触发添加的这几个统计函数，向主进程请求监测数据。
        instrumentator = Instrumentator(
            # excluded_handlers=[".*admin.*", "/metrics"],
        )
        instrumentator.add(self.up_time())
        instrumentator.add(cpu_rate())
        instrumentator.add(mem_rate())
        instrumentator.instrument(localapp).expose(localapp)

        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["formatters"]["default"]["fmt"] = log.get_v2v_logger_formatter()
        log_config["formatters"]["access"]["fmt"] = log.get_v2v_logger_formatter()
        log_config["loggers"]['uvicorn.error'].update({"propagate": False, "handlers": ["default"]})
        uvicorn.run(localapp,  # noqa 标准用法
                    host="0.0.0.0",
                    port=self.port_,
                    ssl_keyfile=self.ssl_keyfile_,
                    ssl_certfile=self.ssl_certfile_,
                    log_level=logging.WARN,
                    log_config=log_config
                    )
