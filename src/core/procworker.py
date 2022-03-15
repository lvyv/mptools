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
import os
import time

from core.pools import ProcessState
from utils import bus, log, V2VErr


class BaseProcWorker:
    def __init__(self, name, dicts, **kwargs):
        # 进程名称 NAME(PID)
        self.name = name
        # 用于标识是否该退出子进程的main_loop阶段
        self.is_break_out_main_loop = False
        self.log = functools.partial(log.logger, f'{name}')

    def main_loop(self):
        self.log("Entering main_loop.")
        raise NotImplementedError(f"{self.__class__.__name__}.main_loop is not implemented")

    def startup(self, event=None):
        self.log("Entering startup.")
        pass

    def shutdown(self):
        self.log("Entering shutdown.")
        pass

    def main_func(self, event=None, *args):
        self.log("Entering main_func.")
        raise NotImplementedError(f"{self.__class__.__name__}.main_func is not implemented")


class ProcWorker(BaseProcWorker, bus.IEventBusMixin):
    def __init__(self, name, topic, dicts, **kwargs):
        super().__init__(name, dicts, **kwargs)
        self._start_time = time.time()                                      # 记录进程启动的时间戳
        self.beeper_ = bus.IEventBusMixin.get_beeper()                   # req-rep客户端。
        self.subscriber_ = bus.IEventBusMixin.get_subscriber(topic)      # pub-sub订阅端。
        # 进程状态
        # type: ProcessState
        self._process_state = ProcessState.INIT

    # 设备编号
    @property
    def state(self):
        return self._process_state

    @state.setter
    def state(self, value: ProcessState):
        if self._process_state == value:
            return
        _pre_state = self._process_state
        self._process_state = value

        # {name: 'NAME(PID)', pid: pid, pre_state: ProcessState.number, new_state: ProcessState.number}
        _params = {'name': self.name,
                   'pid': os.getpid(),
                   'pre_state': _pre_state.value,
                   'new_state': value.value
                   }
        # 通知主进程
        self.call_rpc(bus.CB_UPDATE_PROCESS_STATE, _params)

    def call_rpc(self, method, param):
        self.send_cmd(method, param)
        ret = self.recv_cmd()
        return ret

    def close_zmq(self):
        if self.beeper_ is not None:
            self.beeper_.disconnect()
            self.beeper_.close()
            self.beeper_ = None
        if self.subscriber_ is not None:
            self.subscriber_.disconnect()
            self.subscriber_.close()
            self.subscriber_ = None
        self.log("[BASE] ProcWorker Close ZMQ handle.", level=log.LOG_LVL_INFO)

    def proc_broadcast_msg(self, evt):
        if not evt:
            return
        if evt == bus.EBUS_SPECIAL_MSG_STOP:  # 共性操作：停止子进程
            self.log("[BASE] Recv EBUS_SPECIAL_MSG_STOP event.")
            raise V2VErr.V2VTaskExitProcess('V2VTaskExitProcess.')
        elif evt == bus.EBUS_SPECIAL_MSG_CFG:  # 共性操作：配置发生更新
            self.log("[BASE] Recv EBUS_SPECIAL_MSG_CFG event.")
            raise V2VErr.V2VConfigurationChangedError('V2VConfigurationChanged.')
        elif evt:
            pass

    def main_loop(self):
        while self.is_break_out_main_loop is False:
            evt = self.subscribe()
            self.proc_broadcast_msg(evt)
            # 在每次循环完毕上报一次运行时间。
            delta = time.time() - self._start_time
            self.call_rpc(bus.CB_SET_METRICS, {'up': delta, 'application': self.name})
            # 调用子类中的main_func函数
            self.is_break_out_main_loop = self.main_func(evt)
        self.log(f'[EXIT] Leaving main_loop. {self.is_break_out_main_loop}', level=log.LOG_LVL_INFO)

    def run(self):
        _is_restart = True
        while _is_restart:
            try:
                evt = self.subscribe()
                self.proc_broadcast_msg(evt)
                self.state = ProcessState.START
                # 进程初始化
                self.startup(evt)
                # 进程主循环
                self.state = ProcessState.RUN
                self.main_loop()
                # 进程清理阶段
                self.state = ProcessState.SHUT
                self.shutdown()
                break
            except V2VErr.V2VTaskExitProcess as err:
                self.log(f"[BASE] V2VTaskExitProcess: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
                self.shutdown()
                break
            except V2VErr.V2VConfigurationIllegalError as err:
                # 发生配置不合法，等待配置下发正确，发生在startup，可以不shutdown，避免引入新的错误。
                _is_restart = True
                self.log(f"[BASE] V2VConfigurationIllegalError: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
                # time.sleep(1)
            except V2VErr.V2VConfigurationChangedError as err:
                # 发生运行时配置更新，先shutdown，完成资源回收，再重启动，发生在main_loop。
                _is_restart = True
                self.log(f"[BASE] V2VConfigurationChangedError: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
                self.shutdown()
                # time.sleep(1)
            except V2VErr.V2VTaskNullRtspUrl as err:
                # 暂时没活干也不要退出，毕竟流水线后面还起了ai，mqtt几个等着吧。
                _is_restart = True
                self.log(f"[BASE] V2VTaskNullRtspUrl: {err} restart:{_is_restart}", level=log.LOG_LVL_ERRO)
            except KeyboardInterrupt:
                self.log(f'Caught KeyboardInterrupt event in run loop.', level=log.LOG_LVL_ERRO)
                self.close_zmq()
            except Exception as err:
                self.log(f'[BASE] Unknown error:{err}', level=log.LOG_LVL_ERRO)
        self.log(f"[__exit__] Leaving run loop. restart:{_is_restart}", level=log.LOG_LVL_ERRO)