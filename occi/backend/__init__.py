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

from abc import ABCMeta
from occi.core import CategoryRegistry

class ServerBackend(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.registry = CategoryRegistry()

    class ServerBackendError(Exception):
        pass
    class InvalidOperation(ServerBackendError):
        pass

    def auth_user(self, identity, secret=None, method=None, user=None):
        """Authenticate the user identified by the given user credentials.

        Success:
          Returns a user object, defined by the backend. This user object is
          then passed to all backend methods.

        Failure:
          None is returned.

        :param identity: The user identity.
        :keyword secret: A user secret, digest, etc.
        :keyword method: The authentication method used.
        :keyword user: The authenticated user or None if not authenticated.
        :return: A valid user object or None.
        """
        raise self.ServerBackendError('Server Backend must implement auth_user')

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
        :return: A list of the persisted `Entity` objects.
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

if __name__ == "__main__":
    import doctest
    doctest.testmod()
