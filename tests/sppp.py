import multiprocessing
import time

manager = multiprocessing.Manager()
evt_que = manager.list()


def proc_rtsp(x):
    print(x)
    at = time.time()
    evt_que.append(f'picture #{at}')  # each process should got a files reference.
