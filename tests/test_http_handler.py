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

        # Pre-populate backend
        entities = []
        e = ComputeKind.entity_type(ComputeKind)
        attrs = [('title', 'A "little" VM'), ('occi.compute.memory', 5.0/3)]
        e.set_occi_attributes(attrs)
        entities.append(e)
        #
        e = ComputeKind.entity_type(ComputeKind)
        attrs = [('title', 'Another " VM'), ('occi.compute.speed', '2.33'), ('occi.compute.memory', '4.0')]
        e.set_occi_attributes(attrs)
        entities.append(e)

        self.compute_id = server.backend.save_entities(entities)

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
        self.assertEqual(response.body, '')
        self.assertEqual(len(response.headers), 4)

    def test_get__text_occi(self):
        response = self._get(accept_header='text/occi')
        self.assertEqual(response.body, '')
        self.assertEqual(response.headers[0], ('Content-Type', 'text/occi'))
        self.assertEqual(len(response.headers), 4)

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
        expected_body.append('X-OCCI-Attribute: title="A \\"little\\" VM"')
        expected_body.append('X-OCCI-Attribute: occi.compute.memory="%s"' % (5.0/3))
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
        expected_body.append('X-OCCI-Attribute: title="Another \\" VM"')
        expected_body.append('X-OCCI-Attribute: occi.compute.cores="3"')
        expected_body.append('X-OCCI-Attribute: occi.compute.speed="3.26"')
        expected_body.append('X-OCCI-Attribute: occi.compute.memory="2.0"')
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
