#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 The OPTiDOCK Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# pylint: disable=invalid-name
# pylint: disable=missing-docstring
import functools
import multiprocessing
import os
import signal
import time
import zmq
from utils import bus, log
from utils.config import ConfigSet
from utils.wrapper import proc_worker_wrapper, daemon_wrapper, worker_wrapper


def init_worker():
    # 忽略ctrl+c信号
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    pass


class ProcSimpleFactory:
    """创建子进程对象工厂类.
    设置proc_worker_wrapper函数，作为所有子进程的入口.
    子进程分别在该函数中实例化进程对象，并启动主循环.
    """
    # 类变量，供类方法调用
    _web_process_handle = None  # rest 进程句柄
    _process_pool_handle = None  # rtsp,ai,mqtt 进程池句柄

    def __init__(self, nop):
        self.log = functools.partial(log.logger, f'ProcSimpleFactory')
        self._pool_size = nop
        if self._process_pool_handle is None:
            self._process_pool_handle = multiprocessing.Pool(processes=self._pool_size, initializer=init_worker)

    # 创建进程，每个进程的名称：NAME(PID)
    def create(self, worker_class, name, in_q=None, out_q=None, **kwargs):
        # 启用进程的数量
        _process_cnt = kwargs.get("cnt", 1)
        res = self._process_pool_handle.starmap_async(proc_worker_wrapper,
                                                      [(worker_class,
                                                        name,
                                                        in_q,
                                                        out_q,
                                                        kwargs)
                                                       for _ in range(_process_cnt)])
        return res

    def create_worker(self, worker_class, name, in_q=None, out_q=None, **kwargs):
        res = False
        # 启用进程的数量
        workers = kwargs['worker_services']
        found_item = next((d for d in workers if worker_class in d), None)
        if found_item:
            process_cnt = found_item[worker_class].get('cnt')
            res = self._process_pool_handle.starmap_async(worker_wrapper,
                                                          [(worker_class,
                                                            name,
                                                            in_q,
                                                            out_q,
                                                            kwargs)
                                                           for _ in range(process_cnt)])
        return res

    @classmethod
    def teminate_rest(cls):
        if cls._web_process_handle:
            cls._web_process_handle.terminate()
            cls._web_process_handle.join()

    @classmethod
    def terminate(cls):
        if cls._process_pool_handle:
            cls._process_pool_handle.terminate()

    @classmethod
    def close(cls):
        if cls._process_pool_handle:
            cls._process_pool_handle.close()

    @classmethod
    def join(cls):
        if cls._process_pool_handle:
            cls._process_pool_handle.join()

    @classmethod
    def create_daemon(cls, worker_class, name, **kwargs):
        if cls._web_process_handle is None:
            # name = f'{name}-{os.getpid()}'
            dp = multiprocessing.Process(target=daemon_wrapper, args=(worker_class, name, kwargs), kwargs=kwargs)
            dp.daemon = True
            dp.start()
            cls._web_process_handle = dp
        return cls._web_process_handle


class FSM:
    """
    描述程序内部状态的有限状态机
    """
    STATUS_INITIAL = 0
    STATUS_FULL_SPEED = 1
    STATUS_ERROR = 2

    current_state_ = None

    def __init__(self):
        self.current_state_ = self.STATUS_INITIAL

    def test_status(self, criterion):
        return self.current_state_ == criterion

    def set_status(self, status):
        if status in [getattr(FSM, y) for y in [x for x in dir(self) if x.find('STATUS') == 0]]:
            self.current_state_ = status


class MainContext(bus.IEventBusMixin):
    """封装主进程模块类.
    完成所有子进程的创建，终止工作.
    完成对所有运行子进程的下发配置和查询状态（主要是事件总线和图片及向量队列）.
    """
    NUMBER_OF_PROCESSES = 12  # 进程池默认数量

    def __init__(self, cfg='conf//v2v.cfg'):
        # 日志输出偏函数
        self.log = functools.partial(log.logger, f'MCTX-{os.getpid()}')
        # 初始化MQ服务器句柄
        if MainContext.center_ is None:
            MainContext.center_ = bus.IEventBusMixin.get_center()
        # 初始化MQ服务器广播句柄
        if MainContext.broadcaster_ is None:
            MainContext.broadcaster_ = bus.IEventBusMixin.get_broadcaster()
        # 创建进程池进程备用
        self._factory = ProcSimpleFactory(self.NUMBER_OF_PROCESSES)
        # 处理配置信息
        if cfg:
            ConfigSet.set_v2vcfg_file_path(cfg)
        cfg_dict = ConfigSet.get_v2v_cfg_obj()
        manager = multiprocessing.Manager()
        self._shared_config = manager.dict(cfg_dict)
        # 初始化进程状态管理类
        self._status = FSM()

    def __enter__(self):
        self.log('********************  MainContext V2V AI Dispatching Center  ********************')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.log(f'1.{exc_val}', level=log.LOG_LVL_ERRO, exc_info=(exc_type, exc_val, exc_tb))
        # -- Don't eat exceptions that reach here.
        return not exc_type

    def fork_restful_process(self, cls='core.rest.RestWorker', **kwargs):
        """
        本函数调用工厂类在主进程上下文环境启动rest子进程.
        rest子进程与其它子进程不一样，它与主进程是同生同死的，属于daemon子进程.

        Parameters
        ----------
        *cls:  str.
            指定REST类.
        *kwargs:  port, ssl_keyfile, ssl_certfile.
            指定创建rest进程的端口，https.
        Returns
        -------
        List
            该进程池所有进程执行完成的结果构成的列表.
        Raises
        ----------
        RuntimeError
            待定.
        """
        res = self._factory.create_daemon(cls, 'REST', **kwargs)
        return res

    def fork_work_process(self, **kwargs) -> bool:
        """
        本函数由子类重载，按需要的业务逻辑创建需要的进程，并配置它们之间的读写数据队列.

        Parameters
        ----------
        **kwargs:
            参数示例为整个配置文件.
        Returns
        -------
        bool
            是否成功.
        Raises
        ----------
        RuntimeError
            待定.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.fork_work_process is not implemented")

    def show_queues_status(self):
        """
        本函数由子类重载，按需要的业务逻辑显示当前所有消息队列状态。

        Parameters
        ----------
        Returns
        -------
        Raises
        ----------
        RuntimeError
            待定.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.show_queues_status is not implemented")

    def run(self, rest='core.rest.RestWorker', **kwargs):
        try:
            # 启动所有的工作进程
            self.fork_work_process(**self._shared_config)
            # 启动1个Restful进程，提供微服务调用
            self.fork_restful_process(cls=rest, **self._shared_config)

            # 进入主循环，阻塞处理子进程之间的消息.
            self.log(f"[{self.__class__.__name__}] Enter main event loop.", level=log.LOG_LVL_DBG)
            _main_start_time, _process_pool_time = time.time(), time.time()
            _log_interval = 15
            while True:
                # rpc远程调用服务启动，非阻塞等待外部事件出发状态改变
                try:
                    MainContext.rpc_service()
                except zmq.Again as err:  # noqa
                    time.sleep(0.01)
                # 间隔输出程序运行状态
                if (time.time() - _main_start_time) >= _log_interval:
                    self.show_queues_status()
                    _main_start_time = time.time()
        except KeyboardInterrupt as err:  # noqa
            self.log(f'[{self.__class__.__name__}] Main process get ctrl+c', level=log.LOG_LVL_ERRO)
            self._factory.teminate_rest()
            self._factory.terminate()
        finally:
            self.log(f'[{self.__class__.__name__}] Main process exit.')
            self._factory.close()
            self._factory.join()
