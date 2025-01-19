#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 The OPTiDOCK Authors. All Rights Reserved.
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
import logging
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from uvicorn.main import Server

from core.procworker import ProcWorker
from third_api import spdd
from utils import bus, log

# 猴子补丁：在退出本进程的时候，ctrl+c会等待较长时间关闭socket
original_handler = Server.handle_exit


class AppStatus:
    should_exit = False

    @staticmethod
    def handle_exit(*args, **kwargs):
        AppStatus.should_exit = True
        original_handler(*args, **kwargs)


Server.handle_exit = AppStatus.handle_exit


class DockRestWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, args_dict=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_REST, args_dict, **kwargs)  # 不订阅rtsp、ai、mqtt等线程主题，避免被停等
        self.port_ = None
        self.ssl_keyfile_ = None
        self.ssl_certfile_ = None
        ms_cfg = args_dict['micro_service']
        for key, value in ms_cfg.items():
            if key == 'http_port':
                self.port_ = value
            elif key == 'ssl_keyfile':
                self.ssl_keyfile_ = value
            elif key == 'ssl_certfile':
                self.ssl_certfile_ = value

        self.log(f'The queues are not necessary, in_q: {in_q}, out_q: {out_q}', log.LOG_LVL_INFO)

    # 创建Web服务器
    def create_app(self) -> FastAPI:
        _app = FastAPI(
            title="机器视觉网络系统",
            description="视频图像智能分析RESTful API接口",
            version="3.2.0", )

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

        # EIF3:REST V2V C&M 外部接口-提供UI前端配置V2V需要的截图
        # 本路由为前端ui的路径，该路径相对于当前文件
        _pwd_path = Path(Path(__file__).parent)
        _app.mount('/static', StaticFiles(directory=str(_pwd_path.joinpath("../swagger_ui_dep/static"))), name='static')

        class Switch(BaseModel):
            cmd: str = 'start'

        @_app.post("/api/v1/v2v/pipeline/")
        async def pipeline(item: Switch):
            """统一关闭或启动rtsp，ai，mqtt子进程"""
            cmds = ['start', 'stop']
            if item.cmd in cmds:
                if item.cmd == 'start':
                    ret = _self_obj.call_rpc(bus.CB_STARTUP_PPL, {'cmd': item.cmd})  # noqa
                else:
                    ret = _self_obj.call_rpc(bus.CB_STOP_PPL, {'cmd': item.cmd})  # noqa
            else:
                ret = {'reply': 'unrecognized command.'}
            return ret

        @_app.on_event("shutdown")
        def shutdown():
            """关闭事件"""
            pass

        return _app

    def run(self):
        self.log(f'Create FASTAPI object.', level=log.LOG_LVL_DBG)
        _web_app_obj = self.create_app()

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
