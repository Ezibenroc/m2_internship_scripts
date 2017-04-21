#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
import csv
from math import log, floor
from itertools import product

def measure_page_faults(shared, size, mem_access):
    p = Popen(['/usr/bin/time', '-f', '%S %U %F %R', './page_faults', str(int(shared)), str(size), str(int(mem_access))],
            stdout = DEVNULL, stderr = PIPE)
    output = p.communicate()[1].decode('ascii')
    assert p.wait() == 0
    sys_time, usr_time, major, minor = output.split()
    sys_time = float(sys_time)
    usr_time = float(usr_time)
    major = int(major)
    minor = int(minor)
    assert major == 0
    return sys_time, usr_time, minor

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
        csv_writer.writerow(('shared', 'size', 'mem_access', 'system_time', 'user_time', 'nb_page_faults'))
        exp_id = 0
        for exp in range(nb_exp):
            print('Experiment %d/%d' % (exp+1, nb_exp))
            random.shuffle(experiments)
            size = random.randint(1, max_size)
            for shared, mem_access in experiments:
                sys_time, usr_time, nb_page_faults = measure_page_faults(shared, size, mem_access)
                csv_writer.writerow((shared, size, mem_access, sys_time, usr_time, nb_page_faults))
