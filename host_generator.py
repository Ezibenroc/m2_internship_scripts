#! /usr/bin/env python3
import sys

if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.stderr.write('Syntax: %s <pattern> <number of hosts> <filename>\n' % (sys.argv[0]))
        sys.stderr.write('Example of call: {0} "host-%d.stampede.tacc.utexas.edu" 6400 hostnames_stampede.txt\n'.format(sys.argv[0]))
        sys.exit(1)
    nb_hosts = int(sys.argv[2])
    pattern = sys.argv[1]
    with open(sys.argv[3], 'w') as f:
        for host_id in range(nb_hosts):
            f.write(pattern % host_id)
            f.write('\n')
