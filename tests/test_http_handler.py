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


class EntityHandlerTestCase(HandlerTestCaseBase):
    def setUp(self):
        super(EntityHandlerTestCase, self).setUp()
        self.handler = EntityHandler(self.server)

    def _get(self, accept_header=None):
        request_headers = []
        if accept_header:
            request_headers.append(('accept', accept_header))
        request = HttpRequest(request_headers, '')
        response = self.handler.get(request, self.compute_id[0])
        return response

    def test_get(self):
        response = self._get()
        self.assertEqual(response.body, '')
        self.assertEqual(len(response.headers), 3)

    def test_get__text_occi(self):
        response = self._get('text/occi')
        self.assertEqual(response.body, '')
        self.assertEqual(len(response.headers), 3)

    def test_get__text_plain(self):
        response = self._get('text/plain')
        self.assertEqual(len(response.headers), 0)
        self.assertNotEqual(response.body, '')

    def test_get__text_urilist(self):
        response = self._get('text/uri-list')
        self.assertEqual(len(response.headers), 0)
        self.assertNotEqual(response.body, '')

    def test_get__text_any(self):
        response = self._get('text/*, */*')
        self.assertEqual(len(response.headers), 0)
        self.assertNotEqual(response.body, '')

    def test_post(self):
        pass

