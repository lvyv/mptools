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

import os
import signal
from multiprocessing import Pool
from os import listdir
from os.path import isfile, join
from time import time, sleep
from random import randrange
from utils import bus, comn, config
from utils import log
from core.procworker import ProcWorker

import sys
import json
import zmq
import random
import requests
import cv2
import io
import imutils
import base64
import multiprocessing
import os
import signal
import time
from imutils.video import VideoStream
from matplotlib import pyplot as plt

# ----fastapi-----
from fastapi import FastAPI, File, UploadFile
from fastapi_utils.tasks import repeat_every
import uvicorn


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
    mypath = '../src/mock/local/'
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    files = [('files', (replace_non_ascii(name), open(f'{mypath}{name}', 'rb'))) for name in onlyfiles]
    payload = {'jsos': '{"key1":1, "key2":2}'}
    requests.post(rest, files=files, data=payload, verify=False)  # data=image_data)


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
        socket.send_string(f"{message}, World")     # noqa
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
        socket.send_string(f"send Hello({request}) ")   # noqa
        # socket.send_string(f"send hello twice")
        #  Get the reply.
        message = socket.recv()
        print(f"{name}, Received reply {request} [ {message} ]")


def pools():
    try:
        # cs = center()
        # sleep(1)
        # bbp = beeper()
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        p = Pool(2)
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

    else:
        p.close()
        p.join()


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
            socket.send_string(msg)     # noqa
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
            st = socket.recv_string()   # noqa
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
    else:
        p.close()
        print("Normal termination")
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
        print("In a worker process", os.getpid())
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
        print("Starting 2 jobs of 5 seconds each")
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
        child_process_cli_.send_string('hello---')
        print(child_process_cli_.recv())


def run_fastapi(name):
    global child_process_cli_
    context = zmq.Context()
    #  Socket to talk to server
    print("Connecting to hello world server...")
    socket = context.socket(zmq.REQ)
    socket.connect(ipc_address_)
    child_process_cli_ = socket
    uvicorn.run(app, host="0.0.0.0", port=21800)
    print('going to exit...')
    socket.send_string('exit...')


def fastapi_main():
    dp = multiprocessing.Process(target=run_fastapi, args=('fastapi', ))
    dp.daemon = True
    dp.start()
    return dp


def fastapi_mainloop():
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(ipc_address_)
        dp = fastapi_main()
        while True:
            msg = socket.recv()
            print(f'main:{msg}')
            socket.send_string('back')
    except KeyboardInterrupt:
        print('----KeyboardInterrupt----')
        dp.terminate()

    print('finally')


def nvr_stream_func():
    cap = cv2.VideoCapture('rtsp://127.0.0.1/live')
    print(f'fps: {cap.get(cv2.cv2.CAP_PROP_FPS)}')
    opened = cap.isOpened()
    if opened:
        while True:
            try:
                ret, frame = cap.read()
                height, width, channels = frame.shape
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

    # try:
    #     url = 'rtsp://127.0.0.1/live'
    #     start = time.time()
    #     vs = VideoStream(src=url).start()
    #     end = time.time()
    #     print(end - start)
    # except BaseException as be:
    #     print(be)
    #     pass
    # while True:
    #     try:
    #         frame = vs.read()
    #         # frame = imutils.resize(frame, width=680)
    #         cv2.imshow('NVR realtime', frame)
    #         key = cv2.waitKey(1) & 0xFF
    #         if key == ord('q'):
    #             break
    #     except cv2.error as cve:
    #         print(f'in loop error: {cve}')

    # buf = io.BytesIO()
    # plt.imsave(buf, frame, format='png')
    # image_data = buf.getvalue()
    # image_data = base64.b64encode(image_data)
    # outfile = open(f'{target}{prs["presetid"]}', 'wb')
    # outfile.write(image_data)
    # outfile.close()

    # vs.stop()
    # vs.release()
    pass


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

    def test_MainContext(self):
        """Test core.main.MainContext."""
        # main()
        # pub_sub_pools()
        # fastapi_mainloop()
        nvr_stream_func()


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
