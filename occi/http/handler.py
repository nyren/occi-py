from occi.core import Entity
from occi.http import get_parser, get_renderer
from occi.http.header import HttpHeaderError
from occi.http.parser import ParserError
from occi.http.renderer import RendererError
from occi.http.dataobject import DataObject

class HttpRequest(object):
    def __init__(self, headers, body, content_type=None,
            user=None, query_args=None):
        self.headers = headers
        self.body = body
        self.content_type = content_type
        self.user = user
        self.query_args = query_args or {}

class HttpResponse(object):
    def __init__(self, headers=None, body=None, status=None):
        self.status = status or 200
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
        return hrc.NOT_IMPLEMENTED()

    def put(self, request, entity_id, user=None):
        return hrc.NOT_IMPLEMENTED()

    def delete(self, request, entity_id, user=None):
        return hrc.NOT_IMPLEMENTED()

class CollectionHandler(HandlerBase):
    def get(self, request, path='', user=None):
        print path
        return HttpResponse()

    def post(self, request, path, user=None):
        """Create new resource instance(s) OR execute an action on the specified
        collection.
        """
        # Action request?
        if request.query_args:
            return self._collection_action(request, path, user=user)

        # Parse request
        try:
            parser = get_parser(request.content_type)
            parser.parse(request.headers, request.body)
        except (ParserError, HttpHeaderError) as e:
            return hrc.BAD_REQUEST(e)

        # Get renderer
        try:
            renderer = get_renderer(parser.accept_types)
        except RendererError as e:
            return hrc.BAD_REQUEST(e)

        # Any data-objects specified?
        if not parser.objects:
            return hrc.BAD_REQUEST('No resource instance(s) specified')

        # Convert request objects to entity instances
        entities = []
        try:
            for dao in parser.objects:
                entities.append(dao.save_to_entity(
                    category_registry=self.server.registry))
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)

        # Save all entities using a single backend operation
        try:
            id_list = self.server.backend.save_entities(entities, id_prefix=path, user=user)
        except ServerBackend.ServerBackendError as e:
            print e
            return hrc.SERVER_ERROR()

        # Response is a list of locations
        dao_list = []
        for entity_id in id_list:
            dao_list.append(DataObject(location=entity_id))

        # Render response
        headers, body = renderer.render(dao_list)

        # Set Location header to the first ID
        headers.append(('Location', id_list[0]))

        return HttpResponse(headers, body)

    def _collection_action(self, request, path, user=None):
        return hrc.NOT_IMPLEMENTED()

    def put(self, request, path, user=None):
        """Add resource instance to Mixin collection"""
        return hrc.NOT_IMPLEMENTED()

    def delete(self, request, path, user=None):
        """Remove resource instance from Mixin collection"""
        return hrc.NOT_IMPLEMENTED()

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
