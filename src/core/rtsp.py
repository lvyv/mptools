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
rtsp module
=========================

Pull av stream from nvr and decode pictures from the streams.
"""

# Author: Awen <26896225@qq.com>
# License: Apache Licence 2.0

import cv2
import imutils
from time import time, sleep
from utils import bus, comn
from core.procworker import ProcWorker
from imutils.video import VideoStream


class RtspWorker(ProcWorker, bus.IEventBusMixin):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_RTSP, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_RTSP
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.vs_ = None
        self.args_ = None
        self.sample_rate_ = None
        for key, value in dicts.items():
            if key == 'rtsp_url':
                self.args_ = value
            if key == 'sample_rate':
                self.sample_rate_ = value

    def startup(self):
        """启动进程后，访问对应的rtsp流."""
        self.log(f'{self.name} started.')
        url = self.args_['rtsp_url']
        self.vs_ = VideoStream(src=url, framerate=24).start()
        # self.log(f'Got stream!')

    def main_func(self, event=None, *args):
        """
        本函数实现按配置文件调度摄像头，取rtsp流解析，并调用ai的业务逻辑。
        重载基类主循环函数调用。

        Parameters
        ----------
        event : 主事件循环的外部事件回调。
        *args: tuple, None
            扩展参数。
        Returns
        -------
            无返回值。
        """
        if 'END' == event:
            self.break_out_ = True
        # 1.按参数设置摄像头到预置点，因为预置点有多个，所以要轮流执行
        # 2.等待摄像头执行到预置点位
        # 3.读取流并设置处理该图片的参数
        did = self.args_['device_id']
        cid = self.args_['channel_id']
        vps = self.args_['view_ports']
        inteval = 1 / self.sample_rate_
        for vp in vps:
            comn.run_to_viewpoints(did, cid, vp['preset_id'])
            duration = vp['seconds']                # 配置文件要求停留多少秒
            st = time()
            delta = 0
            cnt = 0
            while duration > delta:
                sleep(inteval - time() % inteval)               # 休眠采样间隔的时间
                frame = self.vs_.read()
                if frame is not None:
                    frame = imutils.resize(frame, width=1200)   # size changed from 6MB to 2MB
                    # cv2.imshow('NVR realtime', frame)
                    pic = {'channel': vp, 'frame': frame}       # 把模型微服务参数等通过队列传给后续进程
                    self.out_q_.put(pic)
                    self.log(f'采用第{cnt}帧.')
                    cnt = cnt + 1
                delta = time() - st                             # 消耗的时间（秒）

    def shutdown(self):
        cv2.destroyAllWindows()
        self.vs_.stop()
