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

encapsulate jaeger client.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0


import logging
from jaeger_client import Config
from opentracing import set_global_tracer, Format


class AdaptorTracingUtility:

    @staticmethod
    def init_tracer(service, agentip='127.0.0.1', agentport=6831):
        logging.getLogger('').handlers = []
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

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
                'logging': True,
                'reporter_bath_size': 1,
            },
            service_name=service,
        )
        set_global_tracer(config.initialize_tracer())

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
