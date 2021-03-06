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

from occi import OrderedDict
from occi.core import Entity, Resource, Link, Mixin
from occi.backend import ServerBackend

class DummyBackend(ServerBackend):
    """Very simple (and inefficient) in-memory backend for test purposes.

    >>> backend = DummyBackend()
    >>> from occi.ext.infrastructure import *
    >>> t = backend.save_entities([ComputeKind.entity_type(ComputeKind)])
    >>> compute = ComputeKind.entity_type(ComputeKind)
    >>> compute.occi_import_attributes([('occi.compute.memory', '2.0')])
    >>> storage = StorageKind.entity_type(StorageKind)
    >>> s_compute, s_storage = backend.save_entities([compute, storage])
    >>> link = StorageLinkKind.entity_type(StorageLinkKind)
    >>> link.occi_import_attributes([('occi.core.source', s_compute.id), ('occi.core.target', s_storage.id), ('occi.storagelink.deviceid', 'ide:0:0')])
    >>> s_link = backend.save_entities([link])
    >>> len(backend.filter_entities())
    4
    >>> len(backend.filter_entities(categories=[ComputeKind]))
    2
    >>> len(backend.filter_entities(categories=[ComputeKind], attributes=[('occi.compute.memory', 2.0)]))
    1
    >>> backend.get_entity(s_compute.id) == compute
    True
    >>> backend.save_entities(delete_entity_ids=[entity.id for entity in t])
    []
    >>> [entity.id for entity in backend.filter_entities(categories=[ComputeKind])] == [s_compute.id]
    True
    """

    def __init__(self):
        super(DummyBackend, self).__init__()
        self._db = OrderedDict()
        self._user_mixins = {}

    def auth_user(self, identity, secret=None, method=None, user=None):
        return None

    def get_entity(self, entity_id, user=None):
        entity_id = str(entity_id)
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

    def save_entities(self, entities=None, delete_entity_ids=None, user=None):
        if delete_entity_ids:
            self._delete_entities(delete_entity_ids, user=user)
        saved_entities = []
        for entity in entities or ():
            # Generate ID if new instance
            if not entity.id:
                entity.occi_set_attribute('occi.core.id', uuid.uuid4())

            # Links
            if isinstance(entity, Link):
                source = self.get_entity(entity.occi_get_attribute('occi.core.source').id, user=user)
                target = self.get_entity(entity.occi_get_attribute('occi.core.target').id, user=user)
                entity.occi_set_attribute('occi.core.source', source)
                entity.occi_set_attribute('occi.core.target', target)
                links = []
                for l in source.links:
                    if l.id != source.id:
                        links.append(l)
                links.append(entity)
                source.links = links

            self._db[str(entity.id)] = entity
            saved_entities.append(entity)
        return saved_entities

    def _delete_entities(self, entity_ids, user=None):
        for entity_id in entity_ids:
            entity_id = str(entity_id)
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

    def exec_action_on_collection(self, action, collection, payload=None, user=None):
        # FIXME: make atomic
        for entity in self.filter_entities(categories=[collection], user=user):
            self.exec_action(action, entity, payload=payload, user=user)
        return None

    def add_user_category(self, category, user=None):
        if not isinstance(category, Mixin):
            raise self.InvalidOperation('Permission denied')
        self._user_mixins[str(category)] = category
        return category

    def remove_user_category(self, category, user=None):
        try:
            del self._user_mixins[str(category)]
        except KeyError:
            raise self.InvalidOperation('Permission denied')

if __name__ == "__main__":
    import doctest
    doctest.testmod()
