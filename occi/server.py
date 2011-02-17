import uuid
from abc import ABCMeta
try:
    from ordereddict import OrderedDict
except ImportError:
    OrderedDict = dict

from occi.core import Entity, Resource, Link, CategoryRegistry

class OCCIServer(object):
    """An OCCI Server instance."""

    def __init__(self, backend):
        """A `ServerBackend` object is required to instantiate an OCCI Server."""
        self.registry = CategoryRegistry()
        self.backend = backend

class ServerBackend(object):
    __metaclass__ = ABCMeta

    class ServerBackendError(Exception):
        pass
    class InvalidOperation(ServerBackendError):
        pass

    def get_entity(self, entitiy_id, user=None):
        raise self.ServerBackendError('Server Backend must implement get_entity')

    def filter_entities(self, categories=None, attributes=None, id_prefix=None, user=None):
        """not too sure about id_prefix filtering, i.e. path"""
        raise self.ServerBackendError('Server Backend must implement filter_entities')

    def save_entities(self, entities, id_prefix=None, user=None):
        """Save a set of entities (resource instances) in a single atomic
        operation.

        :param entities: A list of `Entity` objects to persist.
        :keyword id_prefix: `Entity` ID prefix suggested by client for new object.
        :keyword user: The authenticated user.
        :return: A list IDs of the saved `Entity` objects.
        """
        raise self.ServerBackendError('Server Backend must implement save_entities')

    def delete_entities(self, entity_ids, user=None):
        """Delete a set of entities (resource instances) in a single atomic
        operation.

        :param entity_ids: A list `Entity` IDs to delete.
        :keyword user: The authenticated user.
        """
        raise self.ServerBackendError('Server Backend must implement delete_entities')

    def exec_action(self, action, entity, payload=None, user=None):
        """Execute `Action` on the given `Entity` (resource instance).

        :param action: `Action` instance.
        :param entity: `Entity` (resource) instance.
        :keyword payload: Binary payload supplied with Action.
        :keyword user: The authenticated user.
        """
        raise self.ServerBackendError('Server Backend must implement exec_action')

    def exec_action_on_collection(self, action, collection, payload=None, user=None):
        """Execute `Action` on the all `Entity` instances in the specified
        collection (if applicable).

        :param action: `Action` instance.
        :param collection: `Kind` or `Mixin` instance.
        :keyword payload: Binary payload supplied with Action.
        :keyword user: The authenticated user.
        """
        raise self.ServerBackendError('Server Backend must implement exec_action_on_collection')


class DummyBackend(ServerBackend):
    """Very simple (and inefficient) in-memory backend for test purposes.

    >>> backend = DummyBackend()
    >>> from occi.ext.infrastructure import *
    >>> t = backend.save_entities([ComputeKind.entity_type(ComputeKind)])
    >>> compute = ComputeKind.entity_type(ComputeKind)
    >>> compute.set_occi_attributes([('occi.compute.memory', '2.0')])
    >>> storage = StorageKind.entity_type(StorageKind)
    >>> compute_id, storage_id = backend.save_entities([compute, storage])
    >>> link = StorageLinkKind.entity_type(StorageLinkKind)
    >>> link.set_occi_attributes([('source', compute_id), ('target', storage_id), ('occi.storagelink.deviceid', 'ide:0:0')])
    >>> link_id = backend.save_entities([link])
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
            # Generate ID if new instance
            if not entity.id:
                loc = entity.get_occi_kind().location or ''
                entity.id = '%s%s' % (loc, uuid.uuid4())

            # Links
            if isinstance(entity, Link):
                source = self.get_entity(entity.get_occi_attribute('source'), user=user)
                target = self.get_entity(entity.get_occi_attribute('target'), user=user)
                entity.source = source
                entity.target = target
                links = []
                for l in source.links:
                    if l.id != source.id:
                        links.append(l)
                links.append(entity)
                source.links = links

            self._db[entity.id] = entity
            id_list.append(entity.id)
        return id_list

    def delete_entities(self, entity_ids, user=None):
        for entity_id in entity_ids:
            try:
                entity = self._db[entity_id]
                if isinstance(entity, Resource):
                    for l in entity.links:
                        self._db.pop(l.id, None)
                elif isinstance(entity, Link):
                    try:
                        entity.source.links.remove(entity)
                    except ValueError:
                        pass
                del self._db[entity_id]
            except KeyError:
                raise Entity.DoesNotExist(entity_id)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
