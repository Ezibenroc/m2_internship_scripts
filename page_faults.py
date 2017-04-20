#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
import csv
from math import log, floor
from itertools import product

def measure_page_faults(shared, size, mem_access):
    p = Popen(['/usr/bin/time', '-f', '%F %R', './page_faults', str(int(shared)), str(size), str(int(mem_access))],
            stdout = DEVNULL, stderr = PIPE)
    output = p.communicate()[1].decode('ascii')
    assert p.wait() == 0
    major, minor = (int(n) for n in output.split(' '))
    assert major == 0
    return minor

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
        csv_writer.writerow(('shared', 'size', 'mem_access', 'nb_page_faults'))
        exp_id = 0
        for exp in range(nb_exp):
            print('Experiment %d/%d' % (exp+1, nb_exp))
            random.shuffle(experiments)
            for shared, mem_access in experiments:
                size = random.randint(1, max_size)
                nb_page_faults = measure_page_faults(shared, size, mem_access)
                csv_writer.writerow((shared, size, mem_access, nb_page_faults))
