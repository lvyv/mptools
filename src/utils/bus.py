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
bus module
=========================

Event bus of all processes.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import zmq
import json
import functools
from . import log
# 特殊的通讯主题

EBUS_TOPIC_REST = 'rest'
EBUS_TOPIC_BROADCAST = 'broadcast'  # 广播主题

# 特殊的广播总线事件，用于所有子进程的共性行为，广播主题目前只有一个EBUS_TOPIC_BROADCAST
# 每个广播消息的CODE必须唯一.
EBUS_SPECIAL_MSG_STOP = {'code': 0, 'desc': 'END'}               # 在基类处理的广播消息，退出主循环
EBUS_SPECIAL_MSG_CFG = {'code': 1, 'desc': 'CONFIG'}             # 在基类处理的广播消息，所有配置发生更新
EBUS_SPECIAL_MSG_METRICS = {'code': 2, 'desc': 'METRICS'}        # 在基类处理的广播消息，采集监控指标
EBUS_SPECIAL_MSG_STOP_RESUME_PIPE = {'code': 3, 'desc': 'METRICS'}  # 子类中处理，启停某个流水线
EBUS_SPECIAL_MSG_CHANNEL_CFG = {'code': 4, 'desc': 'CONFIG'}             # 子类中处理，单个通道配置发生更新

# 特殊的call_rpc远程方法
CB_STARTUP_PPL = 'start'                # 开始流水线
CB_STOP_PPL = 'stop'                    # 停止流水线
CB_GET_CFG = 'get_cfg'                  # 获取配置文件
CB_SET_CFG = 'set_cfg'                  # 设置所有通道的配置
CB_SET_CHANNEL_CFG = 'set_channel_cfg'  # 设置单个通道的配置
CB_SAVE_CFG = 'save_cfg'                # 写文件
CB_STOP_REST = 'stop_rest'
CB_SET_METRICS = 'set_metrics'
CB_GET_METRICS = 'get_metrics'
CB_PAUSE_RESUME_PIPE = 'pause_resume_pipe'  # 暂停/启用进程
CB_UPDATE_PROCESS_STATE = 'update_process_state'


class IEventBusMixin:
    address_ = 'tcp://127.0.0.1:13131'
    broadcast_address_ = 'tcp://127.0.0.1:13132'
    center_ = None          # 单例req-reply服务器
    handlers_ = {}          # 远程调用的处理函数注册容器表
    broadcaster_ = None     # 单例pub-sub服务器
    log = functools.partial(log.logger, f'{"IEventBusMixin"}')

    @classmethod
    def register(cls, method, callback):
        cls.handlers_[method] = callback

    @classmethod
    def get_beeper(cls):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(cls.address_)
        return socket

    @classmethod
    def get_center(cls):
        socket = None
        if cls.center_ is None:
            context = zmq.Context()
            socket = context.socket(zmq.REP)
            socket.bind(cls.address_)
            cls.center_ = socket
        return socket

    @classmethod
    def get_broadcaster(cls):
        socket = None
        if cls.broadcaster_ is None:
            context = zmq.Context()
            socket = context.socket(zmq.PUB)
            socket.bind(cls.broadcast_address_)
            cls.broadcaster_ = socket
        return socket

    @classmethod
    def get_subscriber(cls, topic=None):
        #  Socket to talk to server
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(cls.broadcast_address_)
        socket.setsockopt_string(zmq.SUBSCRIBE, topic)  # noqa
        return socket

    @classmethod
    def rpc_service(cls):
        """单例范式：响应远程调用"""
        bus = cls.center_
        # If NOBLOCK is set, this method will raise a ZMQError with EAGAIN if a message is not ready.
        msg = bus.recv(flags=zmq.NOBLOCK).decode('utf-8')
        ret = cls.rpc_implemention(msg)
        bus.send_string(ret)
        return True


    @classmethod
    def rpc_implemention(cls, msg):
        """服务端程序收到客户端数据，在本函数中进行处理，输入需要为json字符串，返回值也需要为json字符串"""
        ret = None
        try:
            ret = json.loads(msg)
            method = ret['method']
            func = cls.handlers_[method]
            if func:
                ret = func(ret['params'])
            ret = json.dumps(ret)
        except json.decoder.JSONDecodeError:
            ret = json.dumps({'reply': 'Illegal input string values.'})
        except KeyError:
            ret = json.dumps({'reply': 'No corresponding method handler.'})
        finally:
            return ret

    @classmethod
    def broadcast(cls, topic, msg):
        """
        Mixin函数，负责广播。

        Parameters
        ----------
        topic: str，广播主题。
        msg: dict，广播消息。

        Returns
        -------
            无返回值。
        """
        try:
            if cls.broadcaster_ is None:    # noqa
                raise Exception("broadcast must be set.")

            bus = cls.broadcaster_         # noqa
            cmdstr = json.dumps(msg)
            bus.send_string(f'{topic}:{cmdstr}')
        except TypeError as err:
            cls.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)        # noqa

    def subscribe(self):
        """
        Mixin函数，负责订阅广播消息。

        Parameters
        ----------
            无参数值。
        Returns
        -------
            dict对象。
        """
        ret = None
        try:
            if self.subscriber_ is None:        # noqa
                raise Exception("self.subscriber_ must be set.")
            bus = self.subscriber_              # noqa
            # bus.setsockopt_string(zmq.SUBSCRIBE, topic)  # noqa
            msg = bus.recv_string(flags=zmq.NOBLOCK)
            idx = msg.index(':') + 1
            ret = json.loads(msg[idx:])
        except json.decoder.JSONDecodeError as err:
            IEventBusMixin.log(f'{err}', level=log.LOG_LVL_ERRO)
        finally:
            return ret

    def recv_cmd(self):
        """
        Mixin函数，负责接受网络侧数据，阻塞。

        Parameters
        ----------
            无参数值。
        Returns
        -------
            dict对象。
        """
        ret = None
        try:
            if self.beeper_ is None:        # noqa
                raise Exception("self.beeper_ must be set.")
            bus = self.beeper_              # noqa
            msg = bus.recv().decode('utf-8')
            ret = json.loads(msg)
        except json.decoder.JSONDecodeError as err:
            IEventBusMixin.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)   # noqa
        finally:
            return ret

    def send_cmd(self, method, params):
        """
        Mixin函数，负责封装发送命令。

        Parameters
        ----------
        method: str，调用的远程方法名称。
        params: dict，远程方法的参数。

        Returns
        -------
            无返回值。
        """
        try:
            if self.beeper_ is None:    # noqa
                raise Exception("evt_bus_ must be set.")

            bus = self.beeper_          # noqa
            cmdstr = json.dumps({'method': method, 'params': params})  # 不需要encode为utf-8，编辑器设置缺省就是utf-8编码。
            bus.send_string(cmdstr)
        except TypeError as err:
            IEventBusMixin.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
