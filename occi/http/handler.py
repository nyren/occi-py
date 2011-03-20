from occi.core import Entity
from occi.server import ServerBackend
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

class HttpRequestError(Exception):
    """Exception wrapper for returning a proper HTTP response if an error
    occurs."""
    def __init__(self, response=None):
        assert(isinstance(response, HttpResponse))
        self.response = response
    def __str__(self):
        return repr(self.response)

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
    """HTTP handler base class."""

    def __init__(self, server, translator=None):
        self.server = server            # OCCIServer
        self.translator = translator    # URLTranslator

    def _request_init(self, request):
        """Parse request and initialize response renderer."""
        try:
            parser = get_parser(request.content_type)
            parser.parse(request.headers, request.body)
        except (ParserError, HttpHeaderError) as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))

        # Get renderer
        try:
            renderer = get_renderer(parser.accept_types)
        except RendererError as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))

        return parser, renderer

    def _get_entity(self, entity_id, user=None):
        """Load entity object from backend."""
        try:
            return self.server.backend.get_entity(entity_id, user=user)
        except Entity.DoesNotExist as e:
            raise HttpRequestError(hrc.NOT_FOUND(e))
        except ServerBackend.InvalidOperation as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))
        except ServerBackend.ServerBackendError as e:
            print e
            raise HttpRequestError(hrc.SERVER_ERROR())

    def _filter_entities(self, categories=None, attributes=None, id_prefix=None, user=None):
        """Filter entity objects from backend."""
        try:
            return self.server.backend.filter_entities(
                    categories=categories, attributes=attributes,
                    id_prefix=id_prefix, user=user)
        except Entity.DoesNotExist as e:
            raise HttpRequestError(hrc.NOT_FOUND(e))
        except ServerBackend.InvalidOperation as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))
        except ServerBackend.ServerBackendError as e:
            print e
            raise HttpRequestError(hrc.SERVER_ERROR())

    def _save_entities(self, entities, id_prefix=None, user=None):
        """Save Entity objects to backend."""
        try:
            return self.server.backend.save_entities(entities, id_prefix=id_prefix, user=user)
        except Entity.DoesNotExist as e:
            raise HttpRequestError(hrc.NOT_FOUND(e))
        except ServerBackend.InvalidOperation as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))
        except ServerBackend.ServerBackendError as e:
            print e
            raise HttpRequestError(hrc.SERVER_ERROR())

    def _delete_entities(self, entity_ids, user=None):
        """Delete Entity IDs from backend."""
        try:
            return self.server.backend.delete_entities(entity_ids, user=user)
        except Entity.DoesNotExist as e:
            raise HttpRequestError(hrc.NOT_FOUND(e))
        except ServerBackend.InvalidOperation as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))
        except ServerBackend.ServerBackendError as e:
            print e
            raise HttpRequestError(hrc.SERVER_ERROR())

    def _exec_action(self, action, entity, payload=None, user=None):
        """Instruct backend to execute Action on the given Entity."""
        try:
            return self.server.backend.exec_action(action, entity, payload=payload, user=user)
        except Entity.DoesNotExist as e:
            raise HttpRequestError(hrc.NOT_FOUND(e))
        except ServerBackend.InvalidOperation as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))
        except ServerBackend.ServerBackendError as e:
            print e
            raise HttpRequestError(hrc.SERVER_ERROR())

class EntityHandler(HandlerBase):
    """HTTP handler for existing Entity instances."""

    def get(self, request, entity_id):
        """Retrieve a resource instance."""
        try:
            parser, renderer = self._request_init(request)
            entity = self._get_entity(entity_id, user=request.user)
        except HttpRequestError as e:
            return e.response

        dao = DataObject(translator=self.translator)
        dao.load_from_entity(entity)
        renderer.render(dao)

        return HttpResponse(renderer.headers, renderer.body)

    def post(self, request, entity_id):
        """Execute an Action on a resource instance."""

        # Action query argument
        try:
            action_name = request.query_args['action']
        except KeyError:
            return hrc.BAD_REQUEST('Missing action query parameter')

        # Get instance
        try:
            parser, renderer = self._request_init(request)
            entity = self._get_entity(entity_id, user=request.user)
        except HttpRequestError as e:
            return e.response

        # Only a single data object allowed
        if not parser.objects:
            return hrc.BAD_REQUEST('No action instance specified')
        elif len(parser.objects) > 1:
            return hrc.BAD_REQUEST('More than one action instance specified')
        dao = parser.objects[0]
        dao.translator = self.translator

        # Create Action instance
        try:
            action = dao.save_as_action(category_registry=self.server.registry)
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)

        # Verify Action query param
        if action.category.term != action_name:
            return hrc.BAD_REQUEST('%s: query parameter mismatch action category' % action_name)

        # Verify Action is applicable
        if not entity.occi_is_applicable_action(action.category):
            return hrc.BAD_REQUEST('%s: action not applicable' % action_name)

        # Execute Action
        try:
            body = self._exec_action(action, entity, payload=request.body, user=request.user)
        except HttpRequestError as e:
            return e.response

        # Build response
        headers = []
        if body:
            headers.append(('Content-Type', 'application/octet-stream'))
            response = HttpResponse(headers, body)
        else:
            response = hrc.ALL_OK()
        return response

    def put(self, request, entity_id):
        """Update an existing resource instance."""
        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Only a single data object allowed
        if not parser.objects:
            return hrc.BAD_REQUEST('No resource instance specified')
        elif len(parser.objects) > 1:
            return hrc.BAD_REQUEST('More than one resource instance specified')
        dao = parser.objects[0]
        dao.translator = self.translator

        # Load entity object from backend
        try:
            entity = self._get_entity(entity_id, user=request.user)
        except HttpRequestError as e:
            return e.response

        # Update entity object from request data
        try:
            dao.save_to_entity(entity=entity,
                    category_registry=self.server.registry)
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)

        # Save the updated entity object
        try:
            id_list = self._save_entities([entity], user=request.user)
        except HttpRequestError as e:
            return e.response

        return hrc.ALL_OK()

    def delete(self, request, entity_id):
        """Delete a resource instance."""
        try:
            parser, renderer = self._request_init(request)
            self._delete_entities([entity_id])
        except HttpRequestError as e:
            return e.response

        return hrc.ALL_OK()

class CollectionHandler(HandlerBase):
    """HTTP handler for collections."""

    def get(self, request, path):
        """Get the collection of resource instances under the specified path."""
        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Filtering parameters
        categories = []
        attributes = []
        id_prefix = None

        # Can path be mapped to a Kind/Mixin location?
        t = self.server.registry.lookup_location(path)
        if t:
            categories.append(t)
        else:
            id_prefix = path.lstrip('/')

        # Category and attribute filters
        if parser.objects:
            dao = parser.objects[0]
            dao.translator = self.translator
            for category in dao.categories:
                try:
                    categories.append(self.server.registry.lookup_id(category))
                except Category.DoesNotExist as e:
                    return hrc.BAD_REQUEST(e)
            # FIXME - what about converting value to indicated type?
            attributes = dao.attributes

        # Retrieve resource instances from backend
        try:
            entities = self._filter_entities(categories=categories, attributes=attributes,
                    id_prefix=id_prefix, user=request.user)
        except HttpRequestError as e:
            return e.response

        # Render response
        objects = []
        for entity in entities:
            dao = DataObject(translator=self.translator)
            dao.load_from_entity(entity)
            objects.append(dao)
        renderer.render(objects)

        return HttpResponse(renderer.headers, renderer.body)

    def post(self, request, path):
        """Create new resource instance(s) OR execute an action on the specified
        collection.
        """
        # Action request?
        if request.query_args:
            return self._collection_action(request, path, user=user)

        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Any data-objects submitted?
        if not parser.objects:
            return hrc.BAD_REQUEST('No resource instance(s) specified')

        # Convert request objects to entity instances
        entities = []
        try:
            for dao in parser.objects:
                dao.translator = self.translator
                entities.append(dao.save_to_entity(
                    category_registry=self.server.registry))
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)
        except Entity.EntityError as e:
            return hrc.BAD_REQUEST(e)

        # Save all entities using a single backend operation
        try:
            id_list = self._save_entities(entities, id_prefix=path, user=request.user)
        except HttpRequestError as e:
            return e.response

        # Response is a list of locations
        dao_list = []
        for entity_id in id_list:
            dao_list.append(DataObject(
                location=self.translator.from_native(entity_id)))

        # Render response
        renderer.render(dao_list)

        # Set Location header to the first ID
        renderer.headers.append(('Location', self.translator.from_native(id_list[0])))

        return HttpResponse(renderer.headers, renderer.body)

    def _collection_action(self, request, path):
        return hrc.NOT_IMPLEMENTED()

    def put(self, request, path):
        """Add resource instance to Mixin collection"""
        return hrc.NOT_IMPLEMENTED()

    def delete(self, request, path):
        """Remove resource instance from Mixin collection"""
        return hrc.NOT_IMPLEMENTED()

class DiscoveryHandler(HandlerBase):
    """HTTP handler for the OCCI discovery interface."""

    def get(self, request):
        """List all Category instance registered in the system"""
        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        dao = DataObject(translator=self.translator,
                categories=self.server.registry.all())
        dao.render_flags['category_discovery'] = True

        # Render response
        renderer.render(dao)
        return HttpResponse(renderer.headers, renderer.body)

    def post(self, request):
        """Http POST not valid for the discovery interface."""
        return hrc.BAD_REQUEST()

    def put(self, request):
        """Create a custem Mixin instance"""
        return hrc.NOT_IMPLEMENTED()

    def delete(self, request):
        """Remove a custem Mixin instance"""
        return hrc.NOT_IMPLEMENTED()
