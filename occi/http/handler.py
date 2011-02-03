from occi.core import Entity
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

class HttpResponseCode(object):
    def http_response(self, status, msg=None):
        headers = [('Content-Type', 'text/plain; charset=utf-8')]
        msg = msg or ''
        return HttpResponse(status=status, headers=headers, body=str(msg))

    def ALL_OK(self, msg='OK'):
        return self.http_response(200, msg)
    def CREATED(self, msg='Created'):
        return self.http_response(201, msg)
    def ACCEPTED(self, msg='Accepted'):
        return self.http_response(202, msg)
    def DELETED(self, msg=''):
        return self.http_response(204, msg)
    def BAD_REQUEST(self, msg='Bad request'):
        return self.http_response(400, msg)
    def FORBIDDEN(self, msg='Forbidden'):
        return self.http_response(401, msg)
    def NOT_FOUND(self, msg='Not Found'):
        return self.http_response(404, msg)
    def CONFLICT(self, msg='Conflict/Duplicate'):
        return self.http_response(401, msg)
    def NOT_HERE(self, msg='Gone'):
        return self.http_response(410, msg)
    def SERVER_ERROR(self, msg='Internal Server Error'):
        return self.http_response(500, msg)
    def NOT_IMPLEMENTED(self, msg='Not Implemented'):
        return self.http_response(501, msg)
    def THROTTLED(self, msg='Throttled'):
        return self.http_response(503, msg)
hrc = HttpResponseCode()

class HandlerBase(object):
    def __init__(self, server):
        self.server = server

class EntityHandler(HandlerBase):
    def get(self, request, entity_id, user=None):
        """Retrieve a resource instance."""
        try:
            parser = get_parser(request.content_type)
            parser.parse(request.headers, request.body)
        except (ParserError, HttpHeaderError) as e:
            return hrc.BAD_REQUEST(e)

        try:
            entity = self.server.backend.get_entity(entity_id, user=user)
        except Entity.DoesNotExist as e:
            return hrc.BAD_REQUEST(e)

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
    def get(self, request, path='', user=None):
        print path
        return HttpResponse()

    def post(self, request, path, user=None):
        """create resource instance
         or
        action on collection
        """
        pass

    def _create_resource(self, request, path, user=None):
        pass
    def _collection_action(self, request, path, user=None):
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
