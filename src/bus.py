import os

DEFAULT_POLLING_TIMEOUT = 0.02
EBUS_TOPIC_RTSP = 'rtsp'


def send_cmd(bus, topic, msg):
    try:
        ret = False
        while bus[topic]:
            pass
    except KeyError as err:
        bus['rtsp'] = msg
        print(f'Send-->{msg}')
    finally:
        return ret


def recv_cmd(bus, topic):
    try:
        msg = None
        pid = os.getpid()
        msg = bus.pop(topic)
        print(f'C[{pid}] got events: {msg}')
    except KeyError as ke:
        pass
    finally:
        return msg
