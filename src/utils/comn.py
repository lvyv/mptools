#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : comn.py
# @Time    : 2022/3/7 10:32
# @Author  : XiongFei
# Description：通用模块，保存公共的功能函数
import time


def replace_non_ascii(x):
    return ''.join(i if ord(i) < 128 else '_' for i in x)


def get_time_in_ms():
    """
    获取当前的时间，单位毫秒
    """
    t = time.time()
    return int(round(t * 1000))


def get_pid_from_process_name(value) -> int:
    _pid = -1
    _start = value.find('(')
    _end = value.find(')')
    if _start != -1 and _end != -1:
        # 取任务进程号
        _pid = int(value[_start + 1:_end])
    return _pid


if __name__ == '__main__':
    # print(get_time_in_ms())
    print(get_pid_from_process_name("RTSP(12350)"))
