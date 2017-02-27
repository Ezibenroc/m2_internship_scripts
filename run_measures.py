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

HPL_dat_text = '''HPLinpack benchmark input file
Innovative Computing Laboratory, University of Tennessee
HPL.out      output file name (if any)
6            device out (6=stdout,7=stderr,file)
1            # of problems sizes (N)
{size}       # default: 29 30 34 35  Ns
1            # default: 1            # of NBs
120          # 1 2 3 4      NBs
0            PMAP process mapping (0=Row-,1=Column-major)
1            # of process grids (P x Q)
{P}          Ps
{Q}          Qs
16.0         threshold
3            # of panel fact
0 1 2        PFACTs (0=left, 1=Crout, 2=Right)
2            # of recursive stopping criterium
2 4          NBMINs (>= 1)
1            # of panels in recursion
2            NDIVs
3            # of recursive panel fact.
0 1 2        RFACTs (0=left, 1=Crout, 2=Right)
1            # of broadcast
0            BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM)
1            # of lookahead depth
0            DEPTHs (>=0)
2            SWAP (0=bin-exch,1=long,2=mix)
64           swapping threshold
0            L1 in (0=transposed,1=no-transposed) form
0            U  in (0=transposed,1=no-transposed) form
1            Equilibration (0=no,1=yes)
8            memory alignment in double (> 0)
'''

class AbstractRunner:

    topo_file = 'topo.xml'
    host_file = 'host.txt'

    def __init__(self, topologies, size, nb_proc, nb_runs, csv_file_name):
        self.topologies = topologies
        self.size = size
        self.nb_proc = nb_proc
        self.nb_runs = nb_runs
        self.csv_file_name = csv_file_name
        self.default_args = ['smpirun', '--cfg=smpi/running-power:6217956542.969', '--cfg=smpi/privatize-global-variables:yes', '-np', str(self.nb_proc),
                '-hostfile', self.host_file, '-platform', self.topo_file]

    def check_params(self):
        topo_min_nodes = min(self.topologies, key = lambda t: t.nb_nodes())
        min_nodes = topo_min_nodes.nb_nodes()
        if min_nodes < self.nb_proc:
            print('Error: more processes than nodes for at least one of the topologies (topology %s has  %d nodes, asked for %d processes).' % (topo_min_nodes, min_nodes, self.nb_proc))
            sys.exit(1)

    def prequel(self):
        self.check_params()
        self.csv_file = open(self.csv_file_name, 'w')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(('topology', 'nb_roots', 'nb_proc', 'size', 'time', 'Gflops'))

    def _run(self):
        with open('experiment.log', 'w') as f_log:
            p = Popen(self.args, stdout = PIPE, stderr = f_log)
            output = p.communicate()
            process_exit_code = p.wait()
        assert process_exit_code == 0
        return output[0]

    def run(self): # return the time (in second) and the speed (in Gflops)
        raise NotImplementedError()

    def sequel(self):
        self.csv_file.close()

    def run_all(self):
        self.prequel()
        for i in range(1, self.nb_runs+1):
            print('Iteration %d/%d' % (i, args.nb_runs))
            random.shuffle(self.topologies)
            for j, topo in enumerate(self.topologies):
                self.current_topo = topo
                print('\tSub-iteration %d/%d' % (j+1, len(self.topologies)))
                topo.dump_topology_file(self.topo_file)
                topo.dump_host_file(self.host_file)
                time, flops = self.run()
                self.csv_writer.writerow((topo, topo.nb_roots(), self.nb_proc, self.size, time, flops))
        self.sequel()

class MatrixProduct(AbstractRunner):

    float_string = '[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'
    local_time_string = 'rank\s*:\s*(?P<rank>{0})\s*\|\s*communication_time\s*:\s*(?P<communication_time>{0})\s*\|\s*computation_time\s*:\s*(?P<computation_time>{0})\n'.format(float_string)
    global_time_string = 'number_procs\s*:\s*(?P<nb_proc>{0})\s*\|\s*matrix_size\s*:\s*(?P<matrix_size>{0})\s*\|\s*time\s*:\s*(?P<time>{0})\s*seconds\n'.format(float_string)
    whole_string = '(?P<local>(%s)*)(?P<global>%s)' % (local_time_string, global_time_string)
    local_regex = re.compile(local_time_string.encode())
    regex = re.compile(whole_string.encode())

    def __init__(self, topologies, size, nb_proc, nb_runs, csv_file_name, local_csv_file_name):
        super().__init__(topologies, size, nb_proc, nb_runs, csv_file_name)
        self.local_csv_file_name = local_csv_file_name
        self.args = self.default_args + ['./matmul', str(self.size)]

    def check_params(self):
        super().check_params()
        sqrt_proc = int(sqrt(self.nb_proc))
        if sqrt_proc*sqrt_proc != self.nb_proc:
            print('Error: %d is not a square.' % self.nb_proc)
            sys.exit(1)
        if self.size%sqrt_proc != 0:
            print('Error: sqrt(%d) does not divide %d.' % (self.nb_proc, self.size))
            sys.exit(1)

    def prequel(self):
        super().prequel()
        self.local_csv_file = open(self.local_csv_file_name, 'w')
        self.local_csv_writer = csv.writer(self.local_csv_file)
        self.local_csv_writer.writerow(('topology', 'nb_roots', 'nb_proc', 'size', 'rank', 'communication_time', 'computation_time'))

    def run(self):
        output_str = self._run()
        match = self.regex.match(output_str)
        for local in self.local_regex.finditer(match.group('local')): # would be very nice if we could explore the regex hierarchy instead of having to do another match...
            self.local_csv_writer.writerow((self.current_topo, self.current_topo.nb_roots(), self.nb_proc, self.size,
                int(local.group('rank')), float(local.group('communication_time')), float(local.group('computation_time'))))
        time = float(match.group('time'))
        flops = 2*self.size**3 / (time*10**9)
        return time, flops

    def sequel(self):
        super().sequel()
        self.local_csv_file.close()

def primes(n):
# From http://stackoverflow.com/questions/16996217/prime-factorization-list
    primfac = []
    d = 2
    while d*d <= n:
        while (n % d) == 0:
            primfac.append(d)  # supposing you want multiple factors repeated
            n //= d
        d += 1
    if n > 1:
       primfac.append(n)
    return primfac

class HPL(AbstractRunner):

    HPL_file_name = 'HPL.dat'

    def __init__(self, *args):
        super().__init__(*args)
        self.args = self.default_args + ['../hpl-2.2/bin/SMPI/xhpl']
        self.index = 0

    def get_P_Q(self):
        factors = primes(self.nb_proc)
        P, Q = 1, 1
        for fact in factors:
            if P < Q:
                P *= fact
            else:
                Q *= fact
        return P, Q

    def prequel(self):
        super().prequel()
        P, Q = self.get_P_Q()
        with open(self.HPL_file_name, 'w') as f:
            f.write(HPL_dat_text.format(P=P, Q=Q, size=self.size))

    def run(self): # we parse the ugly output...
        output_str = self._run()
        self.index += 1
        output = [sub.split() for sub in output_str.split(b'\n')]
        for i, sub in enumerate(output):
            if b'Time' in sub and b'Gflops' in sub:
                break
        sub = output[i+2]
        error = False
        time = float(sub[-2])
        flops = float(sub[-1])
        return time, flops

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Experiment runner')
    parser.add_argument('-n', '--nb_runs', type=int,
            default=10, help='Number of experiments to perform.')
    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument('--size', type = int,
            required=True, help='Sizes of the problem')
    required_named.add_argument('--nb_proc', type = int,
            required=True, help='Number of processes to use.')
    required_named.add_argument('--global_csv', type = str,
            required=True, help='Path of the global CSV file.')
    parser.add_argument('--local_csv', type = str,
            help='Path of the local CSV file.')
    required_named.add_argument('--fat_tree', type = lambda s: FatTreeParser.parse(s),
            required=True, help='Description of the fat tree(s).')
    required_named.add_argument('--experiment',
            required=True, help='The type of experiment to run.',
            choices = ['matrix_product', 'HPL'])
    args = parser.parse_args()
    if args.experiment == 'matrix_product':
        if args.local_csv == None:
            sys.stderr.write('Error: no local CSV file given.\n')
            sys.exit(1)
        runner = MatrixProduct(args.fat_tree, args.size, args.nb_proc, args.nb_runs, args.global_csv, args.local_csv)
    elif args.experiment == 'HPL':
        if args.local_csv is not None:
            sys.stderr.write('Error: no need for a local CSV file.\n')
            sys.exit(1)
        runner = HPL(args.fat_tree, args.size, args.nb_proc, args.nb_runs, args.global_csv)
    else:
        assert False # unreachable
    runner.run_all()
