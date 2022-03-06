#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : pools.py
# @Time    : 2022/3/6 15:27
# @Author  : XiongFei
# Description：该类用于管理进程池状态，包含：每个进程的状态，以及每个进程当前处的阶段（startup, mainloop, shutdown...）
from enum import unique, Enum


@unique
class ProcessState(Enum):
    # 该进程处于空闲状态
    INIT = 0
    # 该进程处于运行状态
    RUN = 1
    # 该进程处于暂停状态
    PAUSE = 2
