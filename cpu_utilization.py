#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
import csv
from math import log, floor
from itertools import product
from page_faults import measure_page_faults

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Syntax: %s <nb_exp> <max_size> <CSV file>')
        sys.exit(1)
    nb_exp = int(sys.argv[1])
    max_size = int(sys.argv[2])
    file_name = sys.argv[3]
    with open(file_name, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(('shared', 'size', 'mem_access', 'system_time', 'user_time', 'nb_page_faults', 'cpu_utilization'))
        exp_id = 0
        for exp in range(nb_exp):
            print('Experiment %d/%d' % (exp+1, nb_exp))
            size = random.randint(1, max_size)
            sys_time, usr_time, nb_page_faults, cpu_utilization = measure_page_faults(True, size, True)
            csv_writer.writerow((True, size, True, sys_time, usr_time, nb_page_faults, cpu_utilization))
