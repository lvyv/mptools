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


if __name__ == '__main__':
    print(get_time_in_ms())