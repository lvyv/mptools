#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# @File    : main.py.py
# @Time    : 2022/3/1 15:29
# @Author  : XiongFei
# Description：
import sys
from pathlib import Path

# 配置python加载路径
_module_path = Path(Path(__file__).absolute().parent)
sys.path.append(str(_module_path))
# sys.path.append(str(_module_path.joinpath("core")))
# sys.path.append(str(_module_path.joinpath("utils")))
from utils.config import ConfigSet
from core.kernel import MainContext
from utils import log, comn
from conf import const


def _main_entry():
    # 设置配置文件路径
    ConfigSet.set_v2vcfg_file_path(const.V2V_CFG_PATH)
    ConfigSet.set_basecfg_file_path(const.BASE_CFG_PATH)

    # 加载日志记录器配置文件
    log.init_logger(const.LOG_CFG_PATH)

    # 初始化comn模块
    comn.set_common_cfg(ConfigSet.get_v2v_cfg_obj())

    # 进程主循环
    with MainContext() as main_ctx:
        main_ctx.run()


if __name__ == "__main__":
    _main_entry()
