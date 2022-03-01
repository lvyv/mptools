#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : main.py.py
# @Time    : 2022/3/1 15:29
# @Author  : XiongFei
# Description：
import sys
from pathlib import Path

# 配置python加载路径
_module_path = Path(Path(__file__).parent)
sys.path.append(str(_module_path))
from src.utils.config import ConfigSet
from core.kernel import MainContext
from utils import log, comn


def _main_entry():
    # 构造配置文件路径
    _v2v_cfg = Path(Path(__file__).parent).joinpath("conf/v2v.cfg")
    _base_cfg = Path(Path(__file__).parent).joinpath("conf/baseconfig.cfg")
    _log_cfg = Path(Path(__file__).parent).joinpath("conf/logging.conf")

    # 初始化配置文件路径
    ConfigSet.set_v2vcfg_file_path(_v2v_cfg)
    ConfigSet.set_basecfg_file_path(_base_cfg)
    # 加载日志记录器配置文件
    log.init_logger(str(_log_cfg))

    # 初始化comn模块
    _v2v_cfg_dict = ConfigSet.get_v2v_cfg_obj()
    if _v2v_cfg_dict is None:
        print("Init v2v config file failed.")
        return
    comn.set_common_cfg(_v2v_cfg_dict)

    # 进程主循环
    with MainContext() as main_ctx:
        main_ctx.run()


if __name__ == "__main__":
    _main_entry()
