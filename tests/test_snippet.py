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
import time


from fastapi import FastAPI, File, UploadFile
import uvicorn

app = FastAPI()


@app.post("/files/")
async def create_file(file: bytes = File(...)):
    return {"file_size": len(file)}


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename}


work = [("A", 5), ("B", 2), ("C", 1), ("D", 3)]


def work_log(name, ts):
    print(f" Process {name} waiting {ts} seconds.")
    time.sleep(ts)
    print(f" Process {name} Finished.")


def pool_handler():
    p = Pool(2)
    p.starmap(work_log, [it for it in work])


def test_kwargs(**kwargs):
    for k, v in kwargs.items():
        print(k, v)


def test_arg(*args, **kwargs):
    test_kwargs(**kwargs)
    for it in args:
        print(it)
    return True


if __name__ == '__main__':
    # pool_handler()
    # test_arg('a', 1, key3=3, key5=5, key4=4)
    uvicorn.run(app, host="0.0.0.0", port=21800)
