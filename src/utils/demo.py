#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : demo.py
# @Time    : 2022/7/21 14:23
# @Author  : XiongFei
# Description：

def check_null_if():
    _dict = dict()

    cmd = _dict.get('cmd', None)
    if cmd == 'get_cfg':  # 取v2v.cfg
        print('get cfg')
    else:
        print('null')


if __name__ == '__main__':
    check_null_if()
