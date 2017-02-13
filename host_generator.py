#! /usr/bin/env python3
import sys

PATTERN = 'host-%d.hawaii.edu'

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.stderr.write('Syntax: %s <number of hosts> <filename>\n' % (sys.argv[0]))
        sys.exit(1)
    nb_hosts = int(sys.argv[1])
    with open(sys.argv[2], 'w') as f:
        for host_id in range(nb_hosts):
            f.write(PATTERN % host_id)
            f.write('\n')
