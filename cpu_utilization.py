#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
import csv
from math import log, floor
from itertools import product
from page_faults import measure_page_faults, compile_exec

MAX_ITER = 4

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Syntax: %s <nb_exp> <max_size> <CSV file>')
        sys.exit(1)
    compile_exec()
    nb_exp = int(sys.argv[1])
    max_size = int(sys.argv[2])
    file_name = sys.argv[3]
    experiments = list(product(range(1, MAX_ITER+1), [True, False]))
    with open(file_name, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(('size', 'mem_access', 'hugepage', 'system_time', 'user_time', 'total_time', 'nb_page_faults', 'cpu_utilization', 'memory_size'))
        exp_id = 0
        for exp in range(nb_exp):
            experiments = list(experiments)
            random.shuffle(experiments)
            print('Experiment %d/%d' % (exp+1, nb_exp))
            size = random.randint(1, max_size)
            for nb_iter, hugepage in experiments:
                sys_time, usr_time, total_time, nb_page_faults, cpu_utilization, memory_size = measure_page_faults(True, size, nb_iter, hugepage)
                csv_writer.writerow((size, nb_iter, hugepage, sys_time, usr_time, total_time, nb_page_faults, cpu_utilization, memory_size))
