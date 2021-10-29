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
# import io

# import imutils
# from imutils.video import VideoStream
# from matplotlib import pyplot as plt
from time import time, sleep
from utils import bus, comn, log
from core.procworker import ProcWorker


class RtspWorker(ProcWorker):

    def handle_cfg_update(self, channel):
        """
        本函数为配置发生变化，热更新配置。
        热更新的含义：不需要重启整个程序。
        1）如果没有改deviceid，也就是没有改rtsp_url，则改变的只是aoi，sample_rate，不需要重新建立nvr流。
        2）如果rtsp_url都变了，则要重新建立nvr流，并且刷新fps。
        :param channel:
        :return:
        """
        # self.log(cfg)
        self.args_ = channel
        pass

    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self.vs_ = None
        self.fps_ = None
        self.args_ = None
        # self.sample_rate_ = None
        for key, value in dicts.items():
            if key == 'rtsp_params':
                self.args_ = value
                # self.sample_rate_ = value['sample_rate']

    def startup(self):
        """启动进程后，访问对应的rtsp流."""
        self.log(f'{self.name} started.')
        url = self.args_['rtsp_url']
        # self.vs_ = VideoStream(src=url, framerate=24).start()
        self.log(f'openning rtsp stream: {url}')
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

            # 是否有配置信息更新的广播消息，如果是通道信息，则需要判断是否是自己负责的通道self.args_['rtsp_url']
            if event:
                self.log(event)     # 如果是属于自己的配置更新广播，更新初始化时的数据信息，包括：self.args_和self.fps_。
                for rtsp in event['rtsp_urls']:
                    if rtsp['device_id'] == self.args_['device_id'] and rtsp['channel_id'] == self.args_['channel_id']:
                        self.handle_cfg_update(rtsp)
                        break
            did = self.args_['device_id']
            cid = self.args_['channel_id']
            vps = self.args_['view_ports']
            sar = self.args_['sample_rate']
            # 采样的周期（秒），比如采样率1Hz，则睡1秒工作一次
            inteval = 1 / sar
            # 计算需要丢弃的帧数
            skip = self.fps_ / sar
            for vp in vps:
                presetid = list(vp.keys())[0]   # 目前配置文件格式规定：每个vp对象只有1个presetX的主键，value是一个json对象
                # 让摄像头就位
                comn.run_to_viewpoints(did, cid, presetid)
                # 读取停留时间
                duration = vp[presetid][0]['seconds']   # 对某个具体的预置点vp，子分类aoi停留时间都是一样的，随便取一个即可。
                st, delta = time(), 0

                while duration > delta:
                    # 开始丢帧：如前面计算，当skip>0，比如fps/sample_rate=每都少帧一个抽样
                    frame, current_frame_pos = None, None
                    while skip >= 1 and self.vs_.grab():
                        current_frame_pos = self.vs_.get(cv2.cv2.CAP_PROP_POS_FRAMES)
                        if current_frame_pos % skip == 0:
                            ret, frame = self.vs_.retrieve()
                            self.log(f'framepos---{current_frame_pos}---')
                            break
                    sleep(inteval - time() % inteval)               # 动态调速，休眠采样间隔的时间

                    # 为实现ai效率最大化，把图片中不同ai仪表识别任务分包，一个vp，不同类ai模型给不同的ai线程去处理
                    # 这样会导致同一图片重复放到工作队列中（只是aoi不同）。
                    tasks = vp[presetid]
                    for task in tasks:
                        if task['ai_service'] != '':
                            # 把图像数据和任务信息通过队列传给后续进程，fid和fps可以用来计算流开始以来的时间
                            if frame is not None:
                                pic = {'task': task, 'fid': current_frame_pos, 'fps': self.fps_, 'frame': frame}
                                self.out_q_.put(pic)

                    # 计算是否到设定的时间了
                    delta = time() - st                             # 消耗的时间（秒）
                self.log(f'preset {presetid} spend time: {delta} and current frame pos: {current_frame_pos}')
                # 如果读流发现错误，则需要重新连接流，不再往下发错误数据
                if current_frame_pos is None:
                    raise cv2.error
        except (cv2.error, AttributeError, UnboundLocalError) as err:
            self.log(f'cv2.error:({err}){self.args_["rtsp_url"]}', level=log.LOG_LVL_ERRO)
            self.vs_.release()
            self.startup()
        # except UnboundLocalError as err:
        #     self.log(f'{err}', level=log.LOG_LVL_ERRO)
        except TypeError as err:
            self.log('type error')
            self.log(err, level=log.LOG_LVL_ERRO)
        except Exception as err:
            self.log(f'Unkown error.{err}', level=log.LOG_LVL_ERRO)
        # else:
        #     self.log(f'normal execution.', level=log.LOG_LVL_ERRO)
        finally:
            self.log('finally.')
            return False

    def shutdown(self):
        # cv2.destroyAllWindows()
        self.vs_.release()
