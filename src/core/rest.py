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
# import base64
# import io
import logging
import os
import time
# import xml.etree.ElementTree as xmlET
# from os import listdir
# from os.path import isfile, join
from pathlib import Path
from typing import Callable
# import cv2
# import imutils
import psutil
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# from matplotlib import pyplot as plt
from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info
# from pydantic import BaseModel
# from typing import Optional
from uvicorn.main import Server

from core.procworker import ProcWorker
# from simplegallery.gallery_build import gallery_build
# from simplegallery.gallery_init import gallery_create
# from third_api import spdd
from utils import bus, log
# from utils import GrabFrame, wrapper as wpr

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
        metric.labels('main', 'localhost').set(cpu)  # 可以根据需要设置更多的label标签和值
        info.request.query_params.getlist('v2v')  # 可以获得url参数，http://127.0.0.1:7080/metrics?v2v=x&v2v=2

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
    def __init__(self, name, in_q=None, out_q=None, args_dict=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_REST, args_dict, **kwargs)  # 不订阅rtsp、ai、mqtt等线程主题，避免被停等
        self.cached_cvobjs_ = {}  # 缓存opencv的封装对象

        self.port_ = None
        self.ssl_keyfile_ = None
        self.ssl_certfile_ = None
        if in_q or out_q:   # not need yet
            pass
        for key, value in args_dict.items():
            if key == 'port':
                self.port_ = value
            elif key == 'ssl_keyfile':
                self.ssl_keyfile_ = value
            elif key == 'ssl_certfile':
                self.ssl_certfile_ = value

    def _check_did_cid_valid(self, did, cid) -> bool:
        """
        校验传入的设备ID是否合法
        """
        _is_exist_cid = False
        _cfg_dict = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': self.name})
        for channel in _cfg_dict['rtsp_urls']:
            _did = channel.get('device_id', None)
            _cid = channel.get('channel_id', None)
            if not _did or not _cid:
                continue
            # 检测传入的ID是否存在于配置文件中
            if _did == did and _cid == cid:
                _is_exist_cid = True
                break
        return _is_exist_cid

    # 创建Web服务器
    def create_app(self) -> FastAPI:
        tags_metadata = [
            {
                "name": "基础配置",
                "description": "提供路径规划必须的配置服务，比如地图上传，获取地图等服务接口。",
            },
            {
                "name": "路径规划",
                "description": "多智能体路径寻优，针对指定的地图，提供多个任务的起点和重点，求解完成所有任务的不冲突的智能体最优路径。",
            },
        ]
        _app = FastAPI(
            title="MAPF智能寻径微服务软件",
            description="提供多智能体路径搜索的RESTful API接口。",
            version="2.2.0",
            openapi_tags=tags_metadata)

        # 支持跨域
        origins = ['*']
        _app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*']
        )

        # 实例对象的引用，因为fastapi的接口函数中没有self对象
        _self_obj = self
        # 从主进程获取配置参数
        _v2v_cfg_dict = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': self.name})
        _map_directory = _v2v_cfg_dict['map_directory']

        # EIF1:REST CFG 外部接口-提供地图上传，查询等基本配置相关的接口
        # 解决swagger_ui_dep本地化部署的问题
        _pwd_path = Path(Path(__file__).parent)
        _app.mount('/static', StaticFiles(directory=str(_pwd_path.joinpath("../swagger_ui_dep/static"))), name='static')

        @_app.post("/api/v1/mapf/maps", tags=["基础配置"])
        async def keep_upload_file(upfile: UploadFile = File(...)):
            # 如果配置文件的地图路径不存在，将创建路径并保存上传地图文件
            pfname = f'{_map_directory}{upfile.filename}'
            os.makedirs(os.path.dirname(pfname), exist_ok=True)
            # 上传文件的写入
            contents = upfile.file.read()
            with open(pfname, 'wb') as fi:
                fi.write(contents)
            ret = {'version': '1.0.0', 'reply': True}
            return ret

        @_app.get("/api/v1/mapf/maps", tags=["基础配置"])
        async def list_map_files():
            # 列出地图目录的所有文件并返回
            dir_path = _map_directory
            # list to store files
            res = []
            # Iterate directory
            for path in os.listdir(dir_path):
                # check if current path is a file
                if os.path.isfile(os.path.join(dir_path, path)):
                    res.append(path)
            ret = {'version': '1.0.0', 'reply': res}
            return ret

        # EIF2:REST MAPF 外部接口-提供MAPF算法接口，求解路径
        @_app.get("/api/v1/mapf/mapf_solve", tags=["路径规划"])
        async def mapf_solve(map_name: str = 'zxk-640x440.map',
                             tasks: str = '[{"s": [480, 228], "e": [87, 253]}, {"s": [490, 271], "e": [160, 300]}]',
                             alg_name: str = 'cbs'):
            """对MAPF底层算法求解器的封装"""
            item = {'version': '1.0.0', 'reply': 'pending.'}
            cfg = {
                'map_name': map_name,  # zxk-640x440.map
                'tasks': tasks,        # [{"s": [480, 228], "e": [87, 253]}, {"s": [490, 271], "e": [160, 300]}]
                'alg_name': alg_name   # cbs
            }
            # 实现操作系统层的调用，并反馈结果。
            res = _self_obj.call_rpc(bus.CB_MAPF_SOLVE, cfg)  # noqa 调用主进程函数，传配置给它。
            item['reply'] = res
            return item
        #
        # class Channels(BaseModel):
        #     version: str = '1.0.0'
        #     rtsp_urls: str = '[]'
        #     mqtt_svrs: str = '[]'
        #     micro_service: str = '{}'
        #     nvr_samples: str = ''
        #     ui_config_dir: str = ''
        #     media_service: str = ''
        #     ipc_ptz_delay: int = 3
        #
        # @_app.post("/api/v1/v2v/setup_all_channels")
        # async def setup_all_channels(cfg: Channels):
        #     """设置配置文件，收到该配置文件后，v2v将更新整个v2v的配置文件"""
        #     _reply = {'version': '1.0.0', 'reply': 'pending.'}
        #     _cfg_from_web_dict = cfg.__dict__
        #     _self_obj.call_rpc(bus.CB_SET_CFG, _cfg_from_web_dict)  # noqa 调用主进程函数，传配置给它。
        #     _reply['reply'] = True
        #     return _reply
        #
        # class AiURL(BaseModel):
        #     person: str = 'https://127.0.0.1:7180/api/v1/ai/person'
        #     plc: str = 'https://127.0.0.1:7180/api/v1/ai/plc'
        #     ocr: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
        #     llm: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
        #     pointer: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
        #     switch: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
        #     indicator: str = 'https://127.0.0.1:7180/api/v1/ai/panel'
        #
        # @_app.post("/api/v1/v2v/setup_ai_url")
        # async def setup_ai_url(cfg: AiURL):
        #     """C&M之C：设置ai微服务模型的url"""
        #     """当前功能是修改配置文件"""
        #     item = {'version': '1.0.0', 'reply': 'pending.'}
        #     tree = xmlET.parse(_ui_config_tpl)
        #     root = tree.getroot()
        #
        #     person = root.findall('./Array/add/person')
        #     if len(person) == 1:
        #         person[0].attrib['href'] = cfg.person
        #
        #     plc = root.findall('./Array/add/PLC')
        #     if len(plc) == 1:
        #         plc[0].attrib['href'] = cfg.plc
        #
        #     ocr = root.findall('./Array/add/OCR')
        #     if len(ocr) == 1:
        #         ocr[0].attrib['href'] = cfg.ocr
        #
        #     llm = root.findall('./Array/add/LLM')
        #     if len(llm) == 1:
        #         llm[0].attrib['href'] = cfg.llm
        #
        #     pointer = root.findall('./Array/add/METER')
        #     if len(pointer) == 1:
        #         pointer[0].attrib['href'] = cfg.pointer
        #
        #     switch = root.findall('./Array/add/SWITCH')
        #     if len(switch) == 1:
        #         switch[0].attrib['href'] = cfg.switch
        #
        #     indicator = root.findall('./Array/add/IDL')
        #     if len(indicator) == 1:
        #         indicator[0].attrib['href'] = cfg.indicator
        #
        #     tree.write(_ui_config_file_)
        #     item['reply'] = True
        #     return item
        #
        # @_app.get("/api/v1/v2v/metrics")
        # async def provide_metrics(deviceid: str, channelid: str):
        #     """C&M之M：接受监控端比如promethus的调用，反馈自己是否在线和反馈各种运行时信息"""
        #     item = {'version': '1.0.0'}
        #     _self_obj.log(deviceid)
        #     _self_obj.log(channelid)
        #     return item
        #
        # # EIF5:REST PTZ CNTL 代理视频调度管理软件，返回当前所有摄像头的描述
        # @_app.get("/api/v1/ptz/streaminfo")
        # async def stream_info():
        #     """获取所有的视频通道列表"""
        #     item = {'version': '1.0.0', 'reply': 'pending.'}
        #     _cfg_dict = _self_obj.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': _self_obj.name})
        #     streams = spdd.get_urls(_cfg_dict['media_service'])
        #     item['streams'] = streams
        #     item['reply'] = True
        #     return item
        #
        # @_app.get("/api/v1/v2v/action/{deviceid}/{channelid}")
        # async def set_process_action(deviceid: str, channelid: str, action: str = 'pause'):
        #     """对单个通道进行开始和关闭操作"""
        #     item = {'version': '1.0.0', 'deviceid': deviceid, 'channelid': channelid, 'reply': 'SUCCEED'}
        #     # 检测传入的did, cid是否合法
        #     if action not in ['pause', 'resume']:
        #         item['reply'] = 'action argument need "pause" or "resume"'
        #         return item
        #     # 在配置文件中检测是否存在该ID
        #     if not _self_obj._check_did_cid_valid(deviceid, channelid):
        #         item['reply'] = 'Invalid deviceid and channelid.'
        #         return item
        #     # 广播消息
        #     process_cmd = {'cmd': action, 'deviceid': deviceid, 'channelid': channelid}
        #     _self_obj.log(f"[API] {action} RTSP process pull stream. --> ")
        #     _ret = _self_obj.call_rpc(bus.CB_PAUSE_RESUME_PIPE, process_cmd)
        #     if not _ret['reply']:
        #         item['reply'] = 'rpc call failed.'
        #     # 返回结果
        #     return item
        #
        # @_app.get("/api/v1/v2v/presets/{deviceid}/{channelid}")
        # async def get_presets(deviceid: str, channelid: str, refresh: bool = False):
        #     """获取该视频通道所有预置点，然后逐个预置点取图，保存为base64，加入流断处理，加入流缓存以及互斥锁保护全局缓存流"""
        #     item = {'version': '1.0.0', 'reply': 'pending.', 'rtsp_url': None}
        #     try:
        #         _cfg_dict = _self_obj.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': _self_obj.name})
        #         _spdd_url = _cfg_dict['media_service']
        #         # 不支持nvrsamples的热更新，因为启动程序需要mount本地目录
        #         _preset_image_path = f'{_nvr_samples_path}{deviceid}/{channelid}/'
        #
        #         # 是否需要重新从预置位获取截图
        #         if refresh:
        #             # 重新获取预置位截图前，需要删除该设备之前的截图文件
        #             # FIXME: 子目录没有分类到通道ID一级，如果一个设备包含多个通道，则删除所有通道的截图，会影响其它通道的配置？
        #             if os.path.exists(_preset_image_path) is True:
        #                 _preset_files = [f'{_preset_image_path}/{f}'
        #                                  for f in listdir(_preset_image_path) if
        #                                  isfile(join(_preset_image_path, f))]
        #                 for file in _preset_files:
        #                     os.remove(file)
        #
        #             _url = spdd.get_rtsp_url(deviceid, channelid, _spdd_url)
        #             _self_obj.log(f"[PRESET API] 1.Get channel rtsp url from SPDD. --> {_url}")
        #             _preset_list = None
        #             if _url:
        #                 # 从spdd取预置位
        #                 _preset_list = spdd.get_presets(deviceid, channelid, _spdd_url)
        #                 _self_obj.log(f"[PRESET API] 2.Get presets list from SPDD. --> {_preset_list}")
        #             if _url and _preset_list:
        #                 # 通知主调度，暂停pipeline流水线对本摄像头的识别操作，直到重新发送resume指令。
        #                 pipeline_cmd = {'cmd': 'pause', 'deviceid': deviceid, 'channelid': channelid}
        #                 _rpc_ret = _self_obj.call_rpc(bus.CB_PAUSE_RESUME_PIPE, pipeline_cmd)
        #                 if not _rpc_ret['reply']:
        #                     _self_obj.log("[PRESET API] 3.Pause RTSP process pull stream failed. --> ",
        #                                   level=log.LOG_LVL_WARN)
        #                     raise RuntimeError(f'Pause RTSP process pull stream failed: {deviceid}, {channelid}.')
        #                 else:
        #                     _self_obj.log("[PRESET API] 3.Pause RTSP process pull stream success. --> ",
        #                                   level=log.LOG_LVL_INFO)
        #                 # FIXME:此处需要等待一定时间，让rtsp进程取流的动作停下来，等多长时间，是个问题。
        #                 time.sleep(5)
        #
        #                 if _url in _self_obj.cached_cvobjs_:
        #                     # 如果缓存过，就直接用缓存的流。
        #                     cvobj = _self_obj.cached_cvobjs_[_url]
        #                 else:
        #                     # 如果这个url没配置过，则打开一个新的对象来取流。
        #                     cvobj = GrabFrame.GrabFrame()
        #                     opened = cvobj.open_stream(_url, GrabFrame.GrabFrame.OPEN_RTSP_TIMEOFF)
        #                     if opened:
        #                         _self_obj.cached_cvobjs_[_url] = cvobj
        #                     else:
        #                         _self_obj.log("[PRESET API] 4.Get rtsp stream cv obj failed. --> ",
        #                                       level=log.LOG_LVL_WARN)
        #                         raise cv2.error(f'Failed to open {_url}.')
        #                 _self_obj.log("[PRESET API] 4.Get rtsp stream cv obj success. --> ")
        #                 # 产生系列预置点图片
        #                 item['rtsp_url'] = _url  # 前端需要了解是否有合法url，才方便下发配置的时候填入正确的配置值
        #                 # 开始遍历预置位，进行截图
        #                 for prs in _preset_list:
        #                     _preset_ret = spdd.run_to_viewpoints(deviceid, channelid,
        #                                                          prs['presetid'],
        #                                                          _spdd_url,
        #                                                          _cfg_dict['ipc_ptz_delay'])
        #                     if _preset_ret is False:
        #                         _self_obj.log(f"[PRESET API] 5.Run to presets {prs['presetid']} failed. --> ",
        #                                       level=log.LOG_LVL_WARN)
        #                         continue
        #                     _self_obj.log(f"[PRESET API] 5.Run to presets {prs['presetid']} success. --> ",
        #                                   level=log.LOG_LVL_INFO)
        #
        #                     # FIXME:旋转预置位后，由于摄像头的物理动作比较慢，因此需要延时等待，待多长时间，是个问题.
        #                     time.sleep(6)
        #                     # 从视频流中取当前帧
        #                     _video_frame_data = cvobj.read_frame()
        #                     if _video_frame_data is None:
        #                         cvobj.stop_stream()
        #                         _self_obj.cached_cvobjs_.pop(_url, None)  # 如果没有读出数据，清空缓存
        #                         _self_obj.log(f"[PRESET API] 6.Get presets {prs['presetid']} image failed. -->",
        #                                       level=log.LOG_LVL_WARN)
        #                         raise cv2.error(f'Got empty frame from cv2.')
        #                     _self_obj.log(f"[PRESET API] 6.Get presets {prs['presetid']} image success. -->",
        #                                   level=log.LOG_LVL_INFO)
        #
        #                     # 保存原始图像
        #                     filename = f'{_preset_image_path}{prs["presetid"]}.png'
        #                     os.makedirs(os.path.dirname(filename), exist_ok=True)
        #                     cv2.imwrite(filename, _video_frame_data)
        #                     _self_obj.log(f"[PRESET API] 7.Save preset{prs['presetid']} image to png {filename}. -->",
        #                                   level=log.LOG_LVL_INFO)
        #
        #                     # 保存缩略图，1920x1080的长宽缩小20倍
        #                     _video_frame_data = imutils.resize(_video_frame_data, width=96, height=54)
        #                     buf = io.BytesIO()
        #                     plt.imsave(buf, _video_frame_data, format='png')
        #                     image_data = buf.getvalue()
        #                     image_data = base64.b64encode(image_data)
        #                     outfile = open(f'{_preset_image_path}{prs["presetid"]}', 'wb')
        #                     outfile.write(image_data)
        #                     outfile.close()
        #                     _self_obj.log(f"[PRESET API] 8.Save preset {prs['presetid']} image to base64 file. -->",
        #                                   level=log.LOG_LVL_INFO)
        #             else:
        #                 # 不是合法的设备号
        #                 errmsg = f'查询RTSP地址或获取预置点失败，摄像头信息:{deviceid}-{channelid}.'
        #                 item['reply'] = errmsg
        #                 raise ValueError(errmsg)
        #         onlyfiles = [f'{baseurl_of_nvr_samples_}/{deviceid}/{channelid}/{f}'
        #                      for f in listdir(_preset_image_path) if
        #                      isfile(join(_preset_image_path, f)) and ('.png' not in f)]
        #         # 返回视频的原始分辨率，便于在前端界面了解和载入
        #         # 有问题，如果没有初始化流（fresh=False）,为了获取png文件尺寸，选第一个文件来查询其尺寸
        #         pngfiles = [fn for fn in listdir(_preset_image_path) if
        #                     isfile(join(_preset_image_path, fn)) and ('.png' in fn)]
        #         if len(pngfiles) > 0:
        #             item['reply'] = True
        #             item['presets'] = onlyfiles
        #             pngfile = f'{_preset_image_path}{pngfiles[0]}'
        #             item['width'], item['height'] = wpr.get_picture_size(pngfile)
        #             _self_obj.log(f"[PRESET API] API work success. -->")
        #         else:
        #             item['reply'] = False
        #             item['desc'] = '没有生成可标注的图片.'
        #             _self_obj.log(f"[PRESET API] API work failed. -->", level=log.LOG_LVL_WARN)
        #     except FileNotFoundError as err:
        #         _self_obj.log(f'[FileNotFoundError] Web api get_presets: {err}', level=log.LOG_LVL_ERRO)
        #         item['reply'] = False
        #         item['desc'] = '图片文件不存在.'
        #     except ValueError as err:
        #         _self_obj.log(f'[ValueError] Web api get_presets: {err}', level=log.LOG_LVL_ERRO)
        #     except RuntimeError as err:
        #         _self_obj.log(f'[RuntimeError] Web api get_presets: {err}', level=log.LOG_LVL_ERRO)
        #     except cv2.error as err:
        #         _self_obj.log(f'[cv2.error] Web api get_presets: {err}', level=log.LOG_LVL_ERRO)
        #     else:
        #         _self_obj.log(f'Preset pictures done.', level=log.LOG_LVL_INFO)
        #     finally:
        #         pipeline_cmd = {'cmd': 'resume', 'deviceid': deviceid, 'channelid': channelid}
        #         _rpc_ret = _self_obj.call_rpc(bus.CB_PAUSE_RESUME_PIPE, pipeline_cmd)
        #         _self_obj.log(f"[PRESET API] Finally Resume RTSP process to pull stream. --> {_rpc_ret}",
        #                       level=log.LOG_LVL_INFO)
        #         return item
        #
        # class Directory(BaseModel):
        #     datedir: str = '2022-02-11'
        #
        # @_app.post("/api/v1/v2v/pixgallery")
        # async def pixgallery(item: Directory):
        #     """把参数指定日期得视频识别结果打包为可访问的web服务，返回url地址"""
        #     ret = {'version': '1.0.0', 'reply': False}
        #     _image_path = f'{_nvr_samples_path}airesults/{item.datedir}'
        #     res = gallery_create(_image_path)
        #     if res:
        #         res = gallery_build(_image_path)
        #         if res:
        #             visit_url = f'{baseurl_of_nvr_samples_}/airesults/{item.datedir}/public/index.html'
        #             ret = {'version': '1.0.0', 'reply': res, 'url': visit_url}
        #     return ret

        @_app.on_event("shutdown")
        def shutdown():
            """关闭事件"""
            pass

        return _app

    def up_time(self) -> Callable[[Info], None]:
        metric = Gauge(
            "up_time",
            "开机持续运行时间.",
            labelnames=("application",)
        )
        sts_ = int(time.time())  # 秒为单位
        _self_obj = self

        def instrumentation(info: Info) -> None:  # noqa
            # rest_.log(f'Promethues scrape request: {info.request.url}')
            # 主进程的运行时间累计
            nonlocal sts_
            current = int(time.time())
            delta = current - sts_
            metric.labels('main').set(delta)

            # 收集子进程监测数据(数据结构是{'result':{'AIxx':{'up': 1.1, 'xx': 2}, ... }})
            proc_metrics = _self_obj.call_rpc(bus.CB_GET_METRICS, {'cmd': 'get_metrics', 'desc': 'rest api is called.'})
            res = proc_metrics['result_metrics']
            for key in res.keys():
                item = res[key]
                if 'up' in item.keys():
                    metric.labels(key).set(item['up'])

        return instrumentation

    def run(self):
        self.log(f'Create FASTAPI object.', level=log.LOG_LVL_DBG)
        _web_app_obj = self.create_app()

        # 只要有rest请求，就会触发添加的这几个统计函数，向主进程请求监测数据。
        instrumentator = Instrumentator(
            # excluded_handlers=[".*admin.*", "/metrics"],
        )
        instrumentator.add(self.up_time())
        instrumentator.add(cpu_rate())
        instrumentator.add(mem_rate())
        # 临时不需要提供在线监测功能
        # instrumentator.instrument(_web_app_obj).expose(_web_app_obj)

        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["formatters"]["default"]["fmt"] = log.get_v2v_logger_formatter()
        log_config["formatters"]["access"]["fmt"] = log.get_v2v_logger_formatter()
        log_config["loggers"]['uvicorn.error'].update({"propagate": False, "handlers": ["default"]})

        self.log(f'Run http web server. port: {self.port_}', log.LOG_LVL_INFO)
        uvicorn.run(_web_app_obj,  # noqa 标准用法
                    host="0.0.0.0",
                    port=self.port_,
                    # ssl_keyfile=self.ssl_keyfile_,
                    # ssl_certfile=self.ssl_certfile_,
                    log_level=logging.INFO,
                    log_config=log_config
                    )
