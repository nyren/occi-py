import uuid
from abc import ABCMeta
try:
    from ordereddict import OrderedDict
except ImportError:
    OrderedDict = dict

from occi.core import Entity, CategoryRegistry

class OCCIServer(object):
    """An OCCI Server instance."""

    def __init__(self, backend):
        """A `ServerBackend` object is required to instantiate an OCCI Server."""
        self.registry = CategoryRegistry()
        self.backend = backend

class ServerBackend(object):
    __metaclass__ = ABCMeta

    def ServerBackendError(Exception):
        pass
    def InvalidOperation(ServerBackendError):
        pass

    def get_entity(self, entitiy_id, user=None):
        raise NotImplemented('Server Backend must implement get_entity')

    def filter_entities(self, categories=None, attributes=None, id_prefix=None, user=None):
        """not too sure about id_prefix filtering, i.e. path"""
        raise NotImplemented('Server Backend must implement filter_entities')

    def save_entities(self, entities, id_prefix=None, user=None):
        """Save a set of entities (resource instances) in a single atomic
        operation.

        :param entities: A list of `Entity` objects to persist.
        :keyword id_prefix: `Entity` ID prefix suggested by client for new object.
        :keyword user: The authenticated user.
        :return: A list IDs of the saved `Entity` objects.
        """
        raise NotImplemented('Server Backend must implement save_entities')

    def delete_entities(self, entity_ids, user=None):
        """Delete a set of entities (resource instances) in a single atomic
        operation.

        :param entity_ids: A list `Entity` IDs to delete.
        :keyword user: The authenticated user.
        """
        raise NotImplemented('Server Backend must implement delete_entities')


class DummyBackend(ServerBackend):
    """Very simple (and inefficient) in-memory backend for test purposes.

    >>> backend = DummyBackend()
    >>> from occi.ext.infrastructure import *
    >>> t = backend.save_entities([ComputeKind.entity_type(ComputeKind)])
    >>> compute = ComputeKind.entity_type(ComputeKind)
    >>> compute.set_occi_attributes([('occi.compute.memory', '2.0')])
    >>> storage = StorageKind.entity_type(StorageKind)
    >>> link = StorageLinkKind.entity_type(StorageLinkKind)
    >>> link.target = storage ; compute.links.append(link)
    >>> compute_id, storage_id, link_id = backend.save_entities([compute, storage, link])
    >>> len(backend.filter_entities())
    4
    >>> len(backend.filter_entities(categories=[ComputeKind]))
    2
    >>> len(backend.filter_entities(categories=[ComputeKind], attributes=[('occi.compute.memory', 2.0)]))
    1
    >>> backend.get_entity(compute_id) == compute
    True
    >>> backend.delete_entities(t)
    >>> [entity.id for entity in backend.filter_entities(categories=[ComputeKind])] == [compute_id]
    True
    """

    def __init__(self):
        self._db = OrderedDict()

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
                    if str(t) != str(value):    # FIXME - this implies "2.0" == 2.0
                        skip = True
                        break
            if skip: continue

            result.append(entity)

        return result

    def save_entities(self, entities, id_prefix=None, user=None):
        id_list = []
        for entity in entities:
            if not entity.id:
                loc = entity.get_occi_kind().location or ''
                entity.id = '%s%s' % (loc, uuid.uuid4())

            self._db[entity.id] = entity
            id_list.append(entity.id)
        return id_list

    def delete_entities(self, entity_ids, user=None):
        for entity_id in entity_ids:
            try:
                del self._db[entity_id]
            except KeyError:
                raise Entity.DoesNotExist(entity_id)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
