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
Sub process base class  module
=========================

All common behaviors of sub process.
"""
import functools
import time
from utils import bus, log, V2VErr


class BaseProcWorker:
    def __init__(self, name, dicts, **kwargs):
        # 进程名称 NAME(PID)
        self.name = name
        self.log = functools.partial(log.logger, f'{name}')

        self._is_break_out_startup = None
        # 获取从主进程传输的进程间共享值，用于标记是否该退出子进程的startup阶段
        for key, value in dicts.items():
            if key == 'share_list':
                self._is_break_out_startup = value
                self.log(f"[__init__] Got startup exit status: {self._is_break_out_startup}")
                break
        # 用于标识是否该退出子进程的main_loop阶段
        self.is_break_out_main_loop = False

    def main_loop(self):
        self.log("Entering main_loop.")
        raise NotImplementedError(f"{self.__class__.__name__}.main_loop is not implemented")

    def startup(self):
        self.log("Entering startup.")
        pass

    def shutdown(self):
        self.log("Entering shutdown.")
        pass

    def main_func(self, event=None, *args):
        self.log("Entering main_func.")
        raise NotImplementedError(f"{self.__class__.__name__}.main_func is not implemented")

    def get_exit_state(self):
        # 定义公共函数，用于查询是否该退出子进程.
        # 主要用于RTSP子进程，在执行预置位操作时，阻塞旋转，无法接收退出事件，导致退出流程阻塞
        if self._is_break_out_startup and self._is_break_out_startup[0] is True:
            return True
        else:
            return False

    def run(self):
        _is_restart = True
        while _is_restart:
            try:
                # 由于架构限制，在startup阶段无法接收EMQ事件，因此通过进程间的共享状态标记是否该退出startup阶段.
                # 该值在创建子进程时，由主进程传入，状态变更由主进程负责.
                if self._is_break_out_startup and self._is_break_out_startup[0] is True:
                    raise V2VErr.V2VTaskExitStartupStage('Exit startup stage.')
                self.startup()
                self.main_loop()
                self.shutdown()
            except V2VErr.V2VTaskExitStartupStage as err:
                _is_restart = False
                self.log(f"V2VTaskExitStartupStage: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
            except V2VErr.V2VConfigurationIllegalError as err:
                # 发生配置不合法，等待配置下发正确，发生在startup，可以不shutdown，避免引入新的错误。
                _is_restart = True
                self.log(f"V2VConfigurationIllegalError: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
                time.sleep(1)
            except V2VErr.V2VConfigurationChangedError as err:
                # 发生运行时配置更新，先shutdown，完成资源回收，再重启动，发生在main_loop。
                _is_restart = True
                self.log(f"V2VConfigurationChangedError: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
                self.shutdown()
                time.sleep(1)
            except V2VErr.V2VTaskNullRtspUrl as err:
                # 暂时没活干也不要退出，毕竟流水线后面还起了ai，mqtt几个等着吧。
                _is_restart = True
                self.log(f"V2VTaskNullRtspUrl: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
                time.sleep(5)
        self.log(f"[EXIT] BaseProcWorker run loop. restart:{_is_restart}", level=log.LOG_LVL_INFO)


class ProcWorker(BaseProcWorker, bus.IEventBusMixin):
    def __init__(self, name, topic, dicts, **kwargs):
        super().__init__(name, dicts, **kwargs)
        self._start_time = time.time()                                      # 记录进程启动的时间戳
        self.beeper_ = bus.IEventBusMixin.get_beeper()                   # req-rep客户端。
        self.subscriber_ = bus.IEventBusMixin.get_subscriber(topic)      # pub-sub订阅端。

    def call_rpc(self, method, param):
        self.send_cmd(method, param)
        ret = self.recv_cmd()
        return ret

    def main_loop(self):
        try:
            while self.is_break_out_main_loop is False:
                evt = self.subscribe()
                if evt == bus.EBUS_SPECIAL_MSG_STOP:        # 共性操作：停止子进程
                    self.log("Recv EBUS_SPECIAL_MSG_STOP event.")
                    break
                elif evt == bus.EBUS_SPECIAL_MSG_CFG:       # 共性操作：配置发生更新
                    self.log("Recv EBUS_SPECIAL_MSG_CFG event.")
                    raise V2VErr.V2VConfigurationChangedError(evt)
                elif evt:                                   # 其它广播事件，比如停止某个通道
                    self.log(f'Got event in mainloop: {evt}.')
                # 在每次循环完毕上报一次运行时间。
                delta = time.time() - self._start_time
                self.call_rpc(bus.CB_SET_METRICS, {'up': delta, 'application': self.name})
                self.is_break_out_main_loop = self.main_func(evt)
            self.log('[EXIT] Leaving main_loop.')
        except KeyboardInterrupt:
            self.log(f'Caught KeyboardInterrupt event.', level=log.LOG_LVL_ERRO)
            self.beeper_.disconnect()
            self.beeper_.close()
            self.subscriber_.disconnect()
            self.subscriber_.close()
