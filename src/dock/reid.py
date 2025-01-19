#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OPTiDOCK
# The ReID Process.
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
import os
import queue
import time

from core.procworker import ProcWorker
from utils import bus, log


class ReIDWorker(ProcWorker):
    def __init__(self, name, in_q=None, out_q=None, dicts=None, **kwargs):
        super().__init__(name, bus.EBUS_TOPIC_BROADCAST, dicts, **kwargs)
        # self.bus_topic_ = bus.EBUS_TOPIC_AI
        self.in_q_ = in_q
        self.out_q_ = out_q

    def startup(self, evt=None):
        self.log(f"[{self.__class__.__name__}] has started.", level=log.LOG_LVL_INFO)
        pass

    def main_func(self, event=None, *args) -> bool:
        """
        本函数实现跨摄像头目标对象关联逻辑。
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
        ret = False

        try:
            part = self.in_q_.get_nowait()
            part.update({f'{self.__class__.__name__}': os.getpid()})
            self.out_q_.put_nowait(part)
        except queue.Empty:
            time.sleep(0.01)
            return False

        return ret

    def shutdown(self):
        self.log(f"[{self.__class__.__name__}] has exited.", level=log.LOG_LVL_INFO)
        pass
