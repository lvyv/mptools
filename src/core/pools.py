#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : pools.py
# @Time    : 2022/3/6 15:27
# @Author  : XiongFei
# Description：该类用于管理进程池状态，包含：每个进程的状态，以及每个进程当前处的阶段（startup, mainloop, shutdown...）
import functools
import os
from enum import unique, Enum

from utils import log


@unique
class ProcessState(Enum):
    # 该进程处于空闲状态
    INIT = 0
    # 进程处于startup阶段
    START = 1
    # 该进程处于运行状态,mainloop
    RUN = 2
    # 进程处于shutdown阶段
    SHUT = 3
    # 该进程处于暂停状态
    PAUSE = 4


class ProcessInfo:
    def __init__(self):
        # 运行时间
        self.up_time = 0
        # 进程号
        self.pid = 0
        # 进程的标识名称，不是进程名
        self.name = None
        # 进程上一次的状态
        self.pre_state = ProcessState.INIT
        self.new_state = ProcessState.INIT


class ProcessManage:
    def __init__(self):
        self.log = functools.partial(log.logger, f'PROCESS-MANAGE-{os.getpid()}')
        # {pid: _process_info}
        self._process_dict = dict()

    def clear(self):
        self._process_dict.clear()
        self._process_dict = dict()

    def get_process_state_info(self, pid) -> None or dict:
        _ret = None
        if pid in self._process_dict.keys():
            _p_obj = self._process_dict[pid]
            _ret = {'pre_state': _p_obj.pre_state,
                    'new_state': _p_obj.new_state,
                    'uptime': _p_obj.up_time}
        return _ret

    def update_process_info(self, params):
        _pid = params.get('pid', None)
        if _pid is None:
            return

        _name = params.get('name', None)
        _pre_state = params.get('pre_state', None)
        _new_state = params.get('new_state', None)
        _up_time = params.get('up', None)

        _p_obj = None
        if _pid in self._process_dict.keys():
            _p_obj = self._process_dict[_pid]
        else:
            _p_obj = ProcessInfo()
            self._process_dict.update({_pid: _p_obj})

        _p_obj.pid = _pid
        if _name:
            _p_obj.name = _name
        if _pre_state:
            _p_obj.pre_state = ProcessState(_pre_state)
        if _new_state:
            _p_obj.new_state = ProcessState(_new_state)
        if _up_time:
            _p_obj.up_time = _up_time
