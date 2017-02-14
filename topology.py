import functools
from lxml import etree

class FatTree:

    prefix = 'host-'
    suffix = '.hawaii.edu'
    speed = '1GF'
    bw = '125MBps'
    lat = '50us'
    loopback_bw = '100MBps'
    loopback_lat = '0'

    @classmethod
    def parse(cls, description):
        def parse_int_list(string):
            return [int(n) for n in string.split(',')]
        sub_descr = description.split(';')
        assert len(sub_descr) == 4
        height = int(sub_descr[0])
        down     = parse_int_list(sub_descr[1])
        up       = parse_int_list(sub_descr[2])
        parallel = parse_int_list(sub_descr[3])
        assert height == len(down) == len(up) == len(parallel)
        return cls(down, up, parallel)

    def __init__(self, down, up, parallel):
        def check_list(l):
            for n in l:
                assert isinstance(n, int) and n > 0
        check_list(down)
        check_list(up)
        check_list(parallel)
        assert len(down) == len(up) == len(parallel)
        self.down = down
        self.up = up
        self.parallel = parallel

    def __str__(self):
        def intlist_to_str(l):
            return ','.join(str(n) for n in l)
        down = intlist_to_str(self.down)
        up = intlist_to_str(self.up)
        parallel = intlist_to_str(self.parallel)
        return ';'.join([str(len(self.down)), down, up, parallel])

    def nb_nodes(self):
        return functools.reduce(lambda a, b: a*b, self.down, 1)

    def nb_roots(self):
        return functools.reduce(lambda a, b: a*b, self.up, 1)

    def to_xml(self):
        platform = etree.Element('platform')
        platform.set('version', '4')
        platform.addprevious(etree.Comment('%d-level fat-tree with %d nodes' %
            (len(self.down), self.nb_nodes())))
        AS = etree.SubElement(platform, 'AS')
        AS.set('id', 'AS0')
        AS.set('routing', 'full') # TODO may need to change routing
        cluster = etree.SubElement(AS, 'cluster')
        cluster.set('id', 'cluster0')
        cluster.set('prefix', self.prefix)
        cluster.set('suffix', self.suffix)
        cluster.set('radical', '0-%d' % self.nb_nodes())
        cluster.set('speed', self.speed)
        cluster.set('bw', self.bw)
        cluster.set('lat', self.lat)
        cluster.set('loopback_bw', self.loopback_bw)
        cluster.set('loopback_lat', self.loopback_lat)
        cluster.set('topology', 'FAT_TREE')
        cluster.set('topo_parameters', str(self))
        return etree.ElementTree(platform)

    def dump_topology_file(self, file_name):
        self.to_xml().write(file_name, xml_declaration=True, pretty_print=True)

    def dump_host_file(self, file_name):
        pattern = self.prefix + '%d' + self.suffix + '\n'
        with open(file_name, 'w') as f:
            for host_id in range(self.nb_nodes()):
                f.write(pattern % host_id)
