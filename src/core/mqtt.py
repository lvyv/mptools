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

import json
import queue
import socket
import time

import paho.mqtt.client as mqtt_client

from core.procworker import ProcWorker
from utils import bus, log, V2VErr
from utils.tracing import AdaptorTracingUtility


# from opentracing import global_tracer


class MqttWorker(ProcWorker):
    @classmethod
    def reset_jaeger(cls, aip, apt, nodename):
        servicename = f'v2v_{nodename}'
        # AdaptorTracingUtility.init_tracer(servicename, agentip=aip, agentport=apt)
        # return global_tracer()
        return AdaptorTracingUtility.init_tracer(servicename, agentip=aip, agentport=apt)

    def __init__(self, name, in_q=None, out_q=None, args_dict=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, args_dict, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.mqtt_cid_ = None   # 这个名字无所谓，在网关处会重新mapping key-value到正确的设备号
        self.mqtt_usr_ = None
        self.mqtt_pwd_ = None
        self.mqtt_host_ = None
        self.mqtt_port_ = None
        self._mqtt_pub_topic = None
        self.fsvr_url_ = None
        self.node_name_ = None
        self.jaeger_ = None
        self.tracer_ = None
        self._mqtt_client_obj = None
        for key, value in args_dict.items():
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
                self._mqtt_pub_topic = value
            elif key == 'fsvr_url':
                self.fsvr_url_ = value
            elif key == 'node_name':
                self.node_name_ = value

        # 从主进程获取配置参数
        _base_cfg_dict = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_basecfg', 'source': self.name})
        self.jaeger_ = _base_cfg_dict['jaeger']
        if self.jaeger_['enable']:
            # init opentracing jaeger client
            aip = self.jaeger_['agent_ip']
            apt = self.jaeger_['agent_port']
            nodename = self.jaeger_['node_name']
            servicename = f'v2v_{nodename}'
            # 缓存tracer便于后面使用
            # AdaptorTracingUtility.init_tracer(servicename, agentip=aip, agentport=apt)
            # self.tracer_ = global_tracer()
            self.tracer_ = AdaptorTracingUtility.init_tracer(servicename, agentip=aip, agentport=apt)

    def startup(self, evt=None):
        try:
            # 1.尝试获取配置数据
            self.log(f'Enter startup.')
            _base_cfg_dict = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_cfg', 'source': self.name})
            _mqtt_cfg_dict = _base_cfg_dict['mqtt_svrs'][0]
            self.mqtt_host_ = _mqtt_cfg_dict['mqtt_svr']
            self.mqtt_port_ = _mqtt_cfg_dict['mqtt_port']
            self.mqtt_cid_ = _mqtt_cfg_dict['mqtt_cid']
            self.mqtt_usr_ = _mqtt_cfg_dict['mqtt_usr']
            self.mqtt_pwd_ = _mqtt_cfg_dict['mqtt_pwd']
            self.node_name_ = _mqtt_cfg_dict['node_name']
            self._mqtt_pub_topic = _mqtt_cfg_dict['mqtt_tp']
            self.fsvr_url_ = _mqtt_cfg_dict['fsvr_url']
            # 更新service name
            # 下发的node name 与原来（系统安装的时候）配置不一样了
            if self.node_name_ != self.jaeger_['node_name']:
                # 缓存tracer便于后面使用
                self.tracer_ = self.reset_jaeger(self.jaeger_['agent_ip'], self.jaeger_['agent_port'], self.node_name_)
                self.jaeger_['node_name'] = self.node_name_     # FIXME 更新下发node name（是否需要写配置文件？）
                # 在主进程中操作配置文件
                _ret = self.call_rpc(bus.CB_SAVE_CFG, {'cmd': 'save_basecfg', 'source': self.name})
            self._mqtt_client_obj = mqtt_client.Client(self.mqtt_cid_)
            self._mqtt_client_obj.username_pw_set(self.mqtt_usr_, self.mqtt_pwd_)
            self._mqtt_client_obj.connect(self.mqtt_host_, self.mqtt_port_)

            # 进入主循环
            self._mqtt_client_obj.loop_start()
        except (socket.gaierror, TimeoutError, UnicodeError, ConnectionRefusedError) as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
            msg = f'Cannot connect to {self.mqtt_host_}:{self.mqtt_port_} with {self.mqtt_cid_}/{self.mqtt_pwd_}'
            raise V2VErr.V2VConfigurationIllegalError(msg)
        except (KeyError, ValueError, Exception) as err:
            self.log(f'[{__file__}]{err}', level=log.LOG_LVL_ERRO)
            raise V2VErr.V2VConfigurationIllegalError(err)

    def main_func(self, event=None, *args):
        try:
            vec = self.in_q_.get_nowait()
        except queue.Empty:
            time.sleep(0.01)
            return False

        payload = json.loads(str(vec.decode('utf-8')))
        data = {'payload': payload}
        # FIXME: why?
        # 从类方法或属性中查找'tracer_'
        if 'tracer_' in dir(self):    # 如果配置项有jaeger，将记录
            # inject和extract配合使用，先extract去取出数据包中的metadata的traceid的span上下文，
            # 然后再对上下文进行操作，并把它注入到下一个环节，因为mqtt这个进程是本模块的起点，因此只有inject。
            nodename = self.node_name_
            with self.tracer_.start_active_span(f'v2v_mqtt_{nodename}_send_msg') as scope:       # 带内数据插入trace id
                scope.span.set_tag('originalMsg', vec.decode('utf-8'))
                scope.span.set_tag('link.localHost', socket.gethostname())
                scope.span.set_tag('link.remoteHost', self.mqtt_host_)
                span = self.tracer_.active_span
                AdaptorTracingUtility.inject_span_ctx(self.tracer_, span, data)
        self.log(f"Publish data to MQTT. --> {data}", level=log.LOG_LVL_DBG)
        self._mqtt_client_obj.publish(self._mqtt_pub_topic, json.dumps(data), 1)

        return False

    def shutdown(self):
        self._mqtt_client_obj.loop_stop()
        self._mqtt_client_obj.disconnect()
        self._mqtt_client_obj = None
        pass
