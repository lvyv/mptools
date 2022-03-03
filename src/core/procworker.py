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
        self.name = name
        self.log = functools.partial(log.logger, f'{name}')
        self.break_out_ = False

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

    def running_logic(self):
        re_run = False
        try:
            self.startup()
            self.main_loop()
            self.shutdown()
        except V2VErr.V2VConfigurationIllegalError as err:
            # 发生配置不合法，等待配置下发正确，发生在startup，可以不shutdown，避免引入新的错误。
            self.log(f"V2VConfigurationIllegalError: {err}", level=log.LOG_LVL_ERRO)
            re_run = True
        except V2VErr.V2VConfigurationChangedError as err:
            # 发生运行时配置更新，先shutdown，完成资源回收，再重启动，发生在main_loop。
            self.log(f"V2VConfigurationChangedError: {err}", level=log.LOG_LVL_ERRO)
            re_run = True
            self.shutdown()
        except V2VErr.V2VTaskNullRtspUrl as err:
            # 暂时没活干也不要退出，毕竟流水线后面还起了ai，mqtt几个等着吧。
            self.log(f"V2VTaskNullRtspUrl: {err}", level=log.LOG_LVL_ERRO)
            re_run = True
            time.sleep(5)
        finally:
            return re_run

    def run(self):
        _is_restart = True
        while _is_restart:
            _is_restart = self.running_logic()
            if _is_restart is True:
                self.log(f"BaseProcWorker restart run.", level=log.LOG_LVL_WARN)
        self.log(f"Exit BaseProcWorker run. {_is_restart}", level=log.LOG_LVL_INFO)


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
            while self.break_out_ is False:
                evt = self.subscribe()
                if evt == bus.EBUS_SPECIAL_MSG_STOP:        # 共性操作：停止子进程
                    self.log("Recv EBUS_SPECIAL_MSG_STOP event.")
                    break
                elif evt == bus.EBUS_SPECIAL_MSG_CFG:       # 共性操作：配置发生更新
                    self.log("Recv EBUS_SPECIAL_MSG_CFG event.")
                    raise V2VErr.V2VConfigurationChangedError(evt)
                elif evt:                                   # 其它广播事件，比如停止某个通道
                    self.log(f'Got message: {evt}.')
                # 在每次循环完毕上报一次运行时间。
                delta = time.time() - self._start_time
                self.call_rpc(bus.CB_SET_METRICS, {'up': delta, 'application': self.name})
                self.break_out_ = self.main_func(evt)
            self.log('Leaving main_loop.')
        except KeyboardInterrupt:
            self.log(f'Caught KeyboardInterrupt----', level=log.LOG_LVL_ERRO)
            self.beeper_.disconnect()
            self.beeper_.close()
            self.subscriber_.disconnect()
            self.subscriber_.close()
