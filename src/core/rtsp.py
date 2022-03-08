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
import queue
from time import time, sleep, time_ns

import cv2

from core.pools import ProcessState
from core.procworker import ProcWorker
from third_api import spdd
from utils import bus, log, V2VErr, GrabFrame


class RtspWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, channel_cfg=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, channel_cfg, **kwargs)
        self.in_q_ = in_q
        self.out_q_ = out_q
        self._stream_obj = None
        self._stream_fps = None
        self.args_ = None
        # self.sample_rate_ = None
        for key, value in channel_cfg.items():
            if key == 'rtsp_params':
                self.args_ = value
                break
        # 代表任务的配置文件，里面包含一个通道的信息
        self._process_task_dict = {}
        # 视频调度管理软件的地址
        self._spdd_url = None
        # 旋转云台后的等待时间，默认30秒
        self._ptz_delay = 30

    def handle_cfg_update(self, channel):
        """
        本函数为配置发生变化，热更新配置。
        热更新的含义：不需要重启整个程序。
        1）如果没有改deviceid，也就是没有改rtsp_url，则改变的只是aoi，sample_rate，不需要重新建立nvr流。
        2）如果rtsp_url都变了，则要重新建立nvr流，并且刷新fps。
        :param channel:
        :return:
        """
        self.args_ = channel
        pass

    def _sleep_wrapper(self, timeout) -> int:
        """
        针对time.sleep()函数的封装，解决sleep时无法接收广播事件的问题

        param:
        timeout: 休眠时间，单位秒

        return:
        返回true表示正常，false表示sleep过程中有事件产生
        """
        _ret = -1
        _start_time, delta = time(), 0
        while timeout >= delta:
            evt = self.subscribe()
            if evt:
                _evt_code = evt['code']
                if _evt_code == bus.EBUS_SPECIAL_MSG_STOP['code']:
                    _ret = _evt_code
                    break
                elif _evt_code == bus.EBUS_SPECIAL_MSG_STOP_RESUME_PIPE['code']:
                    self.handle_event(evt)
                    _ret = _evt_code
                    break
                else:
                    break
            # 使用更小的sleep粒度
            sleep(0.05)
            delta = time() - _start_time

        return _ret

    def _check_did_cid_pertain_process(self, did, cid) -> bool:
        """
        检测输入的did, cid是否属于该进程管理

        :return true属于该进程，false不属于该进程
        """
        _ret = False
        # 获取该进程管理的通道
        _p_did = self._process_task_dict.get('device_id', None)
        _p_cid = self._process_task_dict.get('channel_id', None)
        if _p_cid and _p_did and _p_cid == cid and _p_did == did:
            _ret = True
        return _ret

    def handle_event(self, evt) -> bool:
        _ret = True
        # EBUS_SPECIAL_MSG_STOP_RESUME_PIPE = {'code': 3, 'desc': 'METRICS'}
        # 使用唯一的消息码进行判断
        _evt_code = evt['code']
        # 通道的启停
        if _evt_code == bus.EBUS_SPECIAL_MSG_STOP_RESUME_PIPE['code']:
            cmd = evt['cmd']
            if cmd in ['pause', 'resume']:
                did = evt['deviceid']
                cid = evt['channelid']
                if self._check_did_cid_pertain_process(did, cid) is True:
                    if cmd == 'pause':
                        _new_state = ProcessState.PAUSE
                    else:
                        _new_state = ProcessState.RUN
                    self.log(f"[RTSP] Set Process State: {self.state} --> {_new_state}")
                    self.state = _new_state
        elif _evt_code == bus.EBUS_SPECIAL_MSG_CHANNEL_CFG['code']:
            did = evt['device_id']
            cid = evt['channel_id']
            if self._check_did_cid_pertain_process(did, cid) is True:
                self.log("[CONFIG] Single Channel's config changed. Restart Process.")
                raise V2VErr.V2VConfigurationChangedError(f'{did}-{cid}')
        return _ret

    def startup(self, evt=None):
        # rtsp流地址
        _rtsp_url = None
        # 通道的配置信息
        _channel_cfg_dict = None
        try:
            if evt is not None:
                self.handle_event(evt)
            if self.state == ProcessState.PAUSE:
                self._sleep_wrapper(0.1)

            # 1.尝试获取配置数据，找主进程获取一个流水线任务，复用了获取配置文件的命令
            self.log(f'Enter startup.')
            _process_task_dict_from_main = self.call_rpc(bus.CB_GET_CFG,
                                                         {'cmd': 'get_task', 'source': self.name,
                                                          'assigned': self._process_task_dict})
            self._spdd_url = _process_task_dict_from_main['media_service']
            self._ptz_delay = _process_task_dict_from_main['ipc_ptz_delay']
            self.log(f'Get spdd url: {self._spdd_url} ptz_delay:{self._ptz_delay} value from main process.')
            # 2.访问对应的rtsp流
            # 如果此前已经分配过任务，但因为下发配置事件、配置不合法、网络断流等导致重新初始化。
            # 则有新分配任务，按新任务执行，没有新任务，按老任务执行。
            if self._process_task_dict:
                _rtsp_url = self._process_task_dict['rtsp_url']
            if _process_task_dict_from_main['rtsp_urls']:
                _channel_cfg_dict = _process_task_dict_from_main['rtsp_urls'][0]
                _rtsp_url = _channel_cfg_dict['rtsp_url']  # 分配给自己的任务
                self._process_task_dict.update(_channel_cfg_dict)  # 记录分配到的任务
            if _rtsp_url is None:
                # 这个错误是因为返回的配置信息中的任务没有，已经分配完了，或者原来分配任务，但新下发配置终止了原来任务（shutdown调用）
                raise V2VErr.V2VTaskNullRtspUrl(f'No more task left.')
            # 实例化取视频帧类
            cvobj = GrabFrame.GrabFrame()
            # 阻塞打开RTSP流
            # FIXME: 因为阻塞，影响广播消息的接收和响应
            opened = cvobj.open_stream(_rtsp_url, GrabFrame.GrabFrame.OPEN_RTSP_TIMEOFF)
            if opened:
                w, h, self._stream_fps = cvobj.get_stream_info()
                self._stream_obj = cvobj
                self.log(f"Open RTSP stream success. w:{w}, h:{h}, fps:{self._stream_fps}, url:{_rtsp_url}")
            else:
                self.log(f'Open RTSP stream failed. url:{_rtsp_url}', level=log.LOG_LVL_ERRO)
                cvobj.stop_stream()
                raise V2VErr.V2VConfigurationIllegalError(f'Open RTSP stream failed. url:{_rtsp_url}')
        except (cv2.error, IndexError, AttributeError) as err:
            self.log(f'[{__file__}]Rtsp startup task error:({_channel_cfg_dict})', level=log.LOG_LVL_ERRO)
            raise V2VErr.V2VConfigurationIllegalError(err)
        else:
            # startup阶段顺利完成
            pass

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
        _ret = False
        try:
            # 1.按参数设置摄像头到预置点，因为预置点有多个，所以要轮流执行，每个预置点停留时间由seconds参数决定，所以这个函数花费时间会比较久
            # 2.等待摄像头执行到预置点位
            # 3.假设fps比如是30帧，而采样率1Hz，则需要丢弃fps-sample_rate帧图像
            # 4.读取流并设置处理该图片的参数
            if event:
                self.handle_event(event)  # 主要处理暂停事件，当rest发过来请求暂停流水线
            if self.state == ProcessState.PAUSE:
                self._sleep_wrapper(0.1)
                return

            did = self._process_task_dict['device_id']
            cid = self._process_task_dict['channel_id']
            vps = self._process_task_dict['view_ports']
            sar = self._process_task_dict['sample_rate']
            # 采样的周期（秒），比如采样率1Hz，则睡1秒工作一次
            inteval = 1 / sar
            # 计算需要丢弃的帧数
            # skip = self.fps_ / sar
            # 遍历预置位 ["preset1": [], "preset2": []]
            for vp in vps:
                # 取"preset1"值
                presetid = list(vp.keys())[0]  # 目前配置文件格式规定：每个vp对象只有1个presetX的主键，value是一个json对象
                # 让摄像头就位，阻塞操作，函数内部会休眠
                self.log(f"Call PTZ preset. --> {presetid}")
                spdd.run_to_viewpoints(did, cid, presetid, self._spdd_url, self._ptz_delay)
                _sleep_ret = self._sleep_wrapper(self._ptz_delay)
                if _sleep_ret == bus.EBUS_SPECIAL_MSG_STOP['code']:
                    self.log("Got manual exit event, so break ptz control.")
                    # 类似于break
                    _ret = True
                    # 此处有坑，请搜索try..exception..finally中return
                    return _ret
                elif _sleep_ret == bus.EBUS_SPECIAL_MSG_STOP_RESUME_PIPE['code']:
                    # 类似于continue
                    return _ret
                # 读取停留时间，云台旋转到位后，在此画面停留时间
                duration = vp[presetid][0]['seconds']  # 对某个具体的预置点vp，子分类aoi停留时间都是一样的，随便取一个即可。
                st, delta = time(), 0
                current_frame_pos = -1
                while duration > delta:
                    _video_frame_data = self._stream_obj.read_frame(0.1)
                    # 请求用时间戳，便于后续Ai识别后还能够知道是哪一个时间点的视频帧
                    requestid = int(time() * 1000)
                    # requestid = time_ns()
                    current_frame_pos = self._stream_obj.get_stream_frame_pos()

                    # 为实现ai效率最大化，把图片中不同ai仪表识别任务分包，一个vp，不同类ai标注类型给不同的ai进程去处理
                    # 这样会导致同一图片重复放到工作队列中（只是aoi不同）。
                    aitasks = vp[presetid]
                    # 遍历每一个presetX下的对象
                    for _aoi_dict in aitasks:
                        if _aoi_dict['ai_service'] != '':
                            # 把图像数据和任务信息通过队列传给后续进程，fid和fps可以用来计算流开始以来的时间
                            if _video_frame_data is not None:
                                _recognition_obj = {'requestid': requestid,
                                                    'task': _aoi_dict, 'fid': current_frame_pos,
                                                    'fps': self._stream_fps,
                                                    'frame': _video_frame_data}
                                self.log(f'The size of picture queue between rtsp & ai is: {self.out_q_.qsize()}.')
                                self.out_q_.put_nowait(_recognition_obj)
                    # FIXME: why?
                    self.log(f"云台截图休眠时间: {inteval - time() % inteval}")
                    _sleep_ret = self._sleep_wrapper(inteval - time() % inteval)
                    if _sleep_ret == bus.EBUS_SPECIAL_MSG_STOP['code']:
                        self.log("Got manual exit event, so break capture flow.")
                        _ret = True
                        # 此处有坑，请搜索try..exception..finally中return
                        return _ret
                    elif _sleep_ret == bus.EBUS_SPECIAL_MSG_STOP_RESUME_PIPE['code']:
                        # 跳过本次循环
                        return _ret
                    # 计算是否到设定的时间了
                    delta = time() - st  # 消耗的时间（秒）
                self.log(f'preset: "{presetid}" spend time: {delta} and current frame pos: {current_frame_pos}')
        except (cv2.error, AttributeError, UnboundLocalError) as err:
            self.log(f'1.cv2.error:({err}){self._process_task_dict}', level=log.LOG_LVL_ERRO)
        except TypeError as err:
            self.log(f'2.TypeError:{err}', level=log.LOG_LVL_ERRO)
        except queue.Full:
            self.log("[FULL] Image queue is full.", level=log.LOG_LVL_ERRO)
            self.out_q_.clear()
        except Exception as err:
            self.log(f'3.Unkown error:{err}', level=log.LOG_LVL_ERRO)
        finally:
            return _ret

    def shutdown(self):
        if self._stream_obj is not None:
            self._stream_obj.stop_stream()
            self._stream_obj = None
        self._stream_fps = None
        self._process_task_dict.clear()
        self._process_task_dict = {}  # 很重要，清空任务列表
