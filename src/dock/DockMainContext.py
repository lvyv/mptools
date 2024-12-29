#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OPTiDOCK
# The Main Context of the running processes.
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
    with DockMainContext() as main_ctx:
        main_ctx.run('conf/v2v.cfg')
"""
from utils import bus, log
from core.kernel import MainContext
from dock.D3Construct import D3ConstructWorker
from dock.ObjTracker import ObjTrackerWorker
from dock.ReID import ReIDWorker


class DockMainContext(MainContext):
    def __init__(self):
        # 日志输出偏函数
        super().__init__()

    def __switch_on_process(self, name, **kwargs):
        """
        本函数调用工厂类在主进程上下文环境启动所有子进程.
        创建包含指定数量进程的进程池，运行所有进程，并把所有进程执行结果合并为列表，返回.
        同时会将创建的进程池保存在列表中.

        Parameters
        ----------
        name : 区别不同子进程的名称.
            包括：D3Construct，ObjTracker，ReID.
        *kwargs: dict, None
            指定创建进程的数量，比如cnt=3, 表示创建和启动包含3个进程的进程池.
        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表.
        Raises
        ----------
        RuntimeError
            待定.
        """
        if 'D3Construct' == name:
            res = self._factory.create(D3ConstructWorker, name, None, self._queue_frame, **kwargs)
        elif 'ObjTracker' == name:
            res = self._factory.create(ObjTrackerWorker, name, self._queue_frame, self._queue_vector, **kwargs)
        elif 'ReID' == name:
            res = self._factory.create(ReIDWorker, name, self._queue_vector, None, **kwargs)
        else:
            res = (None, None)
        return res

    def fork_work_process(self, expect_rtsp_num=1, now_rtsp_num=1, now_ai_num=1, now_mqtt_num=1) -> bool:
        """
        动态创建工作进程数量.

        return true 创建成功，false 创建失败
        """
        _ret = False

        self.__switch_on_process('ObjTracker')
        self.__switch_on_process('ReID')
        self.__switch_on_process('D3Construct')
        self.log(f'[MAIN] ObjTracker-->ReID-->D3Construct', level=log.LOG_LVL_INFO)
        return True

    def start_v2v_pipeline_task(self):
        # 标记工作状态
        _ret = self.fork_work_process()
        if _ret is True:
            self.log(f"[MAIN] start_v2v_pipeline_task success.", level=log.LOG_LVL_DBG)
        else:
            self.log(f'[MAIN] start_v2v_pipeline_task failed', level=log.LOG_LVL_ERRO)

    def stop_v2v_pipeline_task(self):
        # 停止流水线子进程，需要对任务列表初始化，便于重新分配任务.
        if self._task_manage:
            self._task_manage.clear_task()
        # 微服务进程与主进程同时存在，不会停
        self.log("[MAIN] stop_v2v_pipeline_task()")
        msg = bus.EBUS_SPECIAL_MSG_STOP
        self.broadcast(bus.EBUS_TOPIC_BROADCAST, msg)
        return True
