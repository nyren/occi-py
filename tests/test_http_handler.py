from utils import unittest

from occi.server import OCCIServer, DummyBackend
from occi.http.handler import (HttpRequest, HttpResponse, DiscoveryHandler,
        EntityHandler, CollectionHandler)
from occi.ext.infrastructure import *


class HandlerTestCaseBase(unittest.TestCase):

    def setUp(self):
        # OCCI Server
        server = OCCIServer(backend=DummyBackend())
        self.server = server

        # Register Resource types
        server.registry.register(ComputeKind)
        server.registry.register(NetworkKind)
        server.registry.register(IPNetworkMixin)
        server.registry.register(StorageKind)

        # Register Link types
        server.registry.register(NetworkInterfaceKind)
        server.registry.register(IPNetworkInterfaceMixin)
        server.registry.register(StorageLinkKind)

        # Pre-populate backend: Compute Resources
        entities = []
        e = ComputeKind.entity_type(ComputeKind)
        attrs = [('title', 'A "little" VM'), ('occi.compute.state', 'inactive')]
        attrs.append(('occi.compute.memory', 5.0/3))
        e.set_occi_attributes(attrs, validate=False)
        e.occi_set_applicable_action(ComputeStartActionCategory)
        entities.append(e)
        #
        e = ComputeKind.entity_type(ComputeKind)
        attrs = [('title', 'Another " VM'), ('occi.compute.state', 'active')]
        attrs.append(('occi.compute.speed', '2.33'))
        attrs.append(('occi.compute.memory', '4.0'))
        e.set_occi_attributes(attrs, validate=False)
        e.occi_set_applicable_action(ComputeStopActionCategory)
        entities.append(e)
        #
        self.compute_id = server.backend.save_entities(entities)

        # Pre-populate backend: Network Resources
        entities = []
        e = NetworkKind.entity_type(NetworkKind)
        e.add_occi_mixin(IPNetworkMixin)
        attrs = [('title', 'Internet'), ('occi.network.state', 'active')]
        attrs.append(('occi.network.address', '11.12.0.0/16'))
        attrs.append(('occi.network.gateway', '11.12.0.1'))
        attrs.append(('occi.network.allocation', 'static'))
        e.set_occi_attributes(attrs, validate=False)
        entities.append(e)
        #
        e = NetworkKind.entity_type(NetworkKind)
        attrs = [('title', 'Private VLAN'), ('occi.network.state', 'active')]
        attrs.append(('occi.network.vlan', 123))
        e.set_occi_attributes(attrs, validate=False)
        entities.append(e)
        #
        self.network_id = server.backend.save_entities(entities)

        # Pre-populate backend: Storage Resources
        entities = []
        e = StorageKind.entity_type(StorageKind)
        attrs = [('title', 'SAN'), ('occi.storage.size', 1500.0), ('occi.storage.state', 'active')]
        entities.append(e)
        #
        self.storage_id = server.backend.save_entities(entities)

        # Pre-populate backend: Links
        entities = []
        e = NetworkInterfaceKind.entity_type(NetworkInterfaceKind)
        e.add_occi_mixin(IPNetworkInterfaceMixin)
        attrs = [('title', 'Primary Interface'), ('occi.networkinterface.state', 'active')]
        attrs.append(('occi.networkinterface.interface', 'eth0'))
        attrs.append(('occi.networkinterface.mac', '00:11:22:33:44:55'))
        attrs.append(('occi.networkinterface.ip', '11.12.13.14'))
        attrs.append(('occi.networkinterface.allocation', 'static'))
        attrs.append(('source', self.compute_id[0]))
        attrs.append(('target', self.network_id[0]))
        e.set_occi_attributes(attrs, validate=False)
        entities.append(e)
        #
        e = StorageLinkKind.entity_type(StorageLinkKind)
        attrs = [('title', 'Boot drive'), ('occi.storagelink.state', 'active')]
        attrs.append(('occi.storagelink.deviceid', 'ide:0:0'))
        attrs.append(('source', self.compute_id[0]))
        attrs.append(('target', self.storage_id[0]))
        e.set_occi_attributes(attrs, validate=False)
        entities.append(e)
        #
        self.link_id = server.backend.save_entities(entities)

        self.entity_ids = self.compute_id + self.network_id + self.storage_id + self.link_id

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
        value = '%s; scheme="%s"; class="%s"; rel="%s"; title="%s"' % (
                category.term, category.scheme, cat_class, category.related,
                category.title)
        if body_rendering:
            return 'Category: ' + value
        return ('Category', value)

class EntityHandlerTestCase(HandlerTestCaseBase):
    def setUp(self):
        super(EntityHandlerTestCase, self).setUp()
        self.handler = EntityHandler(self.server)

    def _get(self, entity_id=None, accept_header=None):
        entity_id = entity_id or self.compute_id[0]
        request_headers = []
        if accept_header:
            request_headers.append(('accept', accept_header))
        request = HttpRequest(request_headers, '')
        response = self.handler.get(request, entity_id)
        return response

    def test_get(self):
        response = self._get()
        self.assertEqual(response.headers[0], ('Content-Type', 'text/plain'))

    def test_get__text_occi(self):
        response = self._get(accept_header='text/occi')
        self.assertEqual(response.body, '')
        self.assertEqual(response.headers[0], ('Content-Type', 'text/occi'))
        self.assertEqual(len(response.headers), 6)

    def test_get__text_plain(self):
        response = self._get(accept_header='text/plain')
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])
        self.assertNotEqual(response.body, '')

    def test_get__text_urilist(self):
        response = self._get(accept_header='text/uri-list')
        self.assertEqual(response.headers, [('Content-Type', 'text/uri-list')])
        self.assertEqual(response.body[:44], self.compute_id[0])

    def test_get__text_any(self):
        response = self._get(accept_header='text/*, */*;q=0.1')
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])
        expected_body = []
        expected_body.append(self._category_header(ComputeKind))
        expected_body.append('Link: <%s?action=start>; rel="http://schemas.ogf.org/occi/infrastructure/compute/action#start"; title="Start Compute Resource"' % self.compute_id[0])
        expected_body.append('X-OCCI-Attribute: title="A \\"little\\" VM"')
        expected_body.append('X-OCCI-Attribute: occi.compute.memory="%s"' % (5.0/3))
        expected_body.append('X-OCCI-Attribute: occi.compute.state="inactive"')
        self._verify_body(response.body, expected_body)

    def test_post(self):
        """Action"""
        request_headers = []
        request_headers.append(('Category', 'stop; scheme="http://schemas.ogf.org/occi/infrastructure/compute/action#'))
        request_headers.append(('x-occi-attribute', 'method="acpioff"'))
        request = HttpRequest(request_headers, '', query_args={'action': 'stop'})
        response = self.handler.post(request, self.compute_id[0])
        self.assertEqual(response.status, 501)

    def test_post_nonexisting(self):
        request = HttpRequest([], '')
        response = self.handler.post(request, 'blah/not/found')
        self.assertEqual(response.status, 501)

    def test_put(self):
        entity_id = self.compute_id[1]
        request_body = ''
        request_body += 'x-occi-attribute: occi.compute.cores=3\n'
        request_body += 'x-occi-attribute: occi.compute.speed=3.26, occi.compute.memory=2.0\n'
        request = HttpRequest([], request_body, content_type='text/plain')
        response = self.handler.put(request, entity_id)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/plain; charset=utf-8')])
        self.assertEqual(response.body, 'OK')

        get_response = self._get(entity_id=entity_id, accept_header='text/plain')
        expected_body = []
        expected_body.append(self._category_header(ComputeKind))
        expected_body.append('Link: <%s?action=stop>; rel="http://schemas.ogf.org/occi/infrastructure/compute/action#stop"; title="Stop Compute Resource"' % self.compute_id[1])
        expected_body.append('X-OCCI-Attribute: title="Another \\" VM"')
        expected_body.append('X-OCCI-Attribute: occi.compute.cores="3"')
        expected_body.append('X-OCCI-Attribute: occi.compute.speed="3.26"')
        expected_body.append('X-OCCI-Attribute: occi.compute.memory="2.0"')
        expected_body.append('X-OCCI-Attribute: occi.compute.state="active"')
        self._verify_body(get_response.body, expected_body)

    def test_put_nonexisting(self):
        request = HttpRequest([], '')
        response = self.handler.put(request, 'blah/not/found')
        self.assertEqual(response.status, 404)

    def test_delete(self):
        entity_id = self.compute_id[0]
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
        self.handler = CollectionHandler(self.server)

    def _get(self, path='', headers=[], body=''):
        request = HttpRequest(headers, body)
        response = self.handler.get(request, path)
        return response

    def test_get_all_default(self):
        response = self._get('')
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/uri-list')])

    def test_get_all_text_occi(self):
        response = self._get('', headers=[('accept', 'text/occi')])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers[0], ('Content-Type', 'text/occi'))

        expected_headers = []
        for entity_id in self.entity_ids:
            expected_headers.append(('X-OCCI-Location', entity_id))
        self._verify_headers(response.headers[1:], expected_headers)

    def test_get_all_text_any(self):
        response = self._get('', headers=[('accept', 'text/*')])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/uri-list')])

        expected_body = []
        for entity_id in self.entity_ids:
            expected_body.append(entity_id)
        self._verify_body(response.body, expected_body)

    def test_get_all_text_plain(self):
        response = self._get('', headers=[('accept', 'text/plain')])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])

        expected_body = []
        for entity_id in self.entity_ids:
            expected_body.append('X-OCCI-Location: %s' % entity_id)
        self._verify_body(response.body, expected_body)

    def test_get_filter_compute_location(self):
        response = self._get(ComputeKind.location, headers=[('accept', 'text/plain')])
        expected_body = []
        for entity_id in self.compute_id:
            expected_body.append('X-OCCI-Location: %s' % entity_id)
        self._verify_body(response.body, expected_body)

    def test_get_filter_compute_category(self):
        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'compute; scheme=http://schemas.ogf.org/occi/infrastructure#'))
        response = self._get('', headers=request_headers)
        expected_body = []
        for entity_id in self.compute_id:
            expected_body.append('X-OCCI-Location: %s' % entity_id)
        self._verify_body(response.body, expected_body)

    def test_get_filter_compute_attr(self):
        request_headers = [('accept', 'text/plain')]
        request_headers.append(('Category', 'compute; scheme=http://schemas.ogf.org/occi/infrastructure#'))
        request_headers.append(('x-occi-attribute', 'occi.compute.memory=4.0'))
        response = self._get('', headers=request_headers)

        expected_body = []
        expected_body.append('X-OCCI-Location: %s' % self.compute_id[1])
        self._verify_body(response.body, expected_body)
