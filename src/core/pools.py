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
        # 进程状态
        self.state = ProcessState.INIT


class ProcessManage:
    def __init__(self):
        self.log = functools.partial(log.logger, f'PROCESS-MANAGE-{os.getpid()}')
        # {pid: _process_info}
        self._process_dict = dict()

    def clear(self):
        self._process_dict.clear()
        self._process_dict = dict()


