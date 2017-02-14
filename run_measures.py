#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
from math import floor, sqrt
import csv
import os
from collections import namedtuple
from topology import FatTree

MATRIX_SIZE = 6600
NB_PROCS = 1089

def run_algorithm(topo_file, host_file, number_processes, matrix_size):
    args = ['smpirun', '--cfg=smpi/running-power:6217956542.969', '-np', str(number_processes), '-hostfile', host_file, '-platform', topo_file, './matmul', str(matrix_size)]
    p = Popen(args, stdout = PIPE, stderr = DEVNULL)
    output = p.communicate()
    assert p.wait() == 0
    return output[0]

float_string = '[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'
local_time_string = 'rank\s*:\s*(?P<rank>{0})\s*\|\s*communication_time\s*:\s*(?P<communication_time>{0})\s*\|\s*computation_time\s*:\s*(?P<computation_time>{0})\n'.format(float_string)
global_time_string = 'number_procs\s*:\s*(?P<nb_proc>{0})\s*\|\s*matrix_size\s*:\s*(?P<matrix_size>{0})\s*\|\s*time\s*:\s*(?P<time>{0})\s*seconds\n'.format(float_string)
whole_string = '(?P<local>(%s)*)(?P<global>%s)' % (local_time_string, global_time_string)
local_regex = re.compile(local_time_string.encode())
regex = re.compile(whole_string.encode())

def run_and_parse(topo_file, host_file, number_processes, matrix_size):
    output_str = run_algorithm(topo_file, host_file, number_processes, matrix_size)
    match = regex.match(output_str)
    global_result = namedtuple('global_result', ['nb_proc', 'matrix_size', 'time'])(int(match.group('nb_proc')), int(match.group('matrix_size')), float(match.group('time')))
    local_result = []
    local_tuple = namedtuple('local_result', ['rank', 'communication_time', 'computation_time'])
    for local in local_regex.finditer(match.group('local')): # would be very nice if we could explore the regex hierarchy instead of having to do another match...
        local_result.append(local_tuple(int(local.group('rank')), float(local.group('communication_time')), float(local.group('computation_time'))))
    return global_result, local_result

def check(matrix_sizes, number_procs):
    for nb_proc in number_procs:
        sqrt_proc = int(sqrt(nb_proc))
        if sqrt_proc*sqrt_proc != nb_proc:
            print('Error: %d is not a square.' % nb_proc)
            sys.exit(1)
        for size in matrix_sizes:
            if size%sqrt_proc != 0:
                print('Error: sqrt(%d) does not divide %d.' % (nb_proc, size))
                sys.exit(1)

def run_all(global_csv_writer, local_csv_writer, nb_iter):
    for i in range(1, nb_iter+1):
        print('Iteration %d/%d' % (i, nb_iter))
        values = list(range(1, 25))
        random.shuffle(values)
        for j, nb_roots in enumerate(values):
            print('\tSub-iteration %d/%d' % (j+1, len(values)))
            tree = FatTree([24, 48], [1, nb_roots], [1, 1])
            tree.dump_topology_file('topo.xml')
            tree.dump_host_file('host.txt')
            global_result, local_result = run_and_parse('./topo.xml', './host.txt', NB_PROCS, MATRIX_SIZE)
            global_csv_writer.writerow((nb_roots, global_result.time))
            for local_res in sorted(local_result):
                local_csv_writer.writerow((nb_roots, *local_res))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.stderr.write('Syntax: %s <global csv> <local csv> <nb_iterations>\n' % sys.argv[0])
        sys.exit(1)
    nb_iter = int(sys.argv[3])
    with open(sys.argv[1], 'w') as f_global:
        with open(sys.argv[2], 'w') as f_local:
            global_writer = csv.writer(f_global)
            global_writer.writerow(('nb_root_switches', 'time'))
            local_writer = csv.writer(f_local)
            local_writer.writerow(('nb_root_switches', 'rank', 'communication_time', 'computation_time'))
            run_all(global_writer, local_writer, nb_iter)
