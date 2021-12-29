#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 The CASICloud Authors. All Rights Reserved.
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

"""
=========================
unit test module
=========================

测试multiprocessing库的一些用法及python code snippet.
"""

# Author: Awen <26896225@qq.com>
# License: MIT
from __future__ import print_function
import unittest

# import os
# import signal
# from random import randrange
from multiprocessing import Pool
from os import listdir
from os.path import isfile, join
from time import time, sleep

from utils import wrapper as wpr
from utils import log
# from core.procworker import ProcWorker

import json
import zmq
import random
import requests
import cv2
import io
import imutils
# import base64
import multiprocessing
import os
import signal
import time
from imutils.video import VideoStream

from matplotlib import pyplot as plt
# import matplotlib
import numpy as np

# ----fastapi-----
from fastapi import File, UploadFile
from fastapi_utils.tasks import repeat_every
import uvicorn
import logging
from jaeger_client import Config
# from opentracing import set_global_tracer, Format
# import asyncio
# from typing import Any, Dict, Optional

from fastapi import FastAPI
# from fastapi.testclient import TestClient

from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info
from prometheus_client import Gauge, Counter
from typing import Callable
from fastapi.testclient import TestClient
import psutil
from children import sample_rtsp_frame

app = FastAPI()


def call_aimeter(contents):
    print(contents)
    ret = [
        {'id': 1, 'key1': 31.2, 'loc': [14, 23]},
        {'id': 2, 'key2': 20, 'loc': [102, 538]}
    ]
    return ret


@app.post("/files/")
async def create_file(file: bytes = File(...)):
    fs = len(file)
    print(fs)
    return {"file_size": fs}


@app.post("/uploadfile/")
async def create_upload_file(upfile: UploadFile = File(...)):
    print(upfile.filename, upfile.content_type)
    contents = upfile.file.read()
    # outfile = open(upfile.filename, 'wb')
    # outfile.write(contents)
    # outfile.close()
    ret = call_aimeter(contents)
    return ret


# ----pool-----

work = [("A", 5), ("B", 2), ("C", 1), ("D", 3)]


def work_log(name, ts):
    print(f" Process {name} waiting {ts} seconds.")
    sleep(ts)
    print(f" Process {name} Finished.")


def pool_handler():
    p = Pool(2)
    p.starmap(work_log, [it for it in work])


# ----args-----


def test_kwargs(**kwargs):
    for k, v in kwargs.items():
        print(k, v)


def test_arg(*args, **kwargs):
    test_kwargs(**kwargs)
    for it in args:
        print(it)
    return True


def replace_non_ascii(x): return ''.join(i if ord(i) < 128 else '_' for i in x)


def test_upload_img():
    vs_ = VideoStream('rtsp://127.0.0.1/live').start()
    inteval = 1
    while True:
        sleep(inteval - time() % inteval)  # 休眠采样间隔的时间，动态调速
        frame = vs_.read()
        if frame is not None:
            frame = imutils.resize(frame, width=1200)  # size changed from 6MB to 2MB
            cv2.imshow('NVR realtime', frame)
            buf = io.BytesIO()
            plt.plot()
            plt.imsave(buf, frame, format='png')
            image_data = buf.getvalue()
            rest = 'https://127.0.0.1:21900/meter_recognization/'
            name = r'No1.缺省'
            files = {'upfile': (replace_non_ascii(name), image_data, 'image/png')}
            resp = requests.post(rest, files=files, verify=False)  # data=image_data)
            print(resp)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break


def uploadfiles():
    rest = 'https://127.0.0.1:7180/api/v1/uploadfiles'
    mypath = '../src/mock/local/'
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    files = [('files', (replace_non_ascii(name), open(f'{mypath}{name}', 'rb'))) for name in onlyfiles]
    requests.post(rest, files=files, verify=False)  # data=image_data)


def uploadfile_withparams():
    rest = 'https://127.0.0.1:7180/api/v1/uploadfile_with_params'
    mypath = '../src/mock/local/'
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    files = {
        'jso': (None, '{"key1":"value1"}', 'application/json'),
        'file': (onlyfiles[0], open(f'{mypath}{onlyfiles[0]}', 'rb'), 'application/octet-stream')
    }
    requests.post(rest, files=files, verify=False)  # data=image_data)


def uploadfiles_withparams():
    rest = 'https://127.0.0.1:7180/api/v1/uploadfiles_with_params'
    # upload local files
    mypath = '../src/mock/local/'
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    files = [('files', (replace_non_ascii(name), open(f'{mypath}{name}', 'rb'))) for name in onlyfiles]
    payload = {'jsos': '{"key1":1, "key2":2}'}
    ret = requests.post(rest, files=files, data=payload, verify=False)  # data=image_data)
    log.log(ret)
    for it in files:
        it[1][1].close()

    # upload memory files
    t = np.arange(0.0, 2.0, 0.01)
    s = 1 + np.sin(2 * np.pi * t)
    fig, ax = plt.subplots()
    ax.plot(t, s)
    ax.set(xlabel='time (s)', ylabel='voltage (mV)',
           title='About as simple as it gets, folks')
    ax.grid()
    b = io.BytesIO()
    plt.savefig(b, format='png')
    plt.close()
    b.seek(0)
    files = [('files', ('iobytes.png', b))]
    payload = {'jsos': '{"key3":1, "key2":4}'}
    requests.post(rest, files=files, data=payload, verify=False)
    b.close()


# ----zmq-----


address_ = f'tcp://127.0.0.1:5555'


def svr(name, ts):
    print(ts)
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(address_)
    while True:
        #  Wait for next request from client
        print(f"{name}: waiting message...")

        message = socket.recv()
        print(f"{name}: Received request: {message}")

        #  Do some 'work'
        sleep(0.5)
        print(f'begin sending reply...')
        #  Send reply back to client
        socket.send_string(f"{message}, World")  # noqa
        print(f'send.')


def cli(name, ts):
    print(ts)
    context = zmq.Context()
    #  Socket to talk to server
    print("Connecting to hello world server...")
    socket = context.socket(zmq.REQ)
    socket.connect(address_)
    print('connected.')
    #  Do 10 requests, waiting each time for a response
    for request in range(10):
        print(f"{name}, Sending request {request} ...")
        socket.send_string(f"send Hello({request}) ")  # noqa
        # socket.send_string(f"send hello twice")
        #  Get the reply.
        message = socket.recv()
        print(f"{name}, Received reply {request} [ {message} ]")


def pools():
    p = None
    try:
        # cs = center()
        # sleep(1)
        # bbp = beeper()
        p = Pool(2)
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGINT, original_sigint_handler)

        p.apply_async(svr, (f'Center', random.randint(1, 3)))
        p.apply_async(cli, (f'beeper1', random.randint(1, 3)))
        p.apply_async(cli, (f'beeper2', random.randint(1, 3)))
        while True:
            sleep(0.5)
            pass
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating workers")
        p.terminate()
    # else:
    #     p.close()
    #     p.join()


def pub(name, ts):
    try:
        print(ts)
        print(f'{name}-{os.getpid()}')
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind("tcp://*:5556")
        cnt = 0
        while cnt < 1000:
            sleep(0.1)
            msg = f"中 国 {cnt} 中 {cnt}"
            print(msg)
            socket.send_string(msg)  # noqa
            cnt += 1
        while True:
            pass
    except KeyboardInterrupt:
        print("------------pub-------Caught KeyboardInterrupt, terminating workers-----------------")


def sub(name, ts):
    try:
        #  Socket to talk to server
        print(ts)
        print(f'{name}-{os.getpid()}')
        context = zmq.Context()
        socket = context.socket(zmq.SUB)

        print("Collecting updates from weather server...")
        socket.connect("tcp://localhost:5556")
        strfilter = '中'
        socket.setsockopt_string(zmq.SUBSCRIBE, strfilter)  # noqa

        while True:
            st = socket.recv_string()  # noqa
            print(f'recv: {st}')
    except KeyboardInterrupt:
        print("-----------sub--------Caught KeyboardInterrupt, terminating workers-----------------")


# def pub11(name, delay):
#     try:
#         print("In a worker process", os.getpid())
#         time.sleep(delay)
#     except KeyboardInterrupt:
#         print("-------------------Caught KeyboardInterrupt, terminating workers-----------------")
#         # pool.terminate()
#
#
# def sub11(name, delay):
#     try:
#         print("In a worker process", os.getpid())
#         time.sleep(delay)
#     except KeyboardInterrupt:
#         print("-------------------Caught KeyboardInterrupt, terminating workers-----------------")
#         # pool.terminate()


def pub_sub_pools():
    p = Pool(3)
    try:
        res1 = p.apply_async(pub, (f'pub', 3))
        res2 = p.apply_async(sub, (f'sub1', 3))
        res3 = p.apply_async(sub, (f'sub2', 3))
        logging.info(f'{res1}, {res2}, {res3}')
        # res1.get(60)
        # res2.get(60)
        # res3.get(60)
        # print('--------------------------------')
        # p.close()
        while True:
            pass
    except KeyboardInterrupt:
        print('ctrl+C<<<')
        p.terminate()
    # else:
    #     p.close()
    #     print("Normal termination")
    p.close()
    p.join()


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


def svr2(name, ts):
    print(ts)
    while True:
        #  Wait for next request from client
        print(f'{name} begin sleeping...')
        sleep(ts)
        print(f'{name} wakeup.')


def cli2(name, ts):
    for request in range(10):
        print(f"{name}, Sending request {request} ...")
        sleep(ts)
        print(f"{name}, Received reply {request} [ {'ccccc'} ]")


def keyboard_interrupt():
    p = Pool(3)
    try:
        p.apply_async(svr2, (f'Center', random.randint(1, 1)))
        p.apply_async(cli2, (f'beeper1', random.randint(1, 1)))
        res = p.apply_async(cli2, (f'beeper2', random.randint(1, 1)))
        res.get(60)
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating workers")
        p.terminate()
    else:
        p.close()
    p.join()


def run_worker(name, delay):
    try:
        print(f'In a worker process- {name}', os.getpid())
        time.sleep(delay)
    except KeyboardInterrupt:
        print("-------------------Caught KeyboardInterrupt, terminating workers-----------------")
        # pool.terminate()


def main():
    print("Initializng 2 workers")
    vec_q_ = multiprocessing.Manager().Queue()
    # original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    # original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = multiprocessing.Pool(2)
    # signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        print(f'{vec_q_}, Starting 2 jobs of 5 seconds each')
        res = pool.starmap_async(run_worker, [('a', 15), ('b', 16)])
        print("Waiting for results")

        res.get(60)  # Without the timeout this blocking call ignores all signals.
        print('-------------------OK--------------------------')
    except KeyboardInterrupt:
        print("-------------------Caught KeyboardInterrupt, terminating workers-----------------")
        pool.terminate()
    else:
        print("Normal termination")
        pool.close()
    pool.join()


# --- test ctrl+c --- #


ipc_address_ = f'tcp://127.0.0.1:5155'
child_process_cli_ = None


@app.on_event("startup")
@repeat_every(seconds=1, wait_first=True)
def periodic():
    """周期性任务，用于读取系统状态和实现探针程序数据来源的提取"""
    if child_process_cli_:
        child_process_cli_.send_string('hello---')  # noqa
        print(child_process_cli_.recv())  # noqa


def run_fastapi(name):
    global child_process_cli_
    context = zmq.Context()
    #  Socket to talk to server
    print(f'{name} - Connecting to hello world server...')
    socket = context.socket(zmq.REQ)
    socket.connect(ipc_address_)
    child_process_cli_ = socket
    uvicorn.run('test_snippet:app', host="0.0.0.0", port=21800)
    print('going to exit...')
    socket.send_string('exit...')  # noqa


def fastapi_main():
    dp = multiprocessing.Process(target=run_fastapi, args=('fastapi',))
    dp.daemon = True
    dp.start()
    return dp


def fastapi_mainloop():
    dp = None
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(ipc_address_)
        dp = fastapi_main()
        while True:
            msg = socket.recv()
            print(f'main:{msg}')
            socket.send_string('back')  # noqa
    except KeyboardInterrupt:
        print('----KeyboardInterrupt----')
        dp.terminate()

    print('finally')


def stream_null_inject(stream):
    (ret, frame) = stream.read()
    # frame = None    # inject null frame test.
    return ret, frame


def nvr_stream_func():
    # rtspurl = 'rtsp://192.168.1.225:7554/plc'
    rtspurl = 'rtsp://user:userpass@192.168.1.225:7554/person'
    rtspurl = 'rtsp://admin:admin123@192.168.101.39:554/cam/realmonitor?channel=1&subtype=0'
    cap = cv2.VideoCapture(rtspurl)
    print(f'fps: {cap.get(cv2.cv2.CAP_PROP_FPS)}')
    opened = cap.isOpened()
    if opened:
        while True:
            try:
                # ret, frame = cap.read()
                ret, frame = stream_null_inject(cap)
                if frame is None:
                    raise cv2.error(f'Null frame got.')
                height, width, channels = frame.shape
                logging.info(f'{height},{width}')
                cv2.imshow('frame', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except cv2.error as cve:
                print(cve)
                cap.release()
                cv2.destroyAllWindows()
                cap = cv2.VideoCapture('rtsp://127.0.0.1/live')
                # break
    else:
        print('can not open the video source.')
    cap.release()
    cv2.destroyAllWindows()
    pass


def save_json():
    abc = {'key1': 1,
           'key2': 'value2',
           '中k': '中文支持'
           }
    with open('abc.cfg', 'w', encoding='utf-8') as fp:
        json.dump(abc, fp, ensure_ascii=False)
    filename = "./foo/bar/baz/a.txt"
    os.makedirs(os.path.dirname(filename), exist_ok=True)


class UrlStatisticsHelper:
    def __init__(self, criterion=100):
        self.urls_ = []
        self.criterion_ = criterion  # 连续几次（比如3）访问失败，就不再允许访问，直到发现请求持续超过（100）次，重新放行。

    def add(self, url):
        found = False
        for it in self.urls_:
            if it['url'] == url:
                it['cnt'] += 1
                found = True
                break
        if not found:
            self.urls_.append({'url': url, 'cnt': 1})

    def get_cnts(self, url):
        ret = -1
        for it in self.urls_:
            if it['url'] == url:
                ret = it['cnt']
        return ret

    def waitforrecover(self, url):
        cnt = self.get_cnts(url)
        if cnt < self.criterion_:
            self.add(url)
        else:
            self.freeup(url)

    def freeup(self, url):
        found = False
        for it in self.urls_:
            if it['url'] == url:
                it['cnt'] = 0  # 刑满释放
                found = True
                break
        return found


def test_url_statistics():
    urls = UrlStatisticsHelper(criterion=8)
    url = 'https://192.168.1.4/api/v1/ai/plc'
    while True:
        somethingbad = random.randint(0, 5) == 2
        if somethingbad:
            log.log('something bad happened!')
            urls.add(url)
        if urls.get_cnts(url) < 3:
            log.log('run...')
        else:
            urls.waitforrecover(url)
            log.log('in jail...')


def test_opencv_capture_timeout():
    rtsp = 'rtsp://user:userpass@192.168.1.225:7554/plc'
    try:
        cap_status, cap = wpr.video_capture_open(rtsp)
        if not cap_status:
            print(cap_status, cap)
            return cap
        while True:
            ret, image_frame = cap.read()
            cv2.imshow("res", image_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
    except Exception as err:
        print(err)
        pass


def construct_span(tracer):
    with tracer.start_span('AliyunTestSpan') as span:
        span.log_kv({'event': 'test message', 'life': 42})
        span.set_tag('key2', 60)
        print("tracer.tages: ", tracer.tags)
        with tracer.start_span('AliyunTestChildSpan', child_of=span) as child_span:
            span.log_kv({'event': 'down below'})
            child_span.log_kv({'event': 'child'})
        return span


def test_jaeger():
    log_level = logging.DEBUG
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(asctime)s %(message)s', level=log_level)

    config = Config(
        config={  # usually read from some yaml config
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'local_agent': {
                # 注意这里是指定了JaegerAgent的host和port。
                # 根据官方建议为了保证数据可靠性，JaegerClient和JaegerAgent运行在同一台主机内，因此reporting_host填写为127.0.0.1。
                'reporting_host': '192.168.47.141',
                'reporting_port': 6831,
            },
            'logging': True,
        },
        # 这里填写应用名称
        service_name="mytest3",
        validate=True
    )

    # this call also sets opentracing.tracer
    tracer = config.initialize_tracer()

    span = construct_span(tracer)
    span.set_tag('key1', 'ABCDE')
    time.sleep(2)  # yield to IOLoop to flush the spans-https://github.com/jaegertracing/jaeger-client-python/issues/50
    tracer.close()  # flush any buffered spans


# how to instrument fastapi with promethues
def create_app() -> FastAPI:
    # from prometheus_client import make_asgi_app
    # ap = make_asgi_app()
    localapp = FastAPI()

    @localapp.get("/")
    def read_root():
        return "Hello World!"

    return localapp


def up_time() -> Callable[[Info], None]:
    metric = Counter(
        "up_time",
        "开机持续运行时间.",
        labelnames=("proc",)
    )
    sts_ = int(time.time())  # 秒为单位

    def instrumentation(info: Info) -> None:
        # 主进程的运行时间累计
        nonlocal sts_
        current = int(time.time())
        delta = current - sts_
        metric.labels('main').inc(delta)
        sts_ = current

        # 如果请求了具体的子进程运行时间
        pnames = info.request.query_params.getlist('v2v')
        if 0 <= len(pnames):
            for proc in pnames:
                metric.labels(proc).inc()

    return instrumentation


def cpu_rate() -> Callable[[Info], None]:
    metric = Gauge(
        "cpu_rate",
        "cpu占用率.",
        labelnames=("proc",)
    )

    def instrumentation(info: Info) -> None:
        cpu = psutil.cpu_percent()
        metric.labels('main').set(cpu)
        info.request.query_params.getlist('v2v')

    return instrumentation


def mem_rate() -> Callable[[Info], None]:
    metric = Gauge(
        "mem_rate",
        "内存占用率.",
        labelnames=("proc",)
    )

    def instrumentation(info: Info) -> None:
        mem = psutil.virtual_memory().percent
        metric.labels('main').set(mem)
        info.request.query_params.getlist('v2v')

    return instrumentation


def test_promethues_exporter():
    # reset_prometheus()
    localapp = create_app()
    # Instrumentator().instrument(localapp).expose(localapp)
    # reset_prometheus()
    instrumentator = Instrumentator(
        # excluded_handlers=[".*admin.*", "/metrics"],
    )
    instrumentator.add(up_time())
    instrumentator.add(cpu_rate())
    instrumentator.add(mem_rate())
    instrumentator.instrument(localapp).expose(localapp)

    # uvicorn.run(localapp, host='0.0.0.0', port=21880)

    client = TestClient(localapp)

    response = client.get("/metrics?v2v=rest&v2v=rtsp")
    print(response.headers.items())
    assert (
            "text/plain; version=0.0.4; charset=utf-8; charset=utf-8"
            not in response.headers.values()
    )


metrics_ = {}


def callback_set_metrics(params):
    """
    本函数响应子进程对所有监测指标的设置。
    把子进程上报的自己持续运行的时间等指标记录到一个数据结构中等备查。
    :param params: dict, {'proc': 'RTSP(0)-16380','up': 39.5527503490448, ...}, proc是固定的，除up外还可能增加其它键值。
    :return: dict, {'reply': True}
    """
    pname = params['proc']
    params.pop('proc', None)
    if pname in metrics_.keys():
        proc = metrics_[pname]
        proc.update(params)
        metrics_[pname] = proc
    else:
        metrics_[pname] = params
    return {'reply': True}


# 测试rtsp读流出现错误的问题
# 测试通过：sample_rtsp_frame能够支持3路流的打开同时播放抽帧。
def test_rtsp_process():
    """
    RTSP 进程取流总是出现错误，需要单元测试一下。
    """
    print("Initializng 3 workers")
    # vec_q_ = multiprocessing.Manager().Queue()
    # original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    # original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = multiprocessing.Pool(4)
    # signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        # res = pool.starmap_async(sample_rtsp_frame, [('rtsp://127.0.0.1/live', 1000)])
        res = pool.starmap_async(sample_rtsp_frame, [('rtsp://127.0.0.1/live', 1000),
                                                     ('rtsp://user:userpass@192.168.1.225:7554/person', 1000),
                                                     ('rtsp://user:userpass@192.168.1.225:7554/plc', 1000)])
        res.get(6000)  # Without the timeout this blocking call ignores all signals.
        print('-------------------OK--------------------------')
    except KeyboardInterrupt:
        print("-------------------Caught KeyboardInterrupt, terminating workers-----------------")
        pool.terminate()
    else:
        print("Normal termination")
        pool.close()
    pool.join()


class TestMain(unittest.TestCase):
    """
    Tests for `v2v` entrypoint.
    本测试案例启动整个v2v程序（前提需要启动Mock提供仿真接口，并启动obs的rtsp服务器）
    访问运行本案例的URL：
    https://IP:29080/docs，执行POST /subprocess，发送start/stop命令启停视频识别流水线。
    注意
    """

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_fun(self):
        log.log(f'case: test_fun-{metrics_}')
        a1 = {'up': 39.5527503490448, 'proc': 'RTSP(0)-16380'}
        callback_set_metrics(a1)
        b1 = {'up': 40.51580286026001, 'proc': 'AI(2)-10104'}
        callback_set_metrics(b1)
        b2 = {'up': 50.51580286026001, 'down': 1, 'proc': 'AI(2)-10104'}
        callback_set_metrics(b2)
        a2 = {'up': 60, 'proc': 'RTSP(0)-16380'}
        callback_set_metrics(a2)
        c1 = {'on': 0, 'proc': 'MQTT(1)-16380'}
        callback_set_metrics(c1)

    def test_MainContext(self):
        """Test core.main.MainContext."""
        log.log(f'case: test_MainContext.')
        # main()
        # pub_sub_pools()
        # fastapi_mainloop()
        # nvr_stream_func()
        # uploadfiles_withparams()
        # save_json()
        # test_url_statistics()
        # test_opencv_capture_timeout()
        # test_jaeger()
        # test_promethues_exporter()
        test_rtsp_process()


if __name__ == '__main__':
    # test_arg('a', 1, key3=3, key5=5, key4=4)
    # pool_handler()
    # uvicorn.run(app, host="0.0.0.0", port=21800)
    # cfg = config.load_json('./v2v.cfg')
    # print(cfg)
    # test_upload_img()
    # logging_guide.py
    # log.logger('he', 'hello')
    # uploadfiles()
    # uploadfile_withparams()
    # uploadfiles_withparams()
    # pools()
    # pub_sub_pools()
    # fsm = FSM()
    # fsm.set_status(2)
    # print(fsm.current_state_)
    # keyboard_interrupt()
    # main()
    unittest.main()
