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
import io

# import imutils
# from imutils.video import VideoStream
from matplotlib import pyplot as plt
from time import time, sleep
from utils import bus, comn, log
from core.procworker import ProcWorker


class RtspWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.vs_ = None
        self.fps_ = None
        self.args_ = None
        self.sample_rate_ = None
        for key, value in dicts.items():
            if key == 'rtsp_params':
                self.args_ = value
                self.sample_rate_ = value['sample_rate']

    def startup(self):
        """启动进程后，访问对应的rtsp流."""
        self.log(f'{self.name} started.')
        url = self.args_['rtsp_url']
        # self.vs_ = VideoStream(src=url, framerate=24).start()
        self.vs_ = cv2.VideoCapture(url)
        self.fps_ = self.vs_.get(cv2.cv2.CAP_PROP_FPS)
        # opened = self.vs_.isOpened()  # 暂时不检查是否正确打开流

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
            返回True，退出循环，返回False，继续循环。
        """
        try:
            # 1.按参数设置摄像头到预置点，因为预置点有多个，所以要轮流执行
            # 2.等待摄像头执行到预置点位
            # 3.假设fps比如是30帧，而采样率1Hz，则需要丢弃fps-sample_rate帧图像
            # 4.读取流并设置处理该图片的参数
            if self.vs_.isOpened():
                did = self.args_['device_id']
                cid = self.args_['channel_id']
                vps = self.args_['view_ports']
                # 采样的周期（秒），比如采样率1Hz，则睡1秒工作一次
                inteval = 1 / self.sample_rate_
                # 计算需要丢弃的帧数
                skip = self.fps_ - self.sample_rate_
                for vp in vps:
                    comn.run_to_viewpoints(did, cid, vp['preset_id'])
                    duration = vp['seconds']                # 配置文件要求停留多少秒
                    delta = 0
                    st = time()
                    while duration > delta:
                        # 开始丢帧：如前面计算，当skip>0，比如30fps - 1，则要丢弃29帧
                        if skip > 0:
                            cnt = 1
                            while True:
                                self.vs_.grab()
                                if cnt % skip == 0:
                                    ret, frame = self.vs_.retrieve()
                                    break
                                cnt += 1
                        sleep(inteval - time() % inteval)               # 动态调速，休眠采样间隔的时间

                        # grab, frame = self.vs_.read()
                        # frame = imutils.resize(frame, width=1200)     # size changed from 6MB to 2MB 不能缩小！
                        # cv2.imshow('NVR realtime', frame)
                        # key = cv2.waitKey(1) & 0xFF
                        # if key == ord('q'):
                        #     break

                        buf = io.BytesIO()
                        plt.imsave(buf, pic['frame'], format='jpg')
                        image_data = buf.getvalue()

                        pic = {'channel': vp, 'frame': frame}           # 把模型微服务参数等通过队列传给后续进程
                        self.out_q_.put(pic)
                        self.log(f'采用第{cnt}帧.--du:{duration}--, delta:{delta}.')
                        cnt = cnt + 1
                        delta = time() - st                             # 消耗的时间（秒）
            else:
                self.vs_.release()
                self.startup()
        except cv2.error as err:
            self.log(f'cv2.error:{self.args_["rtsp_url"]}', level=log.LOG_LVL_ERRO)
            self.vs_.release()
            self.startup()
        except TypeError as err:
            self.log('type error')
            self.log(err, level=log.LOG_LVL_ERRO)
        finally:
            self.log('finally.')
            return False

    def shutdown(self):
        # cv2.destroyAllWindows()
        self.vs_.release()
