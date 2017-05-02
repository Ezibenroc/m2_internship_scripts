#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
import csv
from math import log, floor
from itertools import product
from page_faults import measure_page_faults

def noisy(n):
    eps = random.randint(int(-n/10), int(n/10))
    return n+eps

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Syntax: %s <nb_exp> <max_size> <CSV file>')
        sys.exit(1)
    nb_exp = int(sys.argv[1])
    max_size = int(sys.argv[2])
    sizes = [2**n for n in range(20, floor(log(max_size, 2))+1)]
    file_name = sys.argv[3]
    experiments = list(product([True, False], sizes))
    with open(file_name, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(('shared', 'size', 'mem_access', 'system_time', 'user_time', 'nb_page_faults', 'cpu_utilization'))
        exp_id = 0
        for exp in range(nb_exp):
            print('experiment %d/%d' % (exp+1, nb_exp))
            random.shuffle(experiments)
            size = random.randint(1, max_size)
            for i, (mem_access, base_size) in enumerate(experiments):
                print('\tsub %d/%d' % (i+1, len(experiments)))
                size = noisy(base_size)
                sys_time, usr_time, nb_page_faults, cpu_utilization = measure_page_faults(True, size, mem_access)
                csv_writer.writerow((True, size, mem_access, sys_time, usr_time, nb_page_faults, cpu_utilization))
