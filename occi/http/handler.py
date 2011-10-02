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

from occi import OrderedDict
from occi.core import Category, Kind, Mixin, Entity
from occi.backend import ServerBackend
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

    def __init__(self, backend, translator=None):
        self.backend = backend            # OCCI ServerBackend
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
            return self.backend.get_entity(entity_id, user=user)
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
                    category_filter.append(self.backend.registry.lookup_id(category))
                except Category.DoesNotExist as e:
                    return hrc.BAD_REQUEST(e)
            # FIXME - what about converting value to indicated type?
            attribute_filter.extend(dao.attributes)
        try:
            return self.backend.filter_entities(
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

    def _save_entities(self, entities=None, delete_entity_ids=None, user=None):
        """Save Entity objects to backend."""
        try:
            return self.backend.save_entities(entities, delete_entity_ids=delete_entity_ids, user=user)
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
            return self.backend.exec_action(action, entity, payload=payload, user=user)
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
            location_category = self.backend.registry.lookup_location(location)
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

    def post(self, request, path):
        """Update specific resource instance or execute an Action on a resource
        instance."""
        try:
            location, entity_id = path.rsplit('/', 1)
        except ValueError:
            location = None
            entity_id = path
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
            action = dao.save_as_action(category_registry=self.backend.registry)
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
                    category_registry=self.backend.registry)
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

    def put(self, request, path):
        """Replace an existing resource instance or create a new resource
        instance using the specified Entity ID.

        Links associated with an existing Resource instance are not affected by
        this operation.
        """
        try:
            location, entity_id = path.rsplit('/', 1)
        except ValueError:
            location = None
            entity_id = path

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
                    category_registry=self.backend.registry)
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

    def delete(self, request, path):
        """Delete a resource instance."""
        try:
            location, entity_id = path.rsplit('/', 1)
        except ValueError:
            location = None
            entity_id = path
        else:
            # Lookup location path
            location_category = self.backend.registry.lookup_location(location)

        try:
            parser, renderer = self._request_init(request)
            if isinstance(location_category, Mixin):
                entity = self._get_entity(entity_id, user=user)
                entity.occi_remove_mixin(location_category)
                self._save_entities([entity], user=request.user)
            else:
                self._save_entities(delete_entity_ids=[entity_id], user=request.user)
        except Entity.UnknownCategory:
            pass
        except HttpRequestError as e:
            return e.response

        return hrc.ALL_OK()

class CollectionHandler(HandlerBase):
    """HTTP handler for collections."""

    def get(self, request, path):
        """Get the resource instances in the specified collection"""

        # Lookup location path
        categories = self.backend.registry.lookup_recursive(path or '')

        # If path is not a Kind/Mixin location filter out everything but Kind
        # categories
        if len(categories) > 1:
            t = []
            for category in categories:
                if isinstance(category, Kind):
                    t.append(category)
            categories = t

        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Retrieve resource instances from backend
        entities = []
        try:
            for category in categories:
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
        location_category = self.backend.registry.lookup_location(path)

        # Action request?
        if 'action' in request.query_args:
            if not location_category:
                return hrc.BAD_REQUEST('%s: not a Kind nor Mixin location' % path)
            return self._collection_action(request, location_category)
        elif request.query_args:
            return hrc.BAD_REQUEST('Unsupported query parameters')

        return self._update_collection(request, location_category, replace=False)

    def put(self, request, path):
        """Replace all resource instances in a collection"""

        # Lookup location path
        location_category = self.backend.registry.lookup_location(path)

        if not location_category:
            return hrc.BAD_REQUEST('%s: not a Kind nor Mixin location' % path)
        return self._update_collection(request, location_category, replace=True)

    def _update_collection(self, request, location_category, replace=False):
        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Any data-objects submitted?
        if not parser.objects:
            return hrc.BAD_REQUEST('No resource instance(s) specified')

        # Entities to update and delete
        entities_updated = {}
        entities_deleted = {}

        # Only possible to replace a pure Kind/Mixin location
        if replace:
            assert(location_category)
            # When replacing the whole collection we need to:
            #  - Remove the all entities of Kind not part of the update.
            #  - Remove the Mixin from all entities not part of the update.
            try:
                if isinstance(location_category, Kind):
                    for entity in self._filter_entities(
                            categories=[location_category], user=request.user):
                        entities_deleted[entity_id] = True
                elif isinstance(location_category, Mixin):
                    for entity in self._filter_entities(
                            categories=[location_category], user=request.user):
                        try:
                            entity.occi_remove_mixin(location_category)
                        except Entity.UnknownCategory:
                            pass
                        else:
                            entities_updated[entity.id] = entity
            except HttpRequestError as e:
                return e.response

        # Convert request objects to entity instances
        try:
            for dao in parser.objects:
                # Add location category to entity dao
                if location_category:
                    dao.categories.append(location_category)
                dao.translator = self.translator

                # Get Entity ID from request
                entity_id = dao.get_entity_id()

                # COMPAT: OCCI HTTP Rendering 1.1 does not threat PUT
                # /mixin_loc/ as a resource create/replace operation.
                # Use non-replace mode as workaround.
                _do_replace = replace
                if replace and parser.specification() in ('occi-http-1.1'):
                    _do_replace = False

                # Attempt to load existing Entity
                if entity_id and not _do_replace:
                    try:
                        entity = entities_updated[entity_id]
                    except KeyError:
                        entity = self._get_entity(entity_id, user=request.user)
                else:
                    entity = None

                # Create/update entity object
                # FIXME: If replacing the entity we leave all links untouched.
                # This is according to spec but is it convenient?
                entity = dao.save_to_entity(entity=entity, save_links=(not replace),
                        category_registry=self.backend.registry)
                entities_updated[entity.id] = entity
                entities_deleted.pop(entity.id, None)

                # Add Link objects to list of modified entities
                if hasattr(entity, 'links'):
                    for link in entity.links:
                        entities_updated[link.id] = link
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)
        except HttpRequestError as e:
            return e.response

        # Save (and delete) all affected entities using a single backend operation
        try:
            entities = self._save_entities(
                    entities_updated.values(),
                    delete_entity_ids=entities_deleted.keys(),
                    user=request.user)
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

    def delete(self, request, path):
        """Remove resource instance(s) from collection."""
        # Lookup location path
        location_category = self.backend.registry.lookup_location(path)

        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        entities_updated = {}
        entities_deleted = {}
        try:
            for dao in parser.objects:
                # Get ID of Entity to be deleted from collection
                entity_id = dao.get_entity_id()
                if not entity_id:
                    continue

                if isinstance(location_category, Kind):
                    entities_deleted[entity_id]
                elif isinstance(location_category, Mixin):
                    entity = self._get_entity(entity_id, user=request.user)
                    try:
                        entity.occi_remove_mixin(location_category)
                    except Entity.UnknownCategory:
                        pass
                    else:
                        entities_updated[entity.id] = entity

            # Save/delete entities
            self._save_entities(entities_updated.itervalues(),
                    delete_entity_ids=entities_deleted.iterkeys(),
                    user=request.user)
        except DataObject.Invalid as e:
            return hrc.BAD_REQUEST(e)
        except HttpRequestError as e:
            return e.response

        return hrc.ALL_OK()

    def _collection_action(self, request, category):
        """FIXME: Implement! """
        # Try to share as much code as possible with EntityHandler._post_action()
        return hrc.ALL_OK('')

class DiscoveryHandler(HandlerBase):
    """HTTP handler for the OCCI discovery interface."""

    def get(self, request):
        """List all Category instance registered in the system"""
        # Parse request
        try:
            parser, renderer = self._request_init(request)
        except HttpRequestError as e:
            return e.response

        # Category filter
        categories = []
        if not parser.objects or not parser.objects[0].categories:
            categories = self.backend.registry.all()
        else:
            for category in parser.objects[0].categories:
                try:
                    category = self.backend.registry.lookup_id(str(category))
                except Category.DoesNotExist:
                    return hrc.NOT_FOUND('%s: Category not found' % category)
                else:
                    categories.append(category)

        dao = DataObject(translator=self.translator,
                categories=categories)
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
                    self.backend.registry.lookup_id(category)
                except Category.DoesNotExist:
                    pass
                else:
                    return hrc.BAD_REQUEST('%s: Category already exist' % category)

                # Mixin location must not be used
                location = self.translator.url_strip(category.location)
                if self.backend.registry.lookup_location(location):
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
                mixin = self.backend.add_user_category(mixin, user=request.user)
                try:
                    # FIXME: locking needed to avoid race condition
                    self.backend.registry.register(mixin)
                except Category.Invalid as e:
                    self.backend.remove_user_category(mixin, user=request.user)
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
                    mixin = self.backend.registry.lookup_id(category)
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
                self.backend.remove_user_category(mixin, user=request.user)
                try:
                    self.backend.registry.unregister(mixin)
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
