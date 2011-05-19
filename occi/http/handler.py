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

from occi.core import Category, Kind, Mixin, Entity
from occi.server import ServerBackend
from occi.http import get_parser, get_renderer, HttpRequest, HttpResponse
from occi.http.header import HttpHeaderError
from occi.http.parser import ParserError
from occi.http.renderer import RendererError
from occi.http.dataobject import DataObject

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
    def NO_CONTENT(self, msg=''):
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
            parser = get_parser(request.content_type,
                    translator=self.translator)
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

    def _filter_entities(self, categories=None, attributes=None, dao_filter=None, user=None):
        """Filter entity objects from backend."""
        category_filter = categories or []      # FIXME - copy?
        attribute_filter = attributes or []

        # Category and attribute filters
        if dao_filter:
            dao = dao_filter[0]
            dao.translator = self.translator
            for category in dao.categories:
                try:
                    category_filter.append(self.server.registry.lookup_id(category))
                except Category.DoesNotExist as e:
                    return hrc.BAD_REQUEST(e)
            # FIXME - what about converting value to indicated type?
            attribute_filter.extend(dao.attributes)
        try:
            return self.server.backend.filter_entities(
                    categories=category_filter,
                    attributes=attribute_filter,
                    user=user)
        except Entity.DoesNotExist as e:
            raise HttpRequestError(hrc.NOT_FOUND(e))
        except ServerBackend.InvalidOperation as e:
            raise HttpRequestError(hrc.BAD_REQUEST(e))
        except ServerBackend.ServerBackendError as e:
            print e
            raise HttpRequestError(hrc.SERVER_ERROR())

    def _save_entities(self, entities, user=None):
        """Save Entity objects to backend."""
        try:
            return self.server.backend.save_entities(entities, user=user)
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

    def get(self, request, path):
        """Retrieve a resource instance."""

        try:
            location, entity_id = path.rsplit('/', 1)
        except ValueError:
            location = None
            entity_id = path

        if location:
            location_category = self.server.registry.lookup_location(location)
        else:
            location_category = None

        try:
            parser, renderer = self._request_init(request)
            entity = self._get_entity(entity_id, user=request.user)
        except HttpRequestError as e:
            return e.response

        if (location_category and location_category != entity.occi_get_kind()
                and location_category in entity.occi_get_mixins()):
            return hrc.NOT_FOUND()

        dao = DataObject(translator=self.translator)
        dao.load_from_entity(entity)
        renderer.render(dao)

        return HttpResponse(renderer.headers, renderer.body)

    def post(self, request, entity_id):
        """Update specific resource instance or execute an Action on a resource
        instance."""
        if request.query_args:
            return self._post_action(request, entity_id)
        else:
            return self._post_update(request, entity_id)

    def _post_action(self, request, entity_id):
        """Execute an Action on a resource instance."""

        # Action query argument
        try:
            action_name = request.query_args['action'][0]
        except (KeyError, IndexError):
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

    def _post_update(self, request, entity_id):
        """Update an existing resource instance."""
        # Parse request
        try:
            parser, renderer = self._request_init(request)
            entity = self._get_entity(entity_id, user=request.user)
        except HttpRequestError as e:
            return e.response

        # Only a single data object allowed
        if not parser.objects:
            return hrc.BAD_REQUEST('No resource instance specified')
        elif len(parser.objects) > 1:
            return hrc.BAD_REQUEST('More than one resource instance specified')
        dao = parser.objects[0]
        dao.translator = self.translator

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

    def put(self, request, entity_id):
        """Replace an existing resource instance or create a new resource
        instance using the specified Entity ID.

        Links associated with an existing Resource instance are not affected by
        this operation.
        """
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

        # Populate entity object from request data
        try:
            entity = dao.save_to_entity(save_links=False,
                    category_registry=self.server.registry)
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)

        # Set Entity ID as specified in request
        entity.occi_import_attributes([('occi.core.id', entity_id)], validate=False)

        # Replace entity object in backend
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
        """Get the resource instances in the specified `Kind` collection"""

        # Lookup location path
        categories = self.server.registry.lookup_recursive(path or '')

        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Retrieve resource instances from backend
        entities = []
        try:
            for category in categories:
                if isinstance(category, Kind):
                    entities.extend(self._filter_entities(categories=[category],
                            dao_filter=parser.objects, user=request.user))
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
        """Create or update resource instance(s) OR execute an action on the
        specified collection.
        """
        # Lookup location path
        location_category = self.server.registry.lookup_location(path)

        # Action request?
        if request.query_args:
            if not location_category:
                return hrc.BAD_REQUEST('%s: not a Kind nor Mixin location' % path)
            return self._collection_action(request, location_category)

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
                # Add location category to entity dao
                if location_category:
                    dao.categories.append(location_category)
                dao.translator = self.translator

                # Entity ID specified in request?
                entity_id = None
                if dao.attributes:
                    for attr, value in dao.attributes:
                        if attr == 'occi.core.id':
                            entity_id = value
                elif dao.location:
                    entity = self.translator.to_native(dao.location)
                    if entity: entity_id = entity.id

                # Attempt to load existing Entity
                if entity_id:
                    entity = self._get_entity(entity_id, user=request.user)
                else:
                    entity = None

                # Create/update entity object
                entity = dao.save_to_entity(entity=entity, save_links=True,
                        category_registry=self.server.registry)
                entities.append(entity)

                # Add Link objects to list of modified entities
                if hasattr(entity, 'links'):
                    for link in entity.links:
                        entities.append(link)
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)
        except HttpRequestError as e:
            return e.response

        # Save all entities using a single backend operation
        try:
            entities = self._save_entities(entities, user=request.user)
        except HttpRequestError as e:
            return e.response

        # Response is a list of created/updated entities
        dao_list = []
        for entity in entities:
            dao = DataObject(translator=self.translator)
            dao.load_from_entity(entity)
            dao_list.append(dao)

        # Render response
        if len(dao_list) == 1:
            renderer.render(dao_list[0])
        else:
            renderer.render(dao_list)

        # Set Location header to the first ID
        renderer.headers.append(('Location', dao_list[0].location))

        return HttpResponse(renderer.headers, renderer.body)

    def _collection_action(self, request, category):
        return hrc.NOT_IMPLEMENTED()

    def put(self, request, path):
        """Replace all resource instances in a collection"""
        return hrc.NOT_IMPLEMENTED()

    def delete(self, request, path):
        """Remove resource instance(s) from collection. Only allowed for Mixin
        collections.
        """
        # Lookup location path
        location_category = self.server.registry.lookup_location(path)

        if isinstance(location_category, Mixin):
            try:
                self._update_mixin_collection(request, location_category, add=False)
            except HttpRequestError as e:
                return e.response
            return hrc.ALL_OK()
        return hrc.NOT_IMPLEMENTED()

    def _update_mixin_collection(self, request, mixin_category, add=True):
        # Parse request
        parser, renderer = self._request_init(request)

        # Get entities corresponding to the given locations
        entities = []
        for dao in parser.objects:
            if not dao.location:
                return hrc.BAD_REQUEST('resource instance location expected')
            entity = self.translator.to_native(dao.location)
            entity = self._get_entity(entity.id, user=request.user)
            if add:
                entity.occi_add_mixin(mixin_category)
            else:
                entity.occi_remove_mixin(mixin_category)
            entities.append(entity)

        # Save all updated entities using a single backend operation
        try:
            self._save_entities(entities, user=request.user)
        except HttpRequestError as e:
            return e.response

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

    def put(self, request):
        """Http PUT not valid for the discovery interface."""
        return hrc.BAD_REQUEST()

    def post(self, request):
        """Create user-defined Mixin instance(s)"""
        # Parse request and extract Mixin defs
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Any Mixin defs supplied?
        if not parser.objects:
            return hrc.BAD_REQUEST('No Mixin definition(s) supplied')

        # Extract Mixin definitions
        mixins = []
        try:
            for category in parser.objects[0].categories:
                # Required parameters
                if not hasattr(category, 'related'):
                    return hrc.BAD_REQUEST('"%s": not a Mixin' % category)
                if not hasattr(category, 'location') or not category.location:
                    return hrc.BAD_REQUEST('"%s": location must be specified' % category)

                # Mixin must not exist
                try:
                    self.server.registry.lookup_id(category)
                except Category.DoesNotExist:
                    pass
                else:
                    return hrc.BAD_REQUEST('%s: Category already exist' % category)

                # Mixin location must not be used
                location = self.translator.url_strip(category.location)
                if self.server.registry.lookup_location(location):
                    return hrc.BAD_REQUEST('%s: conflicting location path' % location)

                # Create Mixin instance
                mixin = Mixin(category.term, category.scheme,
                        userdefined=True,
                        related=category.related, location=location)
                mixins.append(mixin)
        except Category.Invalid as e:
            return hrc.BAD_REQUEST(e)

        # Store Mixins in backend and save to Category registry
        try:
            for mixin in mixins:
                mixin = self.server.backend.add_user_mixin(mixin, user=request.user)
                try:
                    # FIXME: locking needed to avoid race condition
                    self.server.registry.register(mixin)
                except Category.Invalid as e:
                    self.server.backend.remove_user_mixin(mixin, user=request.user)
                    return hrc.BAD_REQUEST(e)
        except ServerBackend.InvalidOperation as e:
            return hrc.BAD_REQUEST(e)
        except ServerBackend.ServerBackendError as e:
            print e
            return hrc.SERVER_ERROR()
        except NotImplementedError as e:
            return hrc.NOT_IMPLEMENTED(e)

        return hrc.ALL_OK()

    def delete(self, request):
        """Remove user-defined Mixin instance(s)"""
        # Parse request and extract Mixin defs
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Any Mixin defs supplied?
        if not parser.objects:
            return hrc.BAD_REQUEST('No Mixin definition(s) supplied')

        # Extract Mixin definitions
        mixins = []
        try:
            for category in parser.objects[0].categories:
                # Find Mixin in registry
                try:
                    mixin = self.server.registry.lookup_id(category)
                except Category.DoesNotExist:
                    return hrc.BAD_REQUEST('%s: does not exist' % category)

                if not hasattr(mixin, 'userdefined') or not mixin.userdefined:
                    return hrc.BAD_REQUEST('%s: not a user-defined Mixin' % mixin)
                mixins.append(mixin)
        except Category.Invalid as e:
            return hrc.BAD_REQUEST(e)

        # Remove Mixins from backend and Category registry
        try:
            for mixin in mixins:
                self.server.backend.remove_user_mixin(mixin, user=request.user)
                try:
                    self.server.registry.unregister(mixin)
                except Category.Invalid as e:
                    return hrc.BAD_REQUEST(e)
        except ServerBackend.InvalidOperation as e:
            return hrc.BAD_REQUEST(e)
        except ServerBackend.ServerBackendError as e:
            print e
            return hrc.SERVER_ERROR()
        except NotImplementedError as e:
            return hrc.NOT_IMPLEMENTED(e)

        return hrc.ALL_OK()
