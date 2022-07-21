#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : demo.py
# @Time    : 2022/7/21 14:23
# @Author  : XiongFei
# Description：
import re


def check_null_if():
    _dict = dict()

    cmd = _dict.get('cmd', None)
    if cmd == 'get_cfg':  # 取v2v.cfg
        print('get cfg')
    else:
        print('null')


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


if __name__ == '__main__':
    # check_null_if()
    print(is_number('1.5'))
    print(is_number(1.5))
    print(is_number('null'))
