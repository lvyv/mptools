#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : task.py
# @Time    : 2022/3/6 11:45
# @Author  : XiongFei
# Description：该类用于管理V2V的任务，包含：分配，启用，暂停和查询
import copy
import functools
import os
from enum import Enum, unique

from core.pools import ProcessManage
from utils import log
from utils.comn import get_pid_from_process_name
from utils.config import ConfigSet


@unique
class TaskType(Enum):
    # 未处理任务
    IDLE = 0
    # 处理RTSP流任务
    RTSP = 1
    # 处理AI识别任务
    AI = 2
    # 处理MQTT数据任务
    MQTT = 3
    # 未知任务
    UNKNOWN = 4


class TaskInfo:
    def __init__(self, url):
        self.rtsp_url = url
        # 进程名：NAME(PID)
        self._name = None
        # 处理该任务的子进程号
        # type: int
        self._task_pid = 0
        # 该任务类型
        # type:TaskType
        self._task_type = TaskType.IDLE
        # 最后一次更新时间
        self._time = 0
        # 任务处理的通道编号
        self._did = None
        self._cid = None

    def dump(self) -> dict:
        return {'url': self.rtsp_url,
                'type': self._task_type,
                'tpid': self._task_pid,
                'deviceid': self._did,
                'channelid': self._cid
                }

    # 设备编号
    @property
    def did(self):
        return self._did

    @did.setter
    def did(self, value):
        self._did = value

    # 通道编号
    @property
    def cid(self):
        return self._cid

    @cid.setter
    def cid(self, value):
        self._cid = value

    @property
    def time(self):
        return self._name

    @property
    def tpid(self):
        return self._task_pid

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        # 取任务类型
        if 'RTSP' in value:
            self._task_type = TaskType.RTSP
        elif 'AI' in value:
            self._task_type = TaskType.AI
        elif 'MQTT' in value:
            self._task_type = TaskType.MQTT
        else:
            self._task_type = TaskType.UNKNOWN
        # 解析出进程号
        self._task_pid = get_pid_from_process_name(value)


class TaskManage:
    def __init__(self):
        self.log = functools.partial(log.logger, f'TASK-MANAGE-{os.getpid()}')
        # {url: _TaskInfo}
        self._task_dict = dict()
        # 管理进程状态信息，进程和任务通过PID进行关联，进程的状态信息由子进程主动更新
        # type: ProcessManage
        self._p_manage = ProcessManage()

    def clear_task(self, url=None):
        if url is None:
            # 清空所有任务
            self._task_dict.clear()
            self._task_dict = dict()
            self._p_manage.clear()
        else:
            # 清空指定的任务
            self._task_dict.pop(url)

    def dump_rtsp_list(self) -> list:
        """
        为了向下兼容
        """
        return list(self._task_dict.keys())

    def get_pre_assigned_cfg(self, source):
        """
        如果某个子进程被分派了任务又重新申请，则还是返回原来任务给它。
        如果这个子进程没有出现在任务注册表中，返回空。

        Parameters
        ----------
        source : 子进程的名称标识。

        Returns
        -------

        Raises
        ----------
        """
        _task_cfg_dict = None
        _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()  # 待分配任务表
        # 遍历主进程管理的任务列表
        for _rtsp_url, _task_info in self._task_dict.items():
            if _task_info.name == source:  # 这个子进程注册过吗？
                for _channel_dict in _v2v_cfg_dict['rtsp_urls']:
                    # 根据任务中的url地址重新取配置信息
                    if _channel_dict and _rtsp_url == _channel_dict['rtsp_url']:  # 注册的这个url对应的配置取出来
                        _task_cfg_dict = _channel_dict
                        break
        return _task_cfg_dict

    def assign_task(self, source, assigned=None) -> dict:
        """
        根据子进程的请求，返回一个含url的任务配置信息。如果发现没有可分配的任务，则返回[]。

        Parameters
        ----------
        source:  子进程名称，可唯一标识子进程。
        assigned: 子进程此前分配的任务。

        Returns
        -------
        Dict
            带全部配置信息，但rtsp_urls数组中只有一个元素rtsp_url。
        Raises
        ----------
        RuntimeError
            待定.
        """
        _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
        _v2v_cfg_dict = copy.deepcopy(_v2v_cfg_dict)
        _new_task_cfg_dict = None
        # 遍历所有通道
        for channel in _v2v_cfg_dict['rtsp_urls']:
            if not channel:
                continue
            _rtsp_url = channel['rtsp_url']
            # 如果_task_dict中有这个值，说明有人先注册处理这个任务，再找下个待分配任务。
            if _rtsp_url in self._task_dict.keys():
                continue
            # 以前没分配过任务，或者分配过，但新的配置中没有那个任务了，均可以分配新的url
            _new_task_cfg_dict = self.get_pre_assigned_cfg(source)
            if _new_task_cfg_dict is None:
                _new_task_cfg_dict = channel
                # 创建任务信息对象
                _task_info = TaskInfo(_rtsp_url)
                _task_info.name = source
                _task_info.did = channel['device_id']
                _task_info.cid = channel['channel_id']
                self._task_dict.update({_rtsp_url: _task_info})
                self.log(f'Assign new task --> :{_rtsp_url}: {source}', level=log.LOG_LVL_INFO)
                break
        if _new_task_cfg_dict:
            _v2v_cfg_dict['rtsp_urls'] = [_new_task_cfg_dict]
        else:
            _v2v_cfg_dict['rtsp_urls'] = []
        return _v2v_cfg_dict

    def query_task_obj_by_url(self, rtsp_url) -> None or TaskInfo:
        """
        通过RTSP链接查询，执行该RTSP链接的任务对象
        """
        pass

    def query_task_obj_by_pid(self, pid) -> None or TaskInfo:
        """
        通过进程号查询，该进程执行任务的对象
        """
        _ret_obj = None
        for _task_info in self._task_dict.values():
            if _task_info.tpid == pid:
                _ret_obj = _ret_obj
                break
        return _ret_obj

    def query_task_obj_by_channel(self, did, cid) -> None or TaskInfo:
        """
        通过设备ID和通道ID查询，执行该ID通道的任务对象
        """
        _ret_obj = None
        for _task_info in self._task_dict.values():
            if _task_info.did == did and _task_info.cid == cid:
                _ret_obj = _ret_obj
                break
        return _ret_obj

    def dump_task_info(self) -> list:
        """
        输出当前所有管理任务的状态信息
        """
        _dump_list = []
        for _task_info in self._task_dict.values():
            # 获取进程状态
            _process_info_dict = self._p_manage.get_process_state_info(_task_info.tpid)
            _task_info_dict = _task_info.dump()
            self.log(f"{_task_info_dict}-{_process_info_dict}", level=log.LOG_LVL_DBG)
            if _process_info_dict is not None:
                _task_info_dict.update(_process_info_dict)
            _dump_list.append(_task_info_dict)
        return _dump_list

    def update_process_info(self, param):
        self._p_manage.update_process_info(param)

    def dump_process_info(self):
        pass
