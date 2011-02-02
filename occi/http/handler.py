from occi.http import get_parser, get_renderer

class HttpRequest(object):
    def __init__(self, headers, body, content_type=None,
            user=None, query_args=None):
        self.headers = headers
        self.body = body
        self.content_type = content_type
        self.user = user
        self.query_args = query_args or {}

class HttpResponse(object):
    def __init__(self, status=200, headers=None, body=None):
        self.status = status
        self.headers = headers or []
        self.body = body or ''

class HandlerBase(object):
    def __init__(self, server):
        self.server = server

class EntityHandler(HandlerBase):
    def get(self, request, entity_id, user=None):
        try:
            parser = get_parser(request.content_type)
            parser.parse(request.headers, request.body)
        except (ParserError, HttpHeaderError) as e:
            return HttpResponse(status=406, body=e)

        try:
            entity = server.backend.get_entity(entity_id, user=user)
        except ServerBackend.Error as e:
            print e
            return HttpResponse(status=500)

        renderer = get_renderer(parser.accept_types)
        obj = DataObject()
        obj.load_from_entity(entity)
        renderer.render(obj)

        return HttpResponse(renderer.headers, rendere.body)

    def post(self, request, entity_id, user=None):
        """action"""
        pass

    def put(self, request, entity_id, user=None):
        pass

    def delete(self, request, entity_id, user=None):
        pass

class CollectionHandler(HandlerBase):
    def get(self, request, path='/', user=None):
        print path
        return HttpResponse()

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
        return HttpResponse()

    def put(self, request, user=None):
        """create custom Mixin"""
        pass

    def delete(self, request, user=None):
        """delete custom Mixin"""
        pass
