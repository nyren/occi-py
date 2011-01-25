from ordereddict import OrderedDict
from abc import ABCMeta

from occi.core import Category

class OCCIServer(object):
    """An OCCI Server instance."""

    def __init__(self, backend):
        """A Backend object is required to instantiate an OCCI Server."""
        self._categories = OrderedDict()
        self.backend = backend

    def register_category(self, category):
        """Register a new Category/Kind/Mixin."""
        s = str(category)
        if s in self._categories:
            raise Category.Invalid("%s: Category already defined", s)
        self._categories[s] = category

    def unregister_category(self, category):
        """Unregister a previously registered Category/Kind/Mixin."""
        try:
            del self._categories[str(category)]
        except KeyError:
            raise Category.Invalid("%s: Category not registered", category)

    def lookup_category(self, identifier):
        try:
            return self._categories[identifier]
        except KeyError:
            raise Category.DoesNotExist

    def lookup_location(self, path):
        assert(False)

class OCCIBackend(object):
    __metaclass__ = ABCMeta

    def get_entity(self, id):
        pass
    def filter_entities(self, categories=None, attributes=None):
        pass
    def save_entity(self, entity):
        pass
    def delete_entity(self, entity):
        pass
