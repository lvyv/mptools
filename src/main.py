import multiprocessing
import random
from time import time, sleep
from rtsp import proc_rtsp
import bus

if __name__ == '__main__':

    INTERVAL = 1
    PROC_RTSP_CNT = 2

    mgr = multiprocessing.Manager()
    pic_que = mgr.Queue()
    vec_que = mgr.Queue()
    ebs = mgr.dict()

    pool_rtsp = multiprocessing.Pool(processes=PROC_RTSP_CNT)
    pool_rtsp.starmap_async(proc_rtsp, [(1, ebs, pic_que), (2, ebs, vec_que)])

    while True:
        sleep(INTERVAL - time() % INTERVAL)
        numb = random.randrange(1, 4)
        bus.send_cmd(ebs, bus.EBUS_TOPIC_RTSP, numb)

    pool.close()
    pool.join()
