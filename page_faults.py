#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
import csv
import psutil
from math import log, floor
from itertools import product
import time

def measure_page_faults(shared, size, mem_access):
    initial_free_memory = psutil.virtual_memory().available
    memory_size = 0
    p = Popen(['/usr/bin/time', '-f', '%S %U %F %R %P', './page_faults', str(int(shared)), str(size), str(int(mem_access))],
            stdout = DEVNULL, stderr = PIPE)
    sleep_time = 0.05
    while p.poll() is None:
        memory_size = max(memory_size, initial_free_memory-psutil.virtual_memory().available)
        time.sleep(sleep_time)
        sleep_time = max(1, sleep_time*2)
    output = p.communicate()[1].decode('ascii')
    assert p.wait() == 0
    sys_time, usr_time, major, minor, cpu_percent = output.split()
    sys_time = float(sys_time)
    usr_time = float(usr_time)
    major = int(major)
    minor = int(minor)
    cpu_utilization = cpu_percent[:-1]
    if cpu_utilization == '?':
        cpu_utilization = 'N/A'
    else:
        cpu_utilization = float(cpu_utilization)/100
    assert major == 0
    return sys_time, usr_time, minor, cpu_utilization, memory_size

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Syntax: %s <nb_exp> <max_size> <CSV file>')
        sys.exit(1)
    nb_exp = int(sys.argv[1])
    max_size = int(sys.argv[2])
    file_name = sys.argv[3]
    experiments = list(product([True, False], [True, False]))
    with open(file_name, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(('shared', 'size', 'mem_access', 'system_time', 'user_time', 'nb_page_faults', 'cpu_utilization', 'memory_size'))
        exp_id = 0
        for exp in range(nb_exp):
            print('Experiment %d/%d' % (exp+1, nb_exp))
            random.shuffle(experiments)
            size = random.randint(1, max_size)
            for shared, mem_access in experiments:
                sys_time, usr_time, nb_page_faults, cpu_utilization, memory_size = measure_page_faults(shared, size, mem_access)
                csv_writer.writerow((shared, size, mem_access, sys_time, usr_time, nb_page_faults, cpu_utilization, memory_size))
