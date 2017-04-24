#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
import csv
from math import log, floor
from page_faults import measure_page_faults

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print('Syntax: %s <nb_exp> <size> <max_access> <CSV file>')
        sys.exit(1)
    nb_exp = int(sys.argv[1])
    size = int(sys.argv[2])
    max_access = int(sys.argv[3])
    file_name = sys.argv[4]
    with open(file_name, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(('size', 'nb_access', 'system_time', 'user_time', 'nb_page_faults'))
        exp_id = 0
        for exp in range(nb_exp):
            print('Experiment %d/%d' % (exp+1, nb_exp))
            nb_access = random.randint(0, max_access)
            sys_time, usr_time, nb_page_faults = measure_page_faults(True, size, nb_access)
            csv_writer.writerow((size, nb_access, sys_time, usr_time, nb_page_faults))
