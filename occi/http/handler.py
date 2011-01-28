
class HttpRequest(object):
    def __init__(self, headers, body, content_type=None,
            user=None, query_args=None):
        self.headers = headers
        self.body = body
        self.content_type = content_type
        self.user = user
        self.query_args = query_args or {}

class HandlerBase(object):
    def __init__(self, server):
        self.server = server

class EntityHandler(HandlerBase):
    def get(self, request, entity_id, user=None):
        pass

    def post(self, request, entity_id, user=None):
        """action"""
        pass

    def put(self, request, entity_id, user=None):
        pass

    def delete(self, request, entity_id, user=None):
        pass

class CollectionHandler(HandlerBase):
    def get(self, request, path, user=None):
        pass

    def post(self, request, path, user=None):
        """create resource instance
         or
        action on collection
        """
        pass

    def put(self, request, path, user=None):
        """Add resource instance to Mixin collection"""
        pass

    def delete(self, request, path, user=None):
        """Remove resource instance from Mixin collection"""
        pass

class DiscoveryHandler(HandlerBase):
    def get(self, request, user=None):
        """list all Categories"""
        pass

    def put(self, request, user=None):
        """create custom Mixin"""
        pass

    def delete(self, request, user=None):
        """delete custom Mixin"""
        pass
