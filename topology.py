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

    def get_nodes_at_level(self, l):
        descriptors = []
        for j in reversed(range(len(self.down))):
            if j > l:
                descriptors.append(range(self.down[j]))
            else:
                descriptors.append(range(self.up[j]))
        return [Node(l, descr) for descr in itertools.product(*descriptors)]

    def initialize_nodes(self):
        self.nodes = dict()
        for l in range(len(self.down)):
            self.nodes[l] = self.get_nodes_at_level(l)
            for i, node in enumerate(self.nodes[l]):
                node.index = i
                node.coordinates = node.index - len(self.nodes[l])/2, l
                if l == 0:
                    node.children = range(i*self.down[0], (i+1)*self.down[0])
                else:
                    node.children = []
                node.parents  = []

    def initialize_edges(self):
        for l in range(1, len(self.down)):
            for parent in self.nodes[l]:
                for potential_child in self.nodes[l-1]:
                    if parent.is_up_node_of(potential_child):
                        parent.children.append(potential_child)
                        potential_child.parents.append(parent)

    def iterate_nodes(self):
        for nodes in self.nodes.values():
            for node in nodes:
                yield node

    def iterate_roots(self):
        return iter(self.nodes[len(self.down)-1])

    def check_edges(self):
        for node in self.iterate_nodes():
            assert len(node.children) == self.down[node.level]
            if node.level < len(self.down) - 1:
                assert len(node.parents) == self.up[node.level+1]
            else:
                assert len(node.parents) == 0

    def check_leaves(self):
        for root in self.iterate_roots():
            assert len(set(root.get_leaves())) == self.nb_nodes()

    def check(self):
        self.check_edges()
        self.check_leaves()

    def initialize(self):
        self.initialize_nodes()
        self.initialize_edges()
        self.check()

    def dump_tikz_nodes(self, fd):
        for node in self.iterate_nodes():
            node.dump_tikz_node(fd)

    def dump_tikz_edges(self, fd):
        for node in self.iterate_nodes():
            node.dump_tikz_children_edges(fd)

    def dump_tikz(self, fd):
        fd.write('\\begin{figure}[!ht]')
        fd.write('\\centering\n')
        fd.write('\\begin{tikzpicture}[scale=0.7,transform shape]\n')
        self.dump_tikz_nodes(fd)
        self.dump_tikz_edges(fd)
        fd.write('\\end{tikzpicture}\n')
        fd.write('\\caption{%s}\n' % str(self))
        fd.write('\\end{figure}\n')

def topo_to_tex(topologies, filename):
    with open(filename, 'w') as fd:
        fd.write('\\documentclass[10pt]{article}\n')
        fd.write('\\usepackage{geometry}\n')
        fd.write('\\geometry{paperwidth=16383pt, paperheight=16383pt, left=40pt, top=40pt, textwidth=280pt, marginparsep=20pt, marginparwidth=100pt, textheight=16263pt, footskip=40pt}\n')
        fd.write('\\usepackage{tikz}\n')
        fd.write('\\thispagestyle{empty}\n')
        fd.write('\\usepackage{caption}')
        fd.write('\\captionsetup[figure]{labelformat=empty}')
        fd.write('\\begin{document}\n')
        for topo in topologies:
            topo.dump_tikz(fd)
        fd.write('\\end{document}\n')

def topo_to_pdf(topologies, filename):
    import os
    import shutil
    from subprocess import Popen, PIPE, DEVNULL
    cwd = os.getcwd()
    os.chdir('/tmp')
    topo_to_tex(topologies, 'tmp.tex')
    p = Popen(['xelatex', '-interaction=batchmode', 'tmp.tex'], stdout = DEVNULL, stderr = DEVNULL)
    assert p.wait() == 0
    p = Popen(['pdfcrop', 'tmp.pdf', 'tmp.pdf'], stdout = DEVNULL, stderr = DEVNULL)
    assert p.wait() == 0
    shutil.move('tmp.pdf', os.path.join(cwd, filename))
    os.chdir(cwd)


class Node:
    NODE_TIKZ_OPT = 'draw, circle'

    def __init__(self, level, descriptor):
        self.level = level
        self.descriptor = descriptor

    def __repr__(self):
        return '%d: %s' % (self.level, self.descriptor)

    def __eq__(self, other):
        return self.level == other.level and self.descriptor == other.descriptor

    def is_up_node_of(self, other):
        if self.level != other.level + 1:
            return False
        for i in range(len(self.descriptor)):
            if len(self.descriptor) - i - 1 == self.level:
                continue
            if self.descriptor[i] != other.descriptor[i]:
                return False
        return True

    def get_leaves(self):
        if self.level == 0:
            return list(self.children)
        else:
            return sum([child.get_leaves() for child in self.children], [])

    def get_id(self):
        return '%d_%d' % (self.level, self.index)

    def dump_tikz_node(self, fd):
        fd.write('\\node[%s] (%s) at %s {} ;\n' % (self.NODE_TIKZ_OPT, self.get_id(), self.coordinates))

    def dump_tikz_children_edges(self, fd):
        if self.level > 0:
            for child in self.children:
                fd.write('\\draw (%s.north) -- (%s.south) ;\n' % (child.get_id(), self.get_id()))
