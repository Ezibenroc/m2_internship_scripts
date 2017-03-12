#! /usr/bin/env python3
import sys
import csv
import re
import random
from subprocess import Popen, PIPE, DEVNULL

BLUE_STR = '\033[1m\033[94m'
GREEN_STR = '\033[1m\033[92m'
RED_STR = '\033[1m\033[91m'
END_STR = '\033[0m'

def print_color(msg, color):
    print('%s%s%s' % (color, msg, END_STR))

def print_blue(msg):
    print_color(msg, BLUE_STR)

def print_green(msg):
    print_color(msg, GREEN_STR)

def error(msg):
    sys.stderr.write('%sERROR: %s%s\n' % (RED_STR, msg, END_STR))
    sys.exit(1)

def run_command(args):
    print_blue('%s' % ' '.join(args))
    process = Popen(args, stdout=PIPE, stderr=DEVNULL)
    output = process.communicate()
    if process.wait() != 0:
        error('with command: %s' % ' '.join(args))
    return output[0]

def run(size, smpi_sample, smpi_malloc, nb_proc=64):
    args = ['smpirun', '--cfg=smpi/running-power:6217956542.969', '--cfg=smpi/privatize-global-variables:yes', '-np', str(nb_proc), '-hostfile', 'hostfile_64.txt', '-platform', 'cluster_fat_tree_64.xml', './matmul', str(size), str(smpi_sample), str(smpi_malloc)]
    result = run_command(args)
    return float(result)

def run_exp(csv_writer, size):
    values = [(0, 0), (0, 1), (1, 0), (1, 1)]
    random.shuffle(values)
    for smpi_sample, smpi_malloc in values:
        time = run(size, smpi_sample, smpi_malloc)
        csv_writer.writerow((time, size, smpi_sample, smpi_malloc))

def run_all(csv_file, nb_exp, size=4000):
    with open(csv_file, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(('time', 'size', 'smpi_sample', 'smpi_malloc'))
        for n in range(nb_exp):
            print('%d/%d' % (n+1, nb_exp))
            run_exp(csv_writer, size)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        error('Syntax: %s <nb_exp> <csv_file>' % sys.argv[0])
    try:
        nb_exp = int(sys.argv[1])
        assert nb_exp > 0
    except (ValueError, AssertionError):
        error('Argument nb_exp must be a positive integer.')
    run_all(sys.argv[2], nb_exp)
