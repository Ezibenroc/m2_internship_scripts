#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
from math import floor, sqrt
import csv
import os
from collections import namedtuple

def run_algorithm(topo_file, host_file, number_processes, msg_size):
    args = ['smpirun', '--cfg=smpi/running-power:6217956542.969', '-np', str(number_processes), '-hostfile', host_file, '-platform', topo_file, './broadcast', str(msg_size)]
    p = Popen(args, stdout = PIPE, stderr = DEVNULL)
    output = p.communicate()
    assert p.wait() == 0
    return output[0]

float_string = '[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'
global_time_string = 'number_procs\s*:\s*(?P<nb_proc>{0})\s*\|\s*msg_size\s*:\s*(?P<msg_size>{0})\s*\|\s*time\s*:\s*(?P<time>{0})\s*seconds\n'.format(float_string)
regex = re.compile(global_time_string.encode())

def run_and_parse(topo_file, host_file, number_processes, msg_size):
    output_str = run_algorithm(topo_file, host_file, number_processes, msg_size)
    match = regex.match(output_str)
    global_result = namedtuple('global_result', ['nb_proc', 'msg_size', 'time'])(int(match.group('nb_proc')), int(match.group('msg_size')), float(match.group('time')))
    return global_result

def run_all(csv_writer, msg_sizes, number_procs):
    i = 0
    while True:
        print('Iteration %d' % i)
        i += 1
        try:
            for size in msg_sizes:
                print('\t%d size' % size)
                for nb_proc in number_procs:
                    print('\t\t%d processors' % nb_proc)
                    global_result = run_and_parse('./cluster_1600.xml', './hostfile_1600.txt', nb_proc, size)
                    csv_writer.writerow(global_result)
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Syntax: %s <global result file> <message sizes> <numbers of processors>' % sys.argv[0])
        sys.exit(1)
    msg_sizes = [int(n) for n in sys.argv[2].split(',')]
    number_procs = [int(n) for n in sys.argv[3].split(',')]
    print('Will use messages of size      : %s' % msg_sizes)
    print('Will use numbers of processors : %s' % number_procs)
    with open(sys.argv[1], 'w') as f_global:
        writer = csv.writer(f_global)
        writer.writerow(('nb_proc', 'msg_size', 'time'))
        run_all(writer, msg_sizes, number_procs)
