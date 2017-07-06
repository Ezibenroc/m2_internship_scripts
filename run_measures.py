#! /usr/bin/env python3

import sys
import os
import time
import random
from subprocess import Popen, PIPE, check_output, CalledProcessError
import re
from math import sqrt
import csv
import argparse
import itertools
import psutil
from collections import namedtuple
from memstat import get_memory_usage
from topology import IntSetParser, TopoParser

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

float_string = b'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'

class AbstractRunner:

    exec_name = 'smpimain'
    topo_file = 'topo.xml'
    host_file = 'host.txt'
    simulation_time_str  = b'The simulation took (?P<simulation>%s) seconds \(after parsing and platform setup\)' % float_string
    application_time_str = b'(?P<application>%s) seconds were actual computation of the application' % float_string
    energy_str           = b'Total energy consumption: (?P<total_energy>%s) Joules \(used hosts: (?P<used_energy>%s) Joules; unused/idle hosts: (?P<unused_energy>%s)\)' % ((float_string,)*3)
    full_time_str        = b'Simulated time: (?P<full_time>%s) seconds.' % float_string
    smpi_reg = re.compile(b'[\S\s]*%s[\S\s]*%s\n%s' % (full_time_str, simulation_time_str, application_time_str))
    smpi_energy_reg = re.compile(b'[\S\s]*%s' % energy_str)

    def __init__(self, topologies, size, nb_proc, nb_runs, csv_file_name, energy=False, huge_page_mount=None, running_power=None, shuffle_hosts=False):
        self.topologies = topologies
        self.size = size
        self.nb_proc = nb_proc
        self.nb_runs = nb_runs
        self.csv_file_name = csv_file_name
        os.environ['TIME'] = '/usr/bin/time:output %U %S %F %R %P' # format for /usr/bin/time
        self.default_args = ['smpirun', '-wrapper', '/usr/bin/time', '--cfg=smpi/privatize-global-variables:dlopen',
                '--cfg=smpi/display-timing:yes', '--cfg=smpi/shared-malloc-blocksize:%d'%(1<<21), '-hostfile', self.host_file, '-platform', self.topo_file]
        if huge_page_mount is not None:
            self.default_args.append('--cfg=smpi/shared-malloc-hugepage:%s' % huge_page_mount)
        if energy:
            self.default_args.append('--cfg=plugin:Energy')
        if running_power is not None:
            self.default_args.append('--cfg=smpi/running-power:6217956542.969')
        self.energy = energy
        self.initial_free_memory = psutil.virtual_memory().available
        self.shuffle_hosts = shuffle_hosts

    def check_params(self):
        topo_min_cores = min(self.topologies, key = lambda t: t.nb_cores())
        min_cores = topo_min_cores.nb_cores()
        if min_cores < max(self.nb_proc):
            print('Error: more processes than cores for at least one of the topologies (topology %s has  %d cores, asked for %d processes).' % (topo_min_cores, min_cores, max(self.nb_proc)))
            sys.exit(1)
        for nb_proc in self.nb_proc:
            for topo in self.topologies:
                if nb_proc % topo.core != 0:
                    print('Error: the number of cores does not divide the number of processes for at least one of the topologies (topology %s has %d cores, asked for %d processes).' % (topo, topo.core, nb_proc))
                    sys.exit(1)

    def prequel(self):
        self.check_params()
        self.csv_file = open(self.csv_file_name, 'w')
        self.csv_writer = csv.writer(self.csv_file)
        if self.energy:
            energy_titles = ('total_energy', 'used_energy', 'unused_energy')
        else:
            energy_titles = tuple()
        self.csv_writer.writerow(('topology', 'nb_roots', 'nb_proc', 'size', 'full_time', 'time', 'Gflops', *energy_titles, 'simulation_time', 'application_time',
            'user_time', 'system_time', 'major_page_fault', 'minor_page_fault', 'cpu_utilization', 'uss', 'rss', 'page_table_size', 'memory_size'))

    def parse_smpi(self, output, args):
        match = self.smpi_reg.match(output)
        match_energy = self.smpi_energy_reg.match(output)
        try:
            simulation_time = float(match.group('simulation'))
            application_time = float(match.group('application'))
            self.full_time = float(match.group('full_time'))
            if self.energy:
                total_energy = float(match_energy.group('total_energy'))
                used_energy = float(match_energy.group('used_energy'))
                unused_energy = float(match_energy.group('unused_energy'))
        except AttributeError:
            print('### ERROR ###')
            print('Command was:')
            print(' '.join(args))
            print('Simgrid output was:')
            print(output.decode('utf-8'))
            sys.exit(1)
        if self.energy:
            self.energy_metrics = namedtuple('smpi_energy', ['total_energy', 'used_energy', 'unused_energy'])(total_energy, used_energy, unused_energy)
        else:
            self.energy_metrics = tuple()
        last_line = output.split(b'\n')[-2]
        values = last_line.split()
        assert values[0] == b'/usr/bin/time:output' and len(values) == 6
        self.smpi_metrics = namedtuple('smpi_perf', ['sim_time', 'app_time', 'usr_time', 'sys_time', 'major_page_fault', 'minor_page_fault', 'cpu_utilization'])(
            sim_time         = simulation_time,
            app_time         = application_time,
            usr_time         = float(values[1]),
            sys_time         = float(values[2]),
            major_page_fault = int(values[3]),
            minor_page_fault = int(values[4]),
            cpu_utilization = float(values[5][:-1])/100 # given in percentage, with '%'
        )

    @staticmethod
    def get_pid(process_name):
        result = check_output(['pidof', process_name]).split()
        assert len(result) == 1
        return int(result[0])

    @staticmethod
    def get_page_table_size(pid):
        result = check_output(['grep', 'VmPTE', '/proc/%d/status'%pid]).split()
        assert len(result) == 3
        assert result[0] == b'VmPTE:'
        assert result[2] == b'kB'
        return int(result[1])*1000


    def get_max_memory(self, process_name, timeout):
        sleep_time = 4
        uss, rss, page_table_size, memory_size = 0, 0, 0, 0
        time.sleep(sleep_time/4)
        try:
            pid = self.get_pid(process_name)
        except CalledProcessError:
            return uss, rss, page_table_size, memory_size
        for i in range(int(timeout/sleep_time)):
            memory_size = max(memory_size, self.initial_free_memory-psutil.virtual_memory().available)
            mem_usage = get_memory_usage([process_name])
            if len(mem_usage) == 0:
                return uss, rss, page_table_size, memory_size
            assert len(mem_usage) == 1
            mem_usage = mem_usage[0]
            uss = max(uss, mem_usage['uss'])
            rss = max(rss, mem_usage['rss'])
            try:
                page_table_size = max(page_table_size, self.get_page_table_size(pid))
            except CalledProcessError:
                return uss, rss, page_table_size, memory_size
            time.sleep(sleep_time)
        p = psutil.Process(pid)
        p.kill()
        raise TimeoutError


    def _run(self, args):
        p = Popen(args, stdout = PIPE, stderr = PIPE)
        try:
            self.uss, self.rss, self.page_table_size, self.memory_size = self.get_max_memory(self.exec_name, timeout=10*60*60)
        except TimeoutError as e:
            p.terminate()
            raise e
        output = p.communicate()
        self.parse_smpi(output[1], args)
        process_exit_code = p.wait()
        assert process_exit_code == 0
        return output[0]


    def run(self, nb_proc, size): # return the time (in second) and the speed (in Gflops)
        raise NotImplementedError()

    def sequel(self):
        self.csv_file.close()

    def gen_exp(self):
        all_exp = list(itertools.product(self.topologies, self.nb_proc, self.size))
        random.shuffle(all_exp)
        return all_exp

    def run_all(self):
        self.prequel()
        for i in range(1, self.nb_runs+1):
            print('Iteration %d/%d' % (i, args.nb_runs))
            exp = self.gen_exp()
            for j, (topo, nb_proc, size) in enumerate(exp):
                self.current_topo = topo
                print('\tSub-iteration %d/%d' % (j+1, len(exp)))
                topo.dump_topology_file(self.topo_file)
                topo.dump_host_file(self.host_file, self.shuffle_hosts)
                try:
                    time, flops = self.run(nb_proc, topo.core, size)
                except TimeoutError:
                    print('\t\tTimeoutError (size=%d nb_proc=%d)' % (size, nb_proc))
                    continue
                self.csv_writer.writerow((topo, topo.nb_roots(), nb_proc, size, self.full_time, time, flops, *self.energy_metrics,
                    self.smpi_metrics.sim_time, self.smpi_metrics.app_time,
                    self.smpi_metrics.usr_time, self.smpi_metrics.sys_time,
                    self.smpi_metrics.major_page_fault, self.smpi_metrics.minor_page_fault,
                    self.smpi_metrics.cpu_utilization,
                    self.uss, self.rss, self.page_table_size, self.memory_size))
        self.sequel()

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
        self.index = 0

    def get_P_Q(self, nb_proc, nb_core):
        if nb_core != 1:
            assert nb_proc%nb_core == 0
            P = nb_core
            Q = int(nb_proc/nb_core)
            return P, Q
        factors = primes(nb_proc)
        P, Q = 1, 1
        for fact in factors:
            if P < Q:
                P *= fact
            else:
                Q *= fact
        return P, Q

    def gen_hpl_file(self, nb_proc, nb_core, size):
        P, Q = self.get_P_Q(nb_proc, nb_core)
        with open(self.HPL_file_name, 'w') as f:
            f.write(HPL_dat_text.format(P=P, Q=Q, size=size))


    def run(self, nb_proc, nb_core, size): # we parse the ugly output...
        args = self.default_args + ['-np', str(nb_proc)] + ['../hpl-2.2/bin/SMPI/xhpl']
        self.gen_hpl_file(nb_proc, nb_core, size)
        output_str = self._run(args)
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
    parser.add_argument('--hugepage', type=str,
            default=None, help='Use huge pages, with the given hugetlbfs.')
    parser.add_argument('--energy', action='store_true',
            help='Use the energy plugin.')
    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument('--size', type = lambda s: IntSetParser.parse(s),
            required=True, help='Sizes of the problem')
    required_named.add_argument('--nb_proc', type = lambda s: IntSetParser.parse(s),
            required=True, help='Number of processes to use.')
    parser.add_argument('--running_power', type = float,
            default=None, help='Running power of the host.')
    required_named.add_argument('--csv_file', type = str,
            required=True, help='Path of the CSV file for the results.')
    required_named.add_argument('--topo', type = lambda s: TopoParser.parse(s),
            required=True, help='Description of the fat tree(s).')
    parser.add_argument('--shuffle_hosts', action='store_true',
            help='Shuffle the host list, therefore giving a random mapping.')
    args = parser.parse_args()
    runner = HPL(args.topo, args.size, args.nb_proc, args.nb_runs, args.csv_file, args.energy, args.hugepage, args.running_power, args.shuffle_hosts)
    runner.run_all()
