import uuid
from abc import ABCMeta

from occi.core import Entity, CategoryRegistry

class OCCIServer(object):
    """An OCCI Server instance."""

    def __init__(self, backend):
        """A `ServerBackend` object is required to instantiate an OCCI Server."""
        self.registry = CategoryRegistry()
        self.backend = backend

class ServerBackend(object):
    __metaclass__ = ABCMeta

    def get_entity(self, entitiy_id, user=None):
        raise NotImplemented('Server Backend must implement get_entity')

    def filter_entities(self, categories=None, attributes=None, id_prefix=None, user=None):
        """not too sure about id_prefix filtering, i.e. path"""
        raise NotImplemented('Server Backend must implement filter_entities')

    def save_entity(self, entity, user=None):
        """
        :return entity_id: string
        """
        raise NotImplemented('Server Backend must implement save_entity')

    def delete_entity(self, entity_id, user=None):
        raise NotImplemented('Server Backend must implement delete_entity')


class DummyBackend(ServerBackend):
    """Very simple (and inefficient) in-memory backend for test purposes.

    >>> backend = DummyBackend()
    >>> from occi.ext.infrastructure import *
    >>> t = backend.save_entity(ComputeKind.entity_type(ComputeKind))
    >>> compute = ComputeKind.entity_type(ComputeKind)
    >>> compute.set_occi_attributes([('occi.compute.memory', '2.0')])
    >>> storage = StorageKind.entity_type(StorageKind)
    >>> link = StorageLinkKind.entity_type(StorageLinkKind)
    >>> link.target = storage ; compute.links.append(link)
    >>> compute_id = backend.save_entity(compute)
    >>> storage_id = backend.save_entity(storage)
    >>> link_id = backend.save_entity(link)
    >>> len(backend.filter_entities())
    4
    >>> len(backend.filter_entities(categories=[ComputeKind]))
    2
    >>> backend.get_entity(compute_id) == compute
    True
    >>> backend.delete_entity(t)
    >>> [entity.id for entity in backend.filter_entities(categories=[ComputeKind])] == [compute_id]
    True
    """

    def __init__(self):
        self._db = {}

    def get_entity(self, entity_id, user=None):
        try:
            return self._db[entity_id]
        except KeyError:
            raise Entity.DoesNotExist(entity_id)

    def filter_entities(self, categories=None, attributes=None, id_prefix=None, user=None):
        result = []
        for entity_id, entity in self._db.iteritems():
            skip = False
            # Filter on id_prefix
            if id_prefix:
                t = entity_id.lstrip(id_prefix)
                if t == entity_id:
                    continue

            # Filter on Categories
            cats = entity.list_occi_categories()
            for cat in categories or ():
                if str(cat) not in cats:
                    skip=True
                    break
            if skip: continue

            # Filter on Attributes
            if categories and attributes:
                for name, value in attributes:
                    t = entity.get_occi_attribute(name)
                    if t != value:
                        skip = True
                        break
            if skip: continue

            result.append(entity)

        return result

    def save_entity(self, entity, user=None):
        """
        :return entity_id: string
        """
        if not entity.id:
            loc = entity.get_occi_kind().location or ''
            entity.id = '%s%s' % (loc, uuid.uuid4())

        self._db[entity.id] = entity
        return entity.id

    def delete_entity(self, entity_id, user=None):
        try:
            del self._db[entity_id]
        except KeyError:
            raise Entity.DoesNotExist(entity_id)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
