#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `mptools` package."""
import multiprocessing
from time import time, sleep
import random


def proc_rtsp(name, sq, dq=None):
    while True:
        ts = random.randrange(1, 5)
        sleep(ts)
        print(f'{name}-{sq}--{ts}')
        if ts == 4:
            sq['RPL'] = ['5s passed.']


if __name__ == '__main__':
    pool = multiprocessing.Pool(processes=2)
    mgr = multiprocessing.Manager()
    signal_que = mgr.dict()
    pic_que = mgr.Queue()
    vec_que = mgr.Queue()
    pool.starmap_async(proc_rtsp, [(1, signal_que, pic_que), (2, signal_que, vec_que)])

    sleep(1)
    signal_que['CMD'] = ['hello']

    while True:
        sleep(3 - time() % 3)
        for it in signal_que:
            print(f'--->{it}')

    pool.close()
    pool.join()

