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

import uuid
from utils import unittest

from occi.backend.dummy import DummyBackend
from occi.http.handler import (HttpRequest, HttpResponse, DiscoveryHandler,
        EntityHandler, CollectionHandler)
from occi.http.dataobject import URLTranslator
from occi.ext.infrastructure import *


class HandlerTestCaseBase(unittest.TestCase):
    BASE_URL = '/api'

    def setUp(self):
        # OCCI Server Backend
        backend = DummyBackend()
        self.backend = backend

        # URL Translator
        self.translator = URLTranslator(self.BASE_URL)

        # Register Resource types
        backend.registry.register(ComputeKind)
        backend.registry.register(NetworkKind)
        backend.registry.register(IPNetworkMixin)
        backend.registry.register(StorageKind)

        # Register Link types
        backend.registry.register(NetworkInterfaceKind)
        backend.registry.register(IPNetworkInterfaceMixin)
        backend.registry.register(StorageLinkKind)

        # Pre-populate backend: Compute Resources
        entities = []
        e = ComputeKind.entity_type(ComputeKind)
        attrs = [('occi.core.title', 'A "little" VM'), ('occi.compute.state', 'inactive')]
        attrs.append(('occi.compute.memory', 5.0/3))
        e.occi_import_attributes(attrs, validate=False)
        e.occi_set_applicable_action(ComputeStartActionCategory)
        entities.append(e)
        #
        e = ComputeKind.entity_type(ComputeKind)
        attrs = [('occi.core.title', 'Another " VM'), ('occi.compute.state', 'active')]
        attrs.append(('occi.compute.speed', '2.33'))
        attrs.append(('occi.compute.memory', '4.0'))
        e.occi_import_attributes(attrs, validate=False)
        e.occi_set_applicable_action(ComputeStopActionCategory)
        entities.append(e)
        #
        self.computes = backend.save_entities(entities)

        # Pre-populate backend: Network Resources
        entities = []
        e = NetworkKind.entity_type(NetworkKind)
        e.occi_add_mixin(IPNetworkMixin)
        attrs = [('occi.core.title', 'Internet'), ('occi.network.state', 'active')]
        attrs.append(('occi.network.address', '11.12.0.0/16'))
        attrs.append(('occi.network.gateway', '11.12.0.1'))
        attrs.append(('occi.network.allocation', 'static'))
        e.occi_import_attributes(attrs, validate=False)
        entities.append(e)
        #
        e = NetworkKind.entity_type(NetworkKind)
        attrs = [('occi.core.title', 'Private VLAN'), ('occi.network.state', 'active')]
        attrs.append(('occi.network.vlan', 123))
        e.occi_import_attributes(attrs, validate=False)
        entities.append(e)
        #
        self.networks = backend.save_entities(entities)

        # Pre-populate backend: Storage Resources
        entities = []
        e = StorageKind.entity_type(StorageKind)
        attrs = [('occi.core.title', 'SAN'), ('occi.storage.size', 1500.0), ('occi.storage.state', 'active')]
        entities.append(e)
        #
        self.storages = backend.save_entities(entities)

        # Pre-populate backend: Links
        entities = []
        e = NetworkInterfaceKind.entity_type(NetworkInterfaceKind)
        e.occi_set_translator(self.translator)
        e.occi_add_mixin(IPNetworkInterfaceMixin)
        attrs = [('occi.core.title', 'Primary Interface'), ('occi.networkinterface.state', 'active')]
        attrs.append(('occi.networkinterface.interface', 'eth0'))
        attrs.append(('occi.networkinterface.mac', '00:11:22:33:44:55'))
        attrs.append(('occi.networkinterface.ip', '11.12.13.14'))
        attrs.append(('occi.networkinterface.allocation', 'static'))
        attrs.append(('occi.core.source', self.computes[0].id))
        attrs.append(('occi.core.target', self.networks[0].id))
        e.occi_import_attributes(attrs, validate=False)
        entities.append(e)
        #
        e = StorageLinkKind.entity_type(StorageLinkKind)
        e.occi_set_translator(self.translator)
        attrs = [('occi.core.title', 'Boot drive'), ('occi.storagelink.state', 'active')]
        attrs.append(('occi.storagelink.deviceid', 'ide:0:0'))
        attrs.append(('occi.core.source', self.computes[0].id))
        attrs.append(('occi.core.target', self.storages[0].id))
        e.occi_import_attributes(attrs, validate=False)
        entities.append(e)
        #
        self.links = backend.save_entities(entities)

        self.entities = self.computes + self.networks + self.storages + self.links

    def _loc(self, entity):
        kind = entity.occi_get_kind()
        url = self.BASE_URL + '/'
        if hasattr(kind, 'location') and kind.location:
            url += kind.location
        url += str(entity.id)
        return url

    def _verify_headers(self, response_headers=[], expected_headers=[]):
        i = 0
        while True:
            try:
                h_response = response_headers[i]
            except IndexError:
                h_response = ()
            try:
                h_expected = expected_headers[i]
            except IndexError:
                h_expected = ()

            if not h_response and not h_expected:
                break

            self.assertEqual(h_response, h_expected)
            i += 1

    def _verify_body(self, response_body='', expected_body=[]):
        i = 0
        for line in response_body.split('\r\n'):
            try:
                self.assertEqual(line, expected_body[i])
            except IndexError:
                self.assertEqual(line, '')
            i += 1

    def _category_header(self, category, body_rendering=True):
        cat_class = ''
        if isinstance(category, Kind):
            cat_class = 'kind'
        elif isinstance(category, Mixin):
            cat_class = 'mixin'
        elif isinstance(category, Category):
            cat_class = 'action'
        value = '%s; scheme="%s"; class="%s"; title="%s"' % (
                category.term, category.scheme, cat_class, category.title)
        if body_rendering:
            return 'Category: ' + value
        return ('Category', value)


class EntityHandlerTestCase(HandlerTestCaseBase):
    def setUp(self):
        super(EntityHandlerTestCase, self).setUp()
        self.handler = EntityHandler(self.backend, translator=self.translator)

    def _get(self, entity_id=None, accept_header=None):
        entity_id = entity_id or self.computes[0].id
        request_headers = []
        if accept_header:
            request_headers.append(('accept', accept_header))
        request = HttpRequest(request_headers, '')
        response = self.handler.get(request, str(entity_id))
        return response

    def test_get(self):
        response = self._get()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers[0], ('Content-Type', 'text/plain'))

    def test_get__text_occi(self):
        response = self._get(accept_header='text/*, text/occi')
        self.assertEqual(response.body, '')
        self.assertEqual(response.headers[0], ('Content-Type', 'text/occi'))
        self.assertEqual(len(response.headers), 9)

    def test_get__text_plain(self):
        response = self._get(accept_header='text/occi;q=0.5, text/plain;q=0.8')
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])
        self.assertNotEqual(response.body, '')

    def test_get__text_urilist(self):
        response = self._get(accept_header='text/plain;q=0.9, text/uri-list')
        self.assertEqual(response.headers, [('Content-Type', 'text/uri-list')])
        self.assertEqual(response.body[:44+len(self.BASE_URL)+1], self._loc(self.computes[0]))

    def test_get__text_any(self):
        response = self._get(accept_header='text/*, */*;q=0.1')
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])
        expected_body = []
        expected_body.append(self._category_header(ComputeKind))
        expected_body.append('Link: <%s>; rel="http://schemas.ogf.org/occi/infrastructure#network http://schemas.ogf.org/occi/infrastructure/network#ipnetwork"; title="Internet"; self="%s"; category="%s"; occi.core.title="Primary Interface"; occi.networkinterface.interface="eth0"; occi.networkinterface.mac="00:11:22:33:44:55"; occi.networkinterface.state="active"; occi.networkinterface.ip="11.12.13.14"; occi.networkinterface.allocation="static"' % (
            self._loc(self.networks[0]), self._loc(self.links[0]), "%s %s" % (str(NetworkInterfaceKind), str(IPNetworkInterfaceMixin))))
        expected_body.append('Link: <%s>; rel="http://schemas.ogf.org/occi/infrastructure#storage"; title=""; self="%s"; category="%s"; occi.core.title="Boot drive"; occi.storagelink.deviceid="ide:0:0"; occi.storagelink.state="active"' % (
            self._loc(self.storages[0]), self._loc(self.links[1]), str(StorageLinkKind)))
        expected_body.append('Link: <%s?action=start>; rel="http://schemas.ogf.org/occi/infrastructure/compute/action#start"; title="Start Compute Resource"' % self._loc(self.computes[0]))
        expected_body.append('X-OCCI-Attribute: occi.core.id="%s"' % self.computes[0].id.urn)
        expected_body.append('X-OCCI-Attribute: occi.core.title="A \\"little\\" VM"')
        expected_body.append('X-OCCI-Attribute: occi.compute.memory=1.67')
        expected_body.append('X-OCCI-Attribute: occi.compute.state="inactive"')
        self._verify_body(response.body, expected_body)

    def test_get_link(self):
        response = self._get(entity_id=self.links[1].id,
                accept_header='text/plain')
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])
        expected_body = []
        expected_body.append(self._category_header(StorageLinkKind))
        expected_body.append('X-OCCI-Attribute: occi.core.id="%s"' % self.links[1].id.urn)
        expected_body.append('X-OCCI-Attribute: occi.core.title="Boot drive"')
        expected_body.append('X-OCCI-Attribute: occi.core.source="%s"' % self._loc(self.computes[0]))
        expected_body.append('X-OCCI-Attribute: occi.core.target="%s"' % self._loc(self.storages[0]))
        expected_body.append('X-OCCI-Attribute: occi.storagelink.deviceid="ide:0:0"')
        expected_body.append('X-OCCI-Attribute: occi.storagelink.state="active"')
        self._verify_body(response.body, expected_body)

    def test_post_action(self):
        request_headers = []
        request_headers.append(('Category', 'stop; scheme="http://schemas.ogf.org/occi/infrastructure/compute/action#'))
        request_headers.append(('x-occi-attribute', 'method="acpioff"'))
        request = HttpRequest(request_headers, '', query_args={'action': ['stop']})
        response = self.handler.post(request, 'compute/' + str(self.computes[1].id))
        self.assertEqual(response.body, 'OK')
        self.assertEqual(response.status, 200)

    def test_post_action_not_found(self):
        request = HttpRequest([], '', query_args={'action': 'stop'})
        response = self.handler.post(request, 'blah/not/found')
        self.assertEqual(response.status, 404)

    def test_post_action_not_applicable(self):
        request_headers = []
        request_headers.append(('Category', 'start; scheme="http://schemas.ogf.org/occi/infrastructure/compute/action#'))
        request = HttpRequest(request_headers, '', query_args={'action': ['start']})
        response = self.handler.post(request, str(self.computes[1].id))
        self.assertEqual(response.status, 400)
        self.assertEqual(response.body, 'start: action not applicable')

    def test_post_update(self):
        entity = self.computes[1]
        request_headers = [('accept', 'text/*;q=0.8, text/uri-list')]
        request_body = ''
        request_body += 'x-occi-attribute: occi.compute.cores=3\n'
        request_body += 'x-occi-attribute: occi.compute.speed=3.26, occi.compute.memory=2.0\n'
        request = HttpRequest(request_headers, request_body, content_type='text/plain')
        response = self.handler.post(request, str(entity.id))
        self.assertEqual(response.body, self._loc(entity) + '\r\n')
        self.assertEqual(response.status, 200)
        expected_headers = []
        expected_headers.append(('Content-Type', 'text/uri-list'))
        expected_headers.append(('Location', self._loc(entity)))
        self._verify_headers(response.headers, expected_headers)

        get_response = self._get(entity_id=entity.id, accept_header='text/plain')
        expected_body = []
        expected_body.append(self._category_header(ComputeKind))
        expected_body.append('Link: <%s?action=stop>; rel="http://schemas.ogf.org/occi/infrastructure/compute/action#stop"; title="Stop Compute Resource"' % self._loc(self.computes[1]))
        expected_body.append('X-OCCI-Attribute: occi.core.id="%s"' % self.computes[1].id.urn)
        expected_body.append('X-OCCI-Attribute: occi.core.title="Another \\" VM"')
        expected_body.append('X-OCCI-Attribute: occi.compute.cores=3')
        expected_body.append('X-OCCI-Attribute: occi.compute.speed=3.26')
        expected_body.append('X-OCCI-Attribute: occi.compute.memory=2.00')
        expected_body.append('X-OCCI-Attribute: occi.compute.state="active"')
        self._verify_body(get_response.body, expected_body)

    def test_post_update_nonexisting(self):
        request = HttpRequest([], '')
        response = self.handler.post(request, 'blah/not/found')
        self.assertEqual(response.status, 404)

    def test_put_new(self):
        entity_id = uuid.uuid4()
        path = 'network/%s' % entity_id
        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'network; scheme=http://schemas.ogf.org/occi/infrastructure#'))
        request_headers.append(('Category', 'ipnetwork; scheme=http://schemas.ogf.org/occi/infrastructure/network#'))
        request_headers.append(('x-occi-attribute', 'occi.core.title="My VLAN"'))
        request_headers.append(('x-occi-attribute', 'occi.network.vlan=91'))
        request_headers.append(('x-occi-attribute', 'occi.network.address=192.168.1.100'))
        request_headers.append(('x-occi-attribute', 'occi.network.gateway=192.168.1.1'))
        request = HttpRequest(request_headers, '', content_type='text/occi')
        response = self.handler.put(request, self.BASE_URL + '/' + path)

        # Assume success
        self.assertEqual(response.body, 'OK')
        self.assertEqual(response.status, 200)

        return entity_id

    def test_put_existing(self):
        entity_id = self.test_put_new()

        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'network; scheme=http://schemas.ogf.org/occi/infrastructure#'))
        request_headers.append(('x-occi-attribute', 'occi.network.vlan=123'))
        request = HttpRequest(request_headers, '', content_type='text/occi')
        response = self.handler.put(request, str(entity_id))

        # Assume success
        self.assertEqual(response.body, 'OK')
        self.assertEqual(response.status, 200)

        get_response = self._get(entity_id=entity_id, accept_header='text/plain')
        expected_body = []
        expected_body.append(self._category_header(NetworkKind))
        expected_body.append('X-OCCI-Attribute: occi.core.id="%s"' % entity_id.urn)
        expected_body.append('X-OCCI-Attribute: occi.network.vlan=123')
        self._verify_body(get_response.body, expected_body)

    def test_delete(self):
        entity_id = 'compute/%s' % self.computes[0].id
        request = HttpRequest([], '')
        response = self.handler.delete(request, entity_id)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/plain; charset=utf-8')])
        self.assertEqual(response.body, 'OK')

        get_response = self._get(entity_id=entity_id)
        self.assertEqual(get_response.status, 404)

    def test_delete_nonexisting(self):
        request = HttpRequest([], '')
        response = self.handler.delete(request, 'blah/not/found')
        self.assertEqual(response.status, 404)


class CollectionHandlerTestCase(HandlerTestCaseBase):
    def setUp(self):
        super(CollectionHandlerTestCase, self).setUp()
        self.handler = CollectionHandler(self.backend, translator=self.translator)

    def _request(self, verb='get', path='', content_type=None,
            headers=[], body='', query_args=None):
        request = HttpRequest(headers, body,
                content_type=content_type, query_args=query_args)
        response = getattr(self.handler, verb)(request, path)
        return response

    def _get(self, **kwargs):
        return self._request(verb='get', **kwargs)
    def _post(self, **kwargs):
        return self._request(verb='post', **kwargs)
    def _put(self, **kwargs):
        return self._request(verb='put', **kwargs)
    def _delete(self, **kwargs):
        return self._request(verb='delete', **kwargs)

    def test_get_all_default(self):
        response = self._get()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])

    def test_get_all_text_occi(self):
        response = self._get(headers=[('accept', 'text/occi')])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers[0], ('Content-Type', 'text/occi'))

        expected_headers = []
        for entity in self.entities:
            expected_headers.append(('X-OCCI-Location', self._loc(entity)))
        self._verify_headers(response.headers[1:], expected_headers)

    def test_get_all_text_any(self):
        response = self._get(headers=[('accept', 'text/*')])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/uri-list')])

        expected_body = []
        for entity in self.entities:
            expected_body.append(self._loc(entity))
        self._verify_body(response.body, expected_body)

    def test_get_all_text_plain(self):
        response = self._get(headers=[('accept', 'text/plain')])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])

        expected_body = []
        for entity in self.entities:
            expected_body.append('X-OCCI-Location: %s' % self._loc(entity))
        self._verify_body(response.body, expected_body)

    def test_get_filter_compute_location(self):
        response = self._get(path=ComputeKind.location, headers=[('accept', 'text/plain')])
        expected_body = []
        for entity in self.computes:
            expected_body.append('X-OCCI-Location: %s' % self._loc(entity))
        self._verify_body(response.body, expected_body)

    def test_get_filter_compute_category(self):
        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'compute; scheme=http://schemas.ogf.org/occi/infrastructure#'))
        response = self._get(headers=request_headers)
        expected_body = []
        for entity in self.computes:
            expected_body.append('X-OCCI-Location: %s' % self._loc(entity))
        self._verify_body(response.body, expected_body)

    def test_get_filter_compute_attr(self):
        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'compute; scheme=http://schemas.ogf.org/occi/infrastructure#'))
        request_headers.append(('x-occi-attribute', 'occi.compute.memory=4.0'))
        response = self._get(headers=request_headers)

        expected_body = []
        expected_body.append('X-OCCI-Location: %s' % self._loc(self.computes[1]))
        self._verify_body(response.body, expected_body)

    def test_post_resource(self):
        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'compute; scheme=http://schemas.ogf.org/occi/infrastructure#'))
        request_headers.append(('x-occi-attribute', 'occi.compute.speed=2.66'))
        request_headers.append(('x-occi-attribute', 'occi.compute.memory=4.0'))
        response = self._post(path='/compute/', headers=request_headers, content_type='text/occi')

        # Assume success
        self.assertEqual(response.status, 200)

        # Location of created object
        location = None
        for header, value in response.headers:
            if header.lower() == 'location':
                location = value
        self.assertNotEqual(location, None)
        base, entity_id = location.rsplit('/', 1)
        entity_id = uuid.UUID(entity_id)

        expected_body = []
        expected_body.append(self._category_header(ComputeKind))
        expected_body.append('X-OCCI-Attribute: occi.core.id="%s"' % entity_id.urn)
        expected_body.append('X-OCCI-Attribute: occi.compute.speed=2.66')
        expected_body.append('X-OCCI-Attribute: occi.compute.memory=4.00')
        self._verify_body(response.body, expected_body)

        return location

    def test_post_resoure_required_attr(self):
        # Storage has a required attribute, see what happens
        response = self._post(path='/storage/')         # Location implies the Kind

        # Bad Request since occi.storage.size is required but not specified
        self.assertEqual(response.body, '"occi.storage.size": Required attribute')
        self.assertEqual(response.status, 400)

    def test_post_link(self):
        source = self.test_post_resource()
        target = self._loc(self.storages[0])

        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'link; scheme=http://schemas.ogf.org/occi/core#'))
        request_headers.append(('x-occi-attribute', 'occi.core.source="%s"' % source))
        request_headers.append(('x-occi-attribute', 'occi.core.target="%s"' % target))
        response = self._post(path='/', headers=request_headers)

        # Assume success
        self.assertEqual(response.status, 200)

        # Location of created object
        location = None
        for header, value in response.headers:
            if header.lower() == 'location':
                location = value
        self.assertNotEqual(location, None)
        base, entity_id = location.rsplit('/', 1)
        entity_id = uuid.UUID(entity_id)

        expected_body = []
        expected_body.append(self._category_header(LinkKind))
        expected_body.append('X-OCCI-Attribute: occi.core.id="%s"' % entity_id.urn)
        expected_body.append('X-OCCI-Attribute: occi.core.source="%s"' % source)
        expected_body.append('X-OCCI-Attribute: occi.core.target="%s"' % target)
        self._verify_body(response.body, expected_body)

    def test_post_link_invalid(self):
        source = self.test_post_resource()
        target = self._loc(self.storages[0])

        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'link; scheme=http://schemas.ogf.org/occi/core#'))
        request_headers.append(('x-occi-attribute', 'occi.core.source="$invalid"'))
        request_headers.append(('x-occi-attribute', 'occi.core.target="%s"' % target))
        response = self._post(path='/', headers=request_headers)

        # Bad Request since occi.core.source is invalid
        self.assertEqual(response.body, "occi.core.id='$invalid': invalid attribute value")
        self.assertEqual(response.status, 400)

    def test_post_action(self, path=''):
        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'start; scheme=http://schemas.ogf.org/occi/infrastructure/compute/action#'))
        response = self._post(headers=request_headers, path=path, query_args={'action': ['start']})

        # Expect bad request, action on name-space path not supported
        self.assertEqual(response.status, 400)

    def test_post_action_compute(self):
        path = self.BASE_URL + '/' + ComputeKind.location
        self.test_post_action(path=path)

    def test_post_mixin(self, path=None):
        path = path or IPNetworkMixin.location
        entity = self.networks[1]
        request_headers = [('Accept', 'text/uri-list')]
        request_body = '%s\r\n' % entity.id
        response = self._post(headers=request_headers, body=request_body,
                content_type='text/uri-list', path=path)
        expected_body = []
        expected_body.append(self._loc(entity))
        self._verify_body(response.body, expected_body)
        self.assertEqual(response.status, 200)
        entity = self.backend.get_entity(self.networks[1].id)
        self.assertEqual(str(entity.occi_list_categories()[-1]),
                str(IPNetworkMixin))

    def test_delete(self, path=None):
        path = path or IPNetworkMixin.location
        request_body = '%s\r\n' % self.networks[0].id
        response = self._delete(body=request_body,
                content_type='text/uri-list', path=path)
        self.assertEqual(response.body, 'OK')
        self.assertEqual(response.status, 200)
        entity = self.backend.get_entity(self.networks[0].id)
        self.assertEqual(len(entity.occi_list_categories()), 1)

class DiscoveryHandlerTestCase(HandlerTestCaseBase):
    def setUp(self):
        super(DiscoveryHandlerTestCase, self).setUp()
        self.handler = DiscoveryHandler(self.backend, translator=self.translator)

    def test_get(self):
        headers = [('Accept', 'text/occi')]
        request = HttpRequest(headers, '')
        response = self.handler.get(request)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, '')
        self.assertEqual(response.headers[0], ('Content-Type', 'text/occi'))
        self.assertEqual(len(response.headers), len(self.backend.registry.all()) + 1)

        expected_headers = []
        expected_headers.append(('Category', 'entity; scheme="http://schemas.ogf.org/occi/core#"; class="kind"; title="Entity type"; attributes="occi.core.id{immutable} occi.core.title"'))
        expected_headers.append(('Category', 'resource; scheme="http://schemas.ogf.org/occi/core#"; class="kind"; title="Resource type"; rel="http://schemas.ogf.org/occi/core#entity"; attributes="occi.core.summary"'))
        expected_headers.append(('Category', 'link; scheme="http://schemas.ogf.org/occi/core#"; class="kind"; title="Link type"; rel="http://schemas.ogf.org/occi/core#entity"; attributes="occi.core.source{required} occi.core.target{required}"'))
        expected_headers.append(('Category', 'compute; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"; title="Compute Resource"; rel="http://schemas.ogf.org/occi/core#resource"; attributes="%s"; actions="%s"; location="/api/compute/"' % (
            'occi.compute.architecture occi.compute.cores occi.compute.hostname occi.compute.speed occi.compute.memory occi.compute.state{immutable}',
            ' '.join([str(cat) for cat in ComputeKind.actions]))))

        self._verify_headers(response.headers[1:5], expected_headers)

    def test_post(self):
        location='my_stuff/'
        path = self.BASE_URL + '/' + location
        headers = [('Content-Type', 'text/occi')]
        headers.append(('Category', 'my_stuff; scheme="http://example.com/occi/custom#"; class=mixin; location=%s' % path))
        headers.append(('Category', 'taggy; scheme="http://example.com/occi/custom#"; class=mixin; location=taggy/'))
        request = HttpRequest(headers, '')
        response = self.handler.post(request)
        self.assertEqual(response.body, 'OK')
        self.assertEqual(response.status, 200)
        self.assertEqual(self.backend.registry.lookup_location(location),
                'http://example.com/occi/custom#my_stuff')
        self.assertEqual(self.backend.registry.lookup_location('taggy/'),
                'http://example.com/occi/custom#taggy')

    def test_delete(self):
        self.test_post()
        headers = [('Content-Type', 'text/occi')]
        headers.append(('Category', 'taggy; scheme="http://example.com/occi/custom#"'))
        request = HttpRequest(headers, '')
        response = self.handler.delete(request)
        self.assertEqual(response.body, 'OK')
        self.assertEqual(response.status, 200)
        self.assertEqual(self.backend.registry.lookup_location('my_stuff/'),
                'http://example.com/occi/custom#my_stuff')
        self.assertEqual(self.backend.registry.lookup_location('taggy/'), None)

