#!/usr/bin/env python
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
        self.occi_set_attributes(attr_default, validate=False)

        self.occi_set_applicable_action(ComputeStartActionCategory)

    def exec_action(self, action, payload=None):
        state = self.occi_get_attribute('occi.compute.state')
        if state == 'inactive' and action.category.term == 'start':
            self.occi_set_attributes([('occi.compute.state', 'active')], validate=False)
            self.occi_set_applicable_action(ComputeStartActionCategory, applicable=False)
            self.occi_set_applicable_action(ComputeStopActionCategory, applicable=True)
        elif state == 'active' and action.category.term == 'stop':
            self.occi_set_attributes([('occi.compute.state', 'inactive')], validate=False)
            self.occi_set_applicable_action(ComputeStopActionCategory, applicable=False)
            self.occi_set_applicable_action(ComputeStartActionCategory, applicable=True)
        return None

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
