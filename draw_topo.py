#! /usr/bin/env python3

import sys
import topology

if __name__ == '__main__':
    topologies = []
    if len(sys.argv) < 3:
        print('Syntax: %s <file_name> <topologies>' % sys.argv[0])
        sys.exit(1)
    for descriptor in sys.argv[2:]:
        topologies.extend(topology.FatTreeParser.parse(descriptor))
    for topo in topologies:
        topo.initialize()
    topology.topo_to_pdf(topologies, sys.argv[1])
