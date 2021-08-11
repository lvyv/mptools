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

from multiprocessing import Pool

from time import time, sleep
from utils import bus, comn, config
from core.procworker import ProcWorker

import requests
import cv2
import io
import imutils
from imutils.video import VideoStream
from matplotlib import pyplot as plt

# ----fastapi-----

from fastapi import FastAPI, File, UploadFile
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
    time.sleep(ts)
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
    vs_ = VideoStream('rtsp://192.168.1.4/live').start()
    inteval = 1
    while True:
        sleep(inteval - time() % inteval)  # 休眠采样间隔的时间
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

    # vp = pic['channel']
    # name = vp['name']
    # rest = vp['micro_service']
    # files = {'upfile': (name, image_data, 'image/png')}
    # resp = requests.post(rest, files=files, verify=False)  # data=image_data)
    # self.out_q_.put(resp.content)


if __name__ == '__main__':
    # test_arg('a', 1, key3=3, key5=5, key4=4)
    # pool_handler()
    # uvicorn.run(app, host="0.0.0.0", port=21800)
    # cfg = config.load_json('./v2v.cfg')
    # print(cfg)
    test_upload_img()
