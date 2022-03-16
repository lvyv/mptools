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
jaeger open tracing module
=========================

encapsulate jaeger client, prometheus fastapi client.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0


import time
from typing import Callable

import psutil
from jaeger_client import Config
from opentracing import Format
from prometheus_client import Gauge, Counter
from prometheus_fastapi_instrumentator.metrics import Info


class AdaptorTracingUtility:

    @staticmethod
    def init_tracer(service, agentip='127.0.0.1', agentport=6831):
        config = Config(
            config={
                'sampler': {
                    'type': 'const',
                    'param': 1,
                },
                'local_agent': {
                    "reporting_host": agentip,
                    "reporting_port": agentport
                },
                'logging': False,
                'reporter_bath_size': 1,
            },
            service_name=service,
        )
        # 测试，原库不支持重新调用，但应用层又需要重新改node name和service name。
        # tracer = config.initialize_tracer()
        # set_global_tracer(tracer)
        tracer = config.new_tracer()
        return tracer

    @staticmethod
    def extract_span_ctx(tracer, msg):
        span_ctx = None
        if isinstance(msg, dict):
            metadata = msg['metadata']
            span_ctx = tracer.extract(Format.TEXT_MAP, metadata)
        return span_ctx

    @staticmethod
    def inject_span_ctx(tracer, span, msg):
        msg.update({"metadata": {}})
        tracer.inject(span, Format.TEXT_MAP, msg["metadata"])


def up_time() -> Callable[[Info], None]:
    metric = Counter(
        "up_time",
        "开机持续运行时间.",
        labelnames=("v2v",)
    )
    sts_ = int(time.time())     # 秒为单位

    def instrumentation(info: Info) -> None:
        pname = info.request.query_params.get('v2v')
        # if pname:
        nonlocal sts_
        current = int(time.time())
        delta = current - sts_
        metric.labels('zh').inc(delta)
        sts_ = current

    return instrumentation


def cpu_rate() -> Callable[[Info], None]:
    metric = Gauge(
        "cpu_rate",
        "cpu占用率.",
        labelnames=("v2v",)
    )

    def instrumentation(info: Info) -> None:
        cpu = psutil.cpu_percent()
        metric.labels('zh').set(cpu)

    return instrumentation


def mem_rate() -> Callable[[Info], None]:
    metric = Gauge(
        "mem_rate",
        "内存占用率.",
        labelnames=("v2v",)
    )

    def instrumentation(info: Info) -> None:
        mem = psutil.virtual_memory().percent
        metric.labels('zh').set(mem)

    return instrumentation
