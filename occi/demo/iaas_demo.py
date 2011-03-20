#!/usr/bin/env python

import argparse
import urlparse

import occi.core
from occi.server import OCCIServer, DummyBackend
from occi.ext.infrastructure import *
from occi.http.tornado_frontend import TornadoHttpServer

class Compute(occi.core.Resource):
    def __init__(self, kind, **kwargs):
        super(Compute, self).__init__(kind, **kwargs)
        attr_default = [
                ('occi.compute.architecture', 'x86_64'),
                ('occi.compute.speed', 2.67),
                ('occi.compute.memory', 1.0),
                ('occi.compute.state', 'inactive'),
        ]
        self.set_occi_attributes(attr_default, validate=False)

        self.occi_set_applicable_action(ComputeStartActionCategory)

def init_server(backend):
    ComputeKind.entity_type = Compute

    server = OCCIServer(backend=backend)
    server.registry.register(ComputeKind)
    server.registry.register(NetworkKind)
    server.registry.register(IPNetworkMixin)
    server.registry.register(StorageKind)
    server.registry.register(NetworkInterfaceKind)
    server.registry.register(IPNetworkInterfaceMixin)
    server.registry.register(StorageLinkKind)
    return server

if __name__ == "__main__":
    parser = argparse.ArgumentParser( description='OCCI IaaS Demo')
    parser.add_argument('--base_url',
            default='http://localhost:8000/',
            help='For example "http://localhost:8000/"')
    args = parser.parse_args()

    url = urlparse.urlparse(args.base_url)

    http_server = TornadoHttpServer(init_server(DummyBackend()),
            listen_address=url.hostname, listen_port=url.port,
            base_url=args.base_url)
    http_server.run()
