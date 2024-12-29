#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OPTiDOCK
# The 3D Reconstruct Process.
#
#
# Awen. 2024.12
#
# 致谢
#
# Copyright (C) 2021 lvyu <lvyu@cxtc.edu.cn>
# Licensed under the GNU LGPL v2.1 - https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html

"""
Test with::

"""


from core.procworker import ProcWorker
from utils import bus


class D3ConstructWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q

    def startup(self, evt=None):
        pass

    def main_func(self, event=None, *args) -> bool:
        """
        本函数实现三维座标重建逻辑。
        重载基类主循环函数调用。

        Parameters
        ----------
        event : 主事件循环的外部事件回调。
        *args: tuple, None
            扩展参数。
        Returns
        -------
            返回True，退出循环，返回False，继续循环。
        """
        _ret = False
        return _ret

    def shutdown(self):
        pass
