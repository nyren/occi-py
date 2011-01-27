
class EntityHandler(object):
    def get(self, headers, body, entity_id, user=None):
        pass

    def post(self, headers, body, entity_id, user=None):
        """action"""
        pass

    def put(self, headers, body, entity_id, user=None):
        pass

    def delete(self, headers, body, entity_id, user=None):
        pass

class CollectionHandler(object):
    def get(self, headers, body, path, user=None):
        pass

    def post(self, headers, body, path, user=None):
        """create resource instance"""
        pass

    def put(self, headers, body, path, user=None):
        """Add resource instance to Mixin collection"""
        pass

    def delete(self, headers, body, path, user=None):
        """Remove resource instance from Mixin collection"""
        pass

class DiscoveryHandler(object):
    def get(self, headers, body, user=None):
        """list all Categories"""
        pass

    def put(self, headers, body, user=None):
        """create custom Mixin"""
        pass

    def delete(self, headers, body, user=None):
        """delete custom Mixin"""
        pass
