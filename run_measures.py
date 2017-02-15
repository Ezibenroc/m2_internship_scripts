#! /usr/bin/env python3

import sys
import random
from subprocess import Popen, PIPE, DEVNULL
import re
from math import floor, sqrt
import csv
import os
import argparse
from collections import namedtuple
from topology import FatTreeParser

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

def run_all(global_csv_writer, local_csv_writer, args):
    for i in range(1, args.nb_runs+1):
        print('Iteration %d/%d' % (i, args.nb_runs))
        random.shuffle(args.fat_tree)
        for j, tree in enumerate(args.fat_tree):
            print('\tSub-iteration %d/%d' % (j+1, len(args.fat_tree)))
            tree.dump_topology_file('topo.xml')
            tree.dump_host_file('host.txt')
            global_result, local_result = run_and_parse('./topo.xml', './host.txt',
                    args.nb_proc, args.size)
            global_csv_writer.writerow((tree, tree.nb_roots(), args.nb_proc, args.size,
                global_result.time))
            for local_res in sorted(local_result):
                local_csv_writer.writerow((tree, tree.nb_roots(), args.nb_proc,
                    args.size, *local_res))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Experiment runner')
    parser.add_argument('-n', '--nb_runs', type=int,
            default=10, help='Number of experiments to perform.')
    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument('--size', type = int,
            required=True, help='Sizes of the matrix')
    parser.add_argument('--nb_proc', type = int,
            help='Number of processes to use.')
    required_named.add_argument('--global_csv', type = str,
            required=True, help='Path of the global CSV file.')
    required_named.add_argument('--local_csv', type = str,
            required=True, help='Path of the local CSV file.')
    parser.add_argument('--fat_tree', type = lambda s: FatTreeParser.parse(s),
            help='Description of the fat tree(s).')
    args = parser.parse_args()
    #check_params(args)
    with open(args.global_csv, 'w') as f_global:
        with open(args.local_csv, 'w') as f_local:
            global_writer = csv.writer(f_global)
            global_writer.writerow(('fat_tree', 'nb_roots', 'nb_proc', 'size', 'time'))
            local_writer = csv.writer(f_local)
            local_writer.writerow(('fat_tree', 'nb_roots', 'nb_proc', 'size', 'rank', 'communication_time', 'computation_time'))
            run_all(global_writer, local_writer, args)
