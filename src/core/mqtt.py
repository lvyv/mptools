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
from utils import bus, log, V2VErr
from core.procworker import ProcWorker
from utils.tracing import AdaptorTracingUtility
from opentracing import global_tracer


class MqttWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.mqtt_cid_ = None   # 这个名字无所谓，在网关处会重新mapping key-value到正确的设备号
        self.mqtt_usr_ = None
        self.mqtt_pwd_ = None
        self.mqtt_host_ = None
        self.mqtt_port_ = None
        self.mqtt_topic_ = None
        self.fsvr_url_ = None
        self.jaeger_ = None
        for key, value in dicts.items():
            if key == 'mqtt_host':
                self.mqtt_host_ = value
            elif key == 'mqtt_port':
                self.mqtt_port_ = value
            elif key == 'mqtt_cid':
                self.mqtt_cid_ = value
            elif key == 'mqtt_cid':
                self.mqtt_usr_ = value
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
                nodename = self.jaeger_['node_name']
                servicename = f'v2v_{nodename}'
                AdaptorTracingUtility.init_tracer(servicename, agentip=aip, agentport=apt)
                # 缓存tracer便于后面使用
                self.tracer_ = global_tracer()

        self.client_ = None

    def startup(self):
        try:
            # 1.尝试获取配置数据
            self.log(f'{self.name} started......')
            cfg = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': self.name})
            mqttcfg = cfg['mqtt_svrs'][0]
            self.mqtt_host_ = mqttcfg['mqtt_svr']
            self.mqtt_port_ = mqttcfg['mqtt_port']
            self.mqtt_cid_ = mqttcfg['mqtt_cid']
            self.mqtt_usr_ = mqttcfg['mqtt_usr']
            self.mqtt_pwd_ = mqttcfg['mqtt_pwd']

            self.mqtt_topic_ = mqttcfg['mqtt_tp']
            self.fsvr_url_ = mqttcfg['fsvr_url']
            self.client_ = mqtt_client.Client(self.mqtt_cid_)

            self.client_.username_pw_set(self.mqtt_usr_, self.mqtt_pwd_)
            self.client_.connect(self.mqtt_host_, self.mqtt_port_)
            self.client_.loop_start()
        except (socket.gaierror, TimeoutError, UnicodeError, ConnectionRefusedError) as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
            msg = f'Cannot connect to {self.mqtt_host_}:{self.mqtt_port_} with {self.mqtt_cid_}/{self.mqtt_pwd_}'
            raise V2VErr.V2VConfigurationIllegalError(msg)
        except (KeyError, ValueError, Exception) as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
            raise V2VErr.V2VConfigurationIllegalError(err)

    def main_func(self, event=None, *args):
        # 全速
        # self.log('mqtt begin get data.')
        vec = self.in_q_.get()

        payload = json.loads(str(vec.decode('utf-8')))
        data = {'payload': payload}

        if 'tracer_' in dir(self):    # 如果配置项有jaeger，将记录
            # inject和extract配合使用，先extract去取出数据包中的metadata的traceid的span上下文，
            # 然后再对上下文进行操作，并把它注入到下一个环节，因为mqtt这个进程是本模块的起点，因此只有inject。
            nodename = self.jaeger_['node_name']
            with self.tracer_.start_active_span(f'v2v_mqtt_{nodename}_send_msg') as scope:       # 带内数据插入trace id
                scope.span.set_tag('originalMsg', vec.decode('utf-8'))
                scope.span.set_tag('link.localHost', socket.gethostname())
                scope.span.set_tag('link.remoteHost', self.mqtt_host_)
                span = self.tracer_.active_span
                AdaptorTracingUtility.inject_span_ctx(self.tracer_, span, data)

        self.client_.publish(self.mqtt_topic_, json.dumps(data), 1)
        self.log(f'发送到mqtt服务器：{data}')

        return False

    def shutdown(self):
        self.client_.loop_stop()
        self.client_.disconnect()
        self.client_ = None
