import itertools

class AbstractSettings:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key not in self.attributes:
                raise AttributeError('Unexpected attribute %s' % key)
            self.__setattr__(key, value)
        self.check_attributes()

    def check_attributes(self):
        for attr, cls in self.attributes.items():
            if not hasattr(self, attr):
                raise AttributeError('Expected attribute %s' % attr)
            attribute = self.__getattribute__(attr)
            if isinstance(attribute, cls):
                self.__setattr__(attr, [attribute])
            elif not hasattr(attribute, '__iter__') or not all(isinstance(x, cls) for x in attribute):
                raise AttributeError('Expected attribute %s of type %s, got %s' % (attr, cls.__name__, attribute))

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(('%s=%s' % (key, self.__getattribute__(key))) for key in self.attributes))

    def __eq__(self, other):
        if self.attributes != other.attributes:
            return False
        for attr in self.attributes:
            if set(self.__getattribute__(attr)) != set(other.__getattribute__(attr)):
                return False
        return True

    def product(self):
        attributes = [[(attr, val) for val in self.__getattribute__(attr)] for attr in self.attributes]
        prod = itertools.product(*attributes)
        prod = [dict(attr) for attr in prod]
        return [self.__class__(**attr) for attr in prod]

class Cluster(AbstractSettings):
    '''
        All the attributes have to be given in standard units (e.g. bandwidth in bps, not Mbps).
    '''
    attributes = {'nb_core': int, 'latency': float, 'bandwidth': float, 'local_latency':float, 'local_bandwidth':float}

class FatTree(AbstractSettings):
    attributes = {'down_ports': int, 'up_ports': int, 'parallel_ports': int}

class HPL(AbstractSettings):
    attributes = {'size': int, 'block_size': int, 'process_width': int, 'process_height': int, 'broadcast_algorithm': int}

class Simgrid(AbstractSettings):
    attributes = {'privatization': str, 'hugetlbfs': str}

class Experiment(AbstractSettings):
    attributes = {'cluster': Cluster, 'FatTree': FatTree, 'HPL': HPL, 'Simgrid': Simgrid}
