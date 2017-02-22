import functools
import itertools
from lxml import etree

class ParseError(Exception):
    pass

class Parser:
    out_separator = ';'
    in_separator = ','
    range_separator = ':'

    @classmethod
    def parse(cls, description):
        blocks = description.split(cls.out_separator)
        sub_blocks = [block.split(cls.in_separator) for block in blocks]
        for i in range(len(sub_blocks)):
            sub_blocks[i] = [cls.parse_range(elt) for elt in sub_blocks[i]]
        return sub_blocks

    @classmethod
    def parse_range(cls, description):
        error = False
        splitted = description.split(cls.range_separator)
        if len(splitted) == 1:
            result = cls.parse_int(splitted[0])
            result = range(result, result+1)
        elif len(splitted) == 2:
            result = range(cls.parse_int(splitted[0]), cls.parse_int(splitted[1])+1)
            if len(result) == 0:
                error = True
        else:
            error = True
        if error:
            raise ParseError('Wrong range: %s' % description)
        else:
            return result

    @classmethod
    def parse_int(cls, description):
        error = False
        try:
            result = int(description)
        except ValueError:
            error = True
        if error or result <= 0:
            raise ParseError('Wrong integer: %s' % description)
        else:
            return result

class FatTreeParser(Parser):
    @classmethod
    def parse(cls, description):
        result = super().parse(description)
        if len(result) != 4:
            raise ParseError('A fat-tree description has exactly 4 parts.')
        l, *descriptors = result
        if len(l) != 1 or len(l[0]) != 1:
            raise ParseError('The first part of a fat-tree description is an integer (number of levels).')
        else:
            l = l[0][0]
        if any(len(sub) != l for sub in descriptors):
            raise ParseError('One of the sub-lists has a length different than %d.' % l)
        for i in range(len(descriptors)):
            descriptors[i] = list(itertools.product(*descriptors[i]))
        descriptors = itertools.product(*descriptors)
        return [FatTree(*t) for t in descriptors]


class FatTree:
    prefix = 'host-'
    suffix = '.hawaii.edu'
    speed = '1Gf'
    bw = '125MBps'
    lat = '50us'
    loopback_bw = '100MBps'
    loopback_lat = '0'

    def __init__(self, down, up, parallel):
        def check_list(l):
            for n in l:
                assert isinstance(n, int) and n > 0
        check_list(down)
        check_list(up)
        check_list(parallel)
        assert len(down) == len(up) == len(parallel)
        self.down = tuple(down)
        self.up = tuple(up)
        self.parallel = tuple(parallel)

    def __eq__(self, other):
        return self.down == other.down and\
            self.up == other.up and\
            self.parallel == other.parallel

    def __hash__(self):
        return hash((self.down, self.up, self.parallel))

    def __str__(self):
        def intlist_to_str(l):
            return ','.join(str(n) for n in l)
        down = intlist_to_str(self.down)
        up = intlist_to_str(self.up)
        parallel = intlist_to_str(self.parallel)
        return ';'.join([str(len(self.down)), down, up, parallel])

    def __repr__(self):
        return str(self)

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
        AS.set('routing', 'Full') # TODO may need to change routing
        cluster = etree.SubElement(AS, 'cluster')
        cluster.set('id', 'cluster0')
        cluster.set('prefix', self.prefix)
        cluster.set('suffix', self.suffix)
        cluster.set('radical', '0-%d' % (self.nb_nodes()-1))
        cluster.set('speed', self.speed)
        cluster.set('bw', self.bw)
        cluster.set('lat', self.lat)
        cluster.set('loopback_bw', self.loopback_bw)
        cluster.set('loopback_lat', self.loopback_lat)
        cluster.set('topology', 'FAT_TREE')
        cluster.set('topo_parameters', str(self))
        return etree.ElementTree(platform)

    def dump_topology_file(self, file_name):
        with open(file_name, 'wb') as f:
            string = etree.tostring(self.to_xml(), xml_declaration=True, pretty_print=True,
                    doctype='<!DOCTYPE platform SYSTEM "http://simgrid.gforge.inria.fr/simgrid/simgrid.dtd">')
            f.write(string)

    def dump_host_file(self, file_name):
        pattern = self.prefix + '%d' + self.suffix + '\n'
        with open(file_name, 'w') as f:
            for host_id in range(self.nb_nodes()):
                f.write(pattern % host_id)
