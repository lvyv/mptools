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
import queue
from time import time, sleep

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
        # 代表任务的配置文件，里面包含一个通道的信息
        self._process_task_dict = {}
        # 视频调度管理软件的地址
        self._spdd_url = None
        # 旋转云台后的等待时间，默认30秒
        self._ptz_delay = 30

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
                self._proc_broadcast_msg(evt)
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

    def _proc_broadcast_msg(self, evt) -> bool:
        _ret = True
        # EBUS_SPECIAL_MSG_STOP_RESUME_PIPE = {'code': 3, 'desc': 'METRICS'}
        # 使用唯一的消息码进行判断
        _evt_code = evt.get('code', -1)
        # 通道的启停
        if _evt_code == bus.EBUS_SPECIAL_MSG_STOP_RESUME_PIPE['code']:
            cmd = evt.get('cmd', None)
            if cmd in ['pause', 'resume']:
                did = evt.get('deviceid', None)
                cid = evt.get('channelid', None)
                if self._check_did_cid_pertain_process(did, cid) is True:
                    if cmd == 'pause':
                        _new_state = ProcessState.PAUSE
                    else:
                        _new_state = ProcessState.RUN
                    self.log(f"[RTSP] Set Process State: {self.state} --> {_new_state}")
                    self.state = _new_state
                    raise V2VErr.V2VPauseRtspProcess("[RTSP] Pause RTSP Process.")
        elif _evt_code == bus.EBUS_SPECIAL_MSG_CHANNEL_CFG['code']:
            did = evt.get('deviceid', None)
            cid = evt.get('channelid', None)
            if self._check_did_cid_pertain_process(did, cid) is True:
                self.log("[RTSP] Single Channel's config changed. Restart Process.")
                raise V2VErr.V2VConfigurationChangedError(f'{did}-{cid}')
        elif _evt_code == bus.EBUS_SPECIAL_MSG_CFG['code']:
            self.log("[RTSP] EBUS_SPECIAL_MSG_CFG. Restart Process.")
            raise V2VErr.V2VConfigurationChangedError(f'EBUS_SPECIAL_MSG_CFG')
        elif _evt_code == bus.EBUS_SPECIAL_MSG_STOP['code']:
            self.log("[RTSP] Recv EBUS_SPECIAL_MSG_STOP event.")
            raise V2VErr.V2VTaskExitProcess('V2VTaskExitProcess.')
        return _ret

    def startup(self, evt=None):
        # rtsp流地址
        _rtsp_url = None
        # 通道的配置信息
        _channel_cfg_dict = None

        if evt is not None:
            self._proc_broadcast_msg(evt)
        if self.state == ProcessState.PAUSE:
            self._sleep_wrapper(0.1)

        # 1.尝试获取配置数据，找主进程获取一个流水线任务，复用了获取配置文件的命令
        self.log(f'[RTSP STARTUP] Enter startup.')
        _process_task_dict_from_main = self.call_rpc(bus.CB_GET_CFG,
                                                     {'cmd': 'get_task',
                                                      'source': self.name,
                                                      'assigned': self._process_task_dict})
        self._spdd_url = _process_task_dict_from_main.get('media_service', None)
        self._ptz_delay = _process_task_dict_from_main.get('ipc_ptz_delay', 10)

        # 2.访问对应的rtsp流
        # 首先从缓存的dict中取RTSP地址
        if self._process_task_dict and len(self._process_task_dict) > 0:
            _rtsp_url = self._process_task_dict['rtsp_url']
        # 如果最新分配的任务中有RTSP，则以此为准
        _rtsp_list = _process_task_dict_from_main.get('rtsp_urls', None)
        if _rtsp_list and len(_rtsp_list) > 0:
            _channel_cfg_dict = _rtsp_list[0]
            _rtsp_url = _channel_cfg_dict.get('rtsp_url', None)  # 分配给自己的任务
        if _rtsp_url is None:
            # 这个错误是因为返回的配置信息中的任务没有，已经分配完了，或者原来分配任务，但新下发配置终止了原来任务（shutdown调用）
            self.log(f"[RTSP STARTUP] 1.该进程没有分配到RTSP流地址，非阻塞休眠10s", level=log.LOG_LVL_WARN)
            self._sleep_wrapper(10)
            raise V2VErr.V2VTaskNullRtspUrl(f'No more task left.')
        else:
            self._process_task_dict.update(_channel_cfg_dict)  # 记录分配到的任务
            self.log(f"[RTSP STARTUP] 1.进程分配到RTSP流地址: {_channel_cfg_dict}", level=log.LOG_LVL_WARN)

        # 实例化取视频帧类
        cvobj = GrabFrame.GrabFrame()
        try:
            # FIXME: 因为阻塞，影响广播消息的接收和响应
            opened = cvobj.open_stream(_rtsp_url, GrabFrame.GrabFrame.OPEN_RTSP_TIMEOFF)
            if opened:
                w, h, self._stream_fps = cvobj.get_stream_info()
                self._stream_obj = cvobj
                self.log(f"[RTSP STARTUP] 2.获取RTSP流成功. w:{w}, h:{h}, fps:{self._stream_fps}, url:{_rtsp_url}",
                         level=log.LOG_LVL_DBG)
            else:
                self.log(f'[RTSP STARTUP] 2.获取RTSP流失败. url:{_rtsp_url}', level=log.LOG_LVL_ERRO)
                cvobj.stop_stream()
                raise V2VErr.V2VTaskConnectError(f'Open RTSP stream failed. url:{_rtsp_url}')
        except (cv2.error, IndexError, AttributeError) as err:
            self.log(f'[RTSP STARTUP] 2.获取RTSP流失败. url:{_rtsp_url}', level=log.LOG_LVL_ERRO)
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
        _ret = False
        try:
            # 1.按参数设置摄像头到预置点，因为预置点有多个，所以要轮流执行，每个预置点停留时间由seconds参数决定，所以这个函数花费时间会比较久
            # 2.等待摄像头执行到预置点位
            # 3.假设fps比如是30帧，而采样率1Hz，则需要丢弃fps-sample_rate帧图像
            # 4.读取流并设置处理该图片的参数
            if event:
                self._proc_broadcast_msg(event)  # 主要处理暂停事件，当rest发过来请求暂停流水线
            if self.state == ProcessState.PAUSE:
                self._sleep_wrapper(0.1)
                return _ret

            _device_id = self._process_task_dict['device_id']
            _channel_id = self._process_task_dict['channel_id']
            _preset_list = self._process_task_dict['view_ports']
            _sample_rate = self._process_task_dict.get('sample_rate', 1)
            # 此处增加对数字的校验
            if isinstance(_sample_rate, str):
                self.log(f"[RTSP RUN] 下发的采样率不是数字类型，使用默认值. --> {_sample_rate}", level=log.LOG_LVL_WARN)
                _sample_rate = 1

            # 采样的周期（秒），比如采样率1Hz，则睡1秒工作一次
            interval = 1 / _sample_rate
            # 计算需要丢弃的帧数
            # skip = self.fps_ / sar
            # 遍历预置位 ["preset1": [], "preset2": []]
            for _preset in _preset_list:
                _preset_id = _api_preset_id = list(_preset.keys())[0]  # 目前配置文件格式规定：每个vp对象只有1个presetX的主键，value是一个json对象
                # 如果前端发送的预置位ID包含preset值，则删除preset
                if 'preset' in _api_preset_id:
                    _api_preset_id = _api_preset_id.replace("preset", "")
                _api_ret = spdd.run_to_viewpoints(_device_id, _channel_id, _api_preset_id, self._spdd_url,
                                                  self._ptz_delay)
                self.log(f"[RTSP RUN] 1.旋转云台到预置位: {_preset_id}. --> {_api_ret}", level=log.LOG_LVL_INFO)

                # 云台的物理旋转动作较慢，延时等待，时间由配置文件指定
                self._sleep_wrapper(self._ptz_delay)

                # 读取停留时间，云台旋转到位后，在此画面停留时间
                _preset_stay_time = _preset[_preset_id][0]['seconds']
                st, _screenshot_use_time = time(), 0
                current_frame_pos = -1
                # 从预置位点截图逻辑，使用循环，一个预置位可能取多张图片
                while _preset_stay_time > _screenshot_use_time:
                    _video_frame_data = self._stream_obj.read_frame(0.5)
                    if _video_frame_data is not None:
                        # 请求用时间戳，便于后续Ai识别后还能够知道是哪一个时间点的视频帧
                        requestid = int(time() * 1000)
                        current_frame_pos = self._stream_obj.get_stream_frame_pos()

                        # 为实现ai效率最大化，把图片中不同ai仪表识别任务分包，一个vp，不同类ai标注类型给不同的ai进程去处理
                        # 这样会导致同一图片重复放到工作队列中（只是aoi不同）
                        aitasks = _preset[_preset_id]
                        # 遍历每一个presetX下的对象
                        for _aoi_dict in aitasks:
                            if _aoi_dict['ai_service'] == '':
                                continue
                            # 把图像数据和任务信息通过队列传给后续进程，fid和fps可以用来计算流开始以来的时间
                            _recognition_obj = {'requestid': requestid,
                                                'task': _aoi_dict, 'fid': current_frame_pos,
                                                'fps': self._stream_fps,
                                                'frame': _video_frame_data}
                            self.log(
                                f'[RTSP RUN] The size of picture queue between rtsp & ai is: {self.out_q_.qsize()}.',
                                level=log.LOG_LVL_DBG)
                            self.out_q_.put_nowait(_recognition_obj)
                    else:
                        self.log(f"[RTSP RUN] 取预置位:{_preset_id} 的视频帧失败. -->", level=log.LOG_LVL_ERRO)
                    # self.log(f"云台截图休眠时间: {inteval - time() % inteval}")
                    self._sleep_wrapper(interval - time() % interval)
                    # 计算是否到设定的时间了
                    _screenshot_use_time = time() - st  # 消耗的时间（秒）
                    _video_frame_data = None
                self.log(
                    f'[RTSP RUN] preset:"{_preset_id}", use time:{_screenshot_use_time}, frame pos:{current_frame_pos}')
            return _ret
        except (cv2.error, AttributeError, UnboundLocalError) as err:
            self.log(f'[RTSP RUN] cv2.error:({err}){self._process_task_dict}', level=log.LOG_LVL_ERRO)
            return _ret
        except TypeError as err:
            self.log(f'[RTSP RUN] TypeError:{err}', level=log.LOG_LVL_ERRO)
            return _ret
        except V2VErr.V2VPauseRtspProcess as err:
            self.log(f"[RTSP RUN] Pause/Resume RTSP process.", level=log.LOG_LVL_WARN)
            return _ret
        except queue.Full:
            self.log("[RTSP RUN] Image queue is [FULL], clear it!", level=log.LOG_LVL_ERRO)
            self.out_q_.queue.clear()
            return _ret

    def shutdown(self):
        if self._stream_obj is not None:
            self._stream_obj.stop_stream()
            self._stream_obj = None
        self._stream_fps = None
        self._process_task_dict.clear()
        self._process_task_dict = {}  # 很重要，清空任务列表
