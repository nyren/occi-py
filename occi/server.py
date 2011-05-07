#
# Copyright (C) 2010-2011  Ralf Nyren <ralf@nyren.net>
#
# This file is part of the occi-py library.
#
# The occi-py library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The occi-py library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with the occi-py library.  If not, see <http://www.gnu.org/licenses/>.
#

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

    def filter_entities(self, categories=None, attributes=None, user=None):
        """Return a list of `Entity` objects matching the specified filter.

        The filter parameters are specified using the keyword arguments
        described below.  All specified filter parameters must match the
        returned `Entity` instances.

        :keyword categories: A list of `Category` instances a matching `Entity`
            instance must be a associated with.
        :keyword attributes: A list of attribute key-value pairs which must all
            be present in a matching `Entity` instance.
        :keyword user: The authenticated user.
        :return: A list of `Entity` instances matching the filter parameters.
        """
        raise self.ServerBackendError('Server Backend must implement filter_entities')

    def save_entities(self, entities, user=None):
        """Save a set of entities (resource instances) in a single atomic
        operation.

        :param entities: A list of `Entity` objects to persist.
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

    def add_user_mixin(self, mixin, user=None):
        """Validate a user-supplied Mixin instance and perform any
        backend-specific tasks related to the event. The method must return the
        mixin instance to be added, either a modified version or the original
        user-supplied Mixin instance.

        :param mixin: User-defined `Mixin` instance.
        :keyword user: The authenticated user.
        :return: The actual `Mixin` instance to be added.
        """
        raise NotImplementedError('User-defined Mixins not supported')

    def remove_user_mixin(self, mixin, user=None):
        """Validate the removal of a user-defined `Mixin` instance and perform
        any backend-specific tasks related to the event. The method is expected
        to throw a InvalidOperation exception if the removal operation is to be
        refused.

        :param mixin: User-defined `Mixin` instance to be removed.
        :keyword user: The authenticated user.
        """
        raise NotImplementedError('User-defined Mixins not supported')


class DummyBackend(ServerBackend):
    """Very simple (and inefficient) in-memory backend for test purposes.

    >>> backend = DummyBackend()
    >>> from occi.ext.infrastructure import *
    >>> t = backend.save_entities([ComputeKind.entity_type(ComputeKind)])
    >>> compute = ComputeKind.entity_type(ComputeKind)
    >>> compute.occi_import_attributes([('occi.compute.memory', '2.0')])
    >>> storage = StorageKind.entity_type(StorageKind)
    >>> compute_id, storage_id = backend.save_entities([compute, storage])
    >>> link = StorageLinkKind.entity_type(StorageLinkKind)
    >>> link.occi_import_attributes([('occi.core.source', compute_id), ('occi.core.target', storage_id), ('occi.storagelink.deviceid', 'ide:0:0')])
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

    def filter_entities(self, categories=None, attributes=None, user=None):
        result = []
        for entity_id, entity in self._db.iteritems():
            skip = False

            # Filter on Categories
            cats = entity.occi_list_categories()
            for cat in categories or ():
                if str(cat) not in cats:
                    skip=True
                    break
            if skip: continue

            # Filter on Attributes
            if categories and attributes:
                for name, value in attributes:
                    t = entity.occi_get_attribute(name)
                    if str(t) != str(value):    # FIXME - this implies "2.0" == 2.0
                        skip = True
                        break
            if skip: continue

            result.append(entity)

        return result

    def save_entities(self, entities, user=None):
        id_list = []
        for entity in entities:
            # Generate ID if new instance
            if not entity.id:
                entity.occi_set_attribute('occi.core.id', uuid.uuid4())

            # Links
            if isinstance(entity, Link):
                source = self.get_entity(entity.occi_get_attribute('occi.core.source').id, user=user)
                target = self.get_entity(entity.occi_get_attribute('occi.core.target').id, user=user)
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

    def exec_action(self, action, entity, payload=None, user=None):
        try:
            return getattr(entity, 'exec_action')(action, payload=payload)
        except AttributeError:
            return None

    def add_user_mixin(self, mixin, user=None):
        return mixin

    def remove_user_mixin(self, mixin, user=None):
        pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()
