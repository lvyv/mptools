import bus
from time import time, sleep

INTERVAL = 0.5  # seconds


def proc_rtsp(name, ebs, dq=None):
    while True:
        sleep(INTERVAL - time() % INTERVAL)
        try:
            msg = bus.recv_cmd(ebs, bus.EBUS_TOPIC_RTSP)
        except KeyError as err:
            print(err, msg)
        finally:
            pass

