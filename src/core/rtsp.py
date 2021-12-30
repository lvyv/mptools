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
from utils import bus, comn, log, V2VErr, GrabFrame
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
        self.task_ = {}

    def startup(self):
        task = None
        try:
            # 1.尝试获取配置数据，找主进程获取一个流水线任务
            self.log(f'{self.name} started......')
            cfg = self.call_rpc(bus.CB_GET_CFG, {'cmd': 'get_task', 'source': self.name, 'assigned': self.task_})
            # 2.访问对应的rtsp流
            # 如果此前已经分配过任务，但因为下发配置事件、配置不合法、网络断流等导致重新初始化。
            # 则有新分配任务，按新任务执行，没有新任务，按老任务执行。
            url = None
            if self.task_:
                url = self.task_['rtsp_url']
            if cfg['rtsp_urls']:
                task = cfg['rtsp_urls'][0]
                url = task['rtsp_url']      # 分配给自己的任务
                self.task_.update(task)     # 记录分配到的任务
            if url is None:
                # 这个错误是因为返回的配置信息中的任务没有，已经分配完了，或者原来分配任务，但新下发配置终止了原来任务（shutdown调用）
                raise V2VErr.V2VTaskNullRtspUrl(f'No more task left.')

            cvobj = GrabFrame.GrabFrame()
            opened = cvobj.open_stream(url, 10)
            if opened:
                w, h, self.fps_ = cvobj.get_stream_info()
                self.vs_ = cvobj
            else:
                raise V2VErr.V2VConfigurationIllegalError(f'Can not open the {url} stream.')

        except (cv2.error, IndexError, AttributeError) as err:
            self.log(f'[{__file__}]Rtsp start up task error:({task})', level=log.LOG_LVL_ERRO)
            raise V2VErr.V2VConfigurationIllegalError(err)

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
            # 1.按参数设置摄像头到预置点，因为预置点有多个，所以要轮流执行，每个预置点停留时间由seconds参数决定，所以这个函数花费时间会比较久
            # 2.等待摄像头执行到预置点位
            # 3.假设fps比如是30帧，而采样率1Hz，则需要丢弃fps-sample_rate帧图像
            # 4.读取流并设置处理该图片的参数

            # 是否有配置信息更新的广播消息，如果是通道信息，则需要判断是否是自己负责的通道self.args_['rtsp_url']
            # if event:
            #     self.log(event)     # 如果是属于自己的配置更新广播，更新初始化时的数据信息，包括：self.args_和self.fps_。
            #     for rtsp in event['rtsp_urls']:
            #         if rtsp['device_id'] == self.args_['device_id'] and rtsp['channel_id'] \
            #                 == self.args_['channel_id']:
            #             self.handle_cfg_update(rtsp)
            #             break
            # did = self.args_['device_id']
            # cid = self.args_['channel_id']
            # vps = self.args_['view_ports']
            # sar = self.args_['sample_rate']
            did = self.task_['device_id']
            cid = self.task_['channel_id']
            vps = self.task_['view_ports']
            sar = self.task_['sample_rate']
            # 采样的周期（秒），比如采样率1Hz，则睡1秒工作一次
            inteval = 1 / sar
            # 计算需要丢弃的帧数
            # skip = self.fps_ / sar
            for vp in vps:
                presetid = list(vp.keys())[0]   # 目前配置文件格式规定：每个vp对象只有1个presetX的主键，value是一个json对象
                # 让摄像头就位
                comn.run_to_viewpoints(did, cid, presetid)
                # 读取停留时间
                duration = vp[presetid][0]['seconds']   # 对某个具体的预置点vp，子分类aoi停留时间都是一样的，随便取一个即可。
                st, delta = time(), 0
                current_frame_pos = -1
                while duration > delta:
                    # 开始丢帧：如前面计算，当skip>0，比如fps/sample_rate=每都少帧一个抽样
                    # frame, current_frame_pos = None, None
                    # while skip >= 1 and self.vs_.grab():
                    #     current_frame_pos = self.vs_.get(cv2.CAP_PROP_POS_FRAMES)
                    #     if current_frame_pos % skip == 0:
                    #         ret, frame = self.vs_.retrieve()
                    #         self.log(f'framepos---{current_frame_pos}---')
                    #         break
                    frame = self.vs_.read_frame(0.1)
                    current_frame_pos = self.vs_.get_stream_frame_pos()
                    sleep(inteval - time() % inteval)               # 动态调速，休眠采样间隔的时间

                    # 为实现ai效率最大化，把图片中不同ai仪表识别任务分包，一个vp，不同类ai模型给不同的ai线程去处理
                    # 这样会导致同一图片重复放到工作队列中（只是aoi不同）。
                    aitasks = vp[presetid]
                    for task in aitasks:
                        if task['ai_service'] != '':
                            # 把图像数据和任务信息通过队列传给后续进程，fid和fps可以用来计算流开始以来的时间
                            if frame is not None:
                                pic = {'task': task, 'fid': current_frame_pos, 'fps': self.fps_, 'frame': frame}
                                self.out_q_.put(pic)

                    # 计算是否到设定的时间了
                    delta = time() - st                             # 消耗的时间（秒）
                self.log(f'preset {presetid} spend time: {delta} and current frame pos: {current_frame_pos}')
                # 如果读流发现错误，则需要重新连接流，不再往下发错误数据
                # if current_frame_pos is None:
                #     raise cv2.error
        except (cv2.error, AttributeError, UnboundLocalError) as err:
            self.log(f'1.[{__file__}]cv2.error:({err}){self.task_}', level=log.LOG_LVL_ERRO)
            # self.vs_.release()
            # self.startup()
        # except UnboundLocalError as err:
        #     self.log(f'{err}', level=log.LOG_LVL_ERRO)
        except TypeError as err:
            self.log('type error')
            self.log(f'2.[{__file__}]{err}', level=log.LOG_LVL_ERRO)
        except Exception as err:
            self.log(f'3.[{__file__}]Unkown error.{err}', level=log.LOG_LVL_ERRO)
        # else:
        #     self.log(f'normal execution.', level=log.LOG_LVL_ERRO)
        finally:
            self.log('finally.')
            return False

    def shutdown(self):
        # cv2.destroyAllWindows()
        self.vs_.stop_stream()
        self.task_ = {}     # 很重要，清空任务列表
        self.fps_ = None
        self.vs_ = None
