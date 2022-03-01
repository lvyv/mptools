#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : const.py
# @Time    : 2022/3/1 19:42
# @Author  : XiongFei
# Description：
from pathlib import Path

# 相对于const.py文件的路径
V2V_CFG_PATH = Path(Path(__file__).parent).joinpath("v2v.cfg")
BASE_CFG_PATH = Path(Path(__file__).parent).joinpath("baseconfig.cfg")
LOG_CFG_PATH = Path(Path(__file__).parent).joinpath("logging.conf")
