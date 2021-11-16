from snmpUtils import snmp_get, get_snmp_from_csv, async_do_schedule_job, set_schedule_running
from concurrent.futures import ThreadPoolExecutor
import time

executor = ThreadPoolExecutor(max_workers=1)
poll_period = 5000


def run():
    previous_poll_time = 0
    while True:
        current_time = time.time() * 1000
        if previous_poll_time + poll_period < current_time:
            get_snmp_from_csv()
            previous_poll_time = current_time
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        time.sleep(.01)


if __name__ == '__main__':
    # snmp_get('.1.3.6.1.2.1.1.1.0')
    # get_snmp_from_csv()
    scheduleExecutor = async_do_schedule_job()
    # run()
    try:
        run()
    except:
        print("stopping ... ")
        set_schedule_running(False)
