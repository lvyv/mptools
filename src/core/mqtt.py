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
mqtt module
=========================

Publish recognized results to iot gateway.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import paho.mqtt.client as mqtt_client
import json
import socket
from utils import bus, log
from core.procworker import ProcWorker
from utils.tracing import AdaptorTracingUtility
from opentracing import global_tracer


class MqttWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.mqtt_cid_ = None   # 这个名字无所谓，在网关处会重新mapping key-value到正确的设备号
        self.mqtt_pwd_ = None
        self.mqtt_host_ = None
        self.mqtt_port_ = None
        self.mqtt_topic_ = None
        self.fsvr_url_ = None
        for key, value in dicts.items():
            if key == 'mqtt_host':
                self.mqtt_host_ = value
            elif key == 'mqtt_port':
                self.mqtt_port_ = value
            elif key == 'mqtt_cid':
                self.mqtt_cid_ = value
            elif key == 'mqtt_pwd':
                self.mqtt_pwd_ = value
            elif key == 'mqtt_topic':
                self.mqtt_topic_ = value
            elif key == 'fsvr_url':
                self.fsvr_url_ = value
            elif key == 'jaeger':
                self.jaeger_ = value

        # cfg = self.call_rpc(bus.CB_GET_CFG, {})                               # 进程创建的时候传入配置参数，不需要实时获取
        if self.jaeger_:
            if self.jaeger_['enable']:
                # init opentracing jaeger client
                aip = self.jaeger_['agent_ip']
                apt = self.jaeger_['agent_port']
                servicename = f'v2v-mqtt-{socket.gethostname()}'
                AdaptorTracingUtility.init_tracer(servicename, agentip=aip, agentport=apt)
                # 缓存tracer便于后面使用
                self.tracer_ = global_tracer()

        self.client_ = None

    def startup(self):
        try:
            self.client_ = mqtt_client.Client()

            if self.mqtt_cid_ and self.mqtt_pwd_:
                self.client_.username_pw_set(self.mqtt_cid_, self.mqtt_pwd_)

            self.client_.connect(self.mqtt_host_, self.mqtt_port_)
            self.client_.loop_start()
        except Exception as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
            raise RuntimeError(f'Cannot connect to mqtt svr:{self.mqtt_host_}:{self.mqtt_port_}')

    def main_func(self, event=None, *args):
        # 全速
        # self.log('mqtt begin get data.')
        vec = self.in_q_.get()

        payload = json.loads(str(vec.decode('utf-8')))
        data = {'payload': payload}

        if 'tracer_' in dir(self):    # 如果配置项有jaeger，将记录
            with self.tracer_.start_active_span('v2v_mqtt_publish_msg') as scope:       # 带内数据插入trace id
                scope.span.set_tag('originalMsg', vec.decode('utf-8'))
                span = self.tracer_.active_span
                AdaptorTracingUtility.inject_span_ctx(self.tracer_, span, data)

        self.client_.publish(self.mqtt_topic_, json.dumps(data), 1)
        self.log(f'发送到mqtt服务器：{data}')

        return False

    def shutdown(self):
        self.client_.loop_stop()
        self.client_.disconnect()
        self.client_ = None
