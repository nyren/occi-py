from ordereddict import OrderedDict
from abc import ABCMeta

from occi.core import Category

class OCCIServer(object):
    """An OCCI Server instance."""

    def __init__(self, backend):
        """A `ServerBackend` object is required to instantiate an OCCI Server."""
        self.registry = CategoryRegistry()
        self.backend = backend

class ServerBackend(object):
    __metaclass__ = ABCMeta

    def get_entity(self, entitiy_id, user=None):
        pass
    def filter_entities(self, categories=None, attributes=None, id_prefix=None, user=None):
        """not too sure about id_prefix filtering, i.e. path"""
        pass
    def save_entity(self, entity, user=None):
        """
        :return entity_id: string
        """
        pass
    def delete_entity(self, entity, user=None):
        pass
