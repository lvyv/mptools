from puresnmp import get
import csv
from concurrent.futures import ThreadPoolExecutor
import schedule
import time
from socket import gethostbyname
from atomicInteger import AtomicInteger

executor = ThreadPoolExecutor(max_workers=24)
scheduleExecutor = ThreadPoolExecutor(max_workers=1)
scheduleInterval = 10
scheduleRunning = True


def schedule_job():
    load_num_to_print = loadNum.get_and_set(0)
    success_num_to_print = successNum.get_and_set(0)
    failed_num_to_print = failedNum.get_and_set(0)
    data_in_process = dataInProcess.value
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) +
          " loadNum:" + str(load_num_to_print)+" successNum:" + str(success_num_to_print) +
          " failedNum:" + str(failed_num_to_print) +
          " pre " + str(scheduleInterval) + " second")
    print("dataInProcess:" + str(data_in_process) + " In total.")


schedule.every(scheduleInterval).seconds.do(schedule_job)

loadNum = AtomicInteger(0)
successNum = AtomicInteger(0)
failedNum = AtomicInteger(0)
dataInProcess = AtomicInteger(0)


ip = '127.0.0.1'
# ip = 'snmp.live.gambitcommunications.com'
community = 'public'
# oid = '.1.3.6.1.2.1.1.1.0'


def snmp_get(inner_oid):
    # result = get(ip, community, inner_oid).decode()
    result = get(gethostbyname(ip), community, inner_oid)
    return result
    # print(result)


def get_snmp_from_csv():
    with open('snmpnorthallpoint.csv', 'r', encoding='UTF-8') as f:
        reader = csv.reader(f)
        # for i in range(8):
        #     row = reader.next()
        #     if row is not None:
        #         print(row)
        i = 0
        for row in reader:
            # print(row)
            executor.submit(snmp_get, row[4]).add_done_callback(snmp_get_callback)
            # snmp_get(row[4])
            loadNum.inc()
            dataInProcess.inc()
            i = i+1
            if i % 1000 == 0:
                print("request:"+str(i))
            if i >= 50:
                break
        print("request:" + str(i))


def snmp_get_callback(future):
    try:
        res = future.result()
        successNum.inc()
    except Exception as e:
        failedNum.inc()
    finally:
        dataInProcess.dec()


def async_do_schedule_job():
    scheduleExecutor.submit(do_schedule_job)
    return scheduleExecutor


def do_schedule_job():
    while scheduleRunning:
        schedule.run_pending()
        time.sleep(1)


def set_schedule_running(status):
    global scheduleRunning
    scheduleRunning = status

