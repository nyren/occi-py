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

import logging
import optparse
import urlparse

import occi.core
import occi.http
from occi.backend.dummy import DummyBackend
from occi.ext.infrastructure import *
from occi.http.tornado_frontend import TornadoHttpServer
import occi.http.content_json as content_json

class Compute(occi.core.Resource):
    def __init__(self, kind, **kwargs):
        super(Compute, self).__init__(kind, **kwargs)
        attr_default = [
                ('occi.compute.architecture', 'x86_64'),
                ('occi.compute.speed', 2.67),
                ('occi.compute.memory', 1.0),
                ('occi.compute.state', 'inactive'),
        ]
        self.occi_import_attributes(attr_default, validate=False)

        self.occi_set_applicable_action(ComputeStartActionCategory)

    def exec_action(self, action, payload=None):
        state = self.occi_get_attribute('occi.compute.state')
        if state == 'inactive' and action.category.term == 'start':
            self.occi_import_attributes([('occi.compute.state', 'active')], validate=False)
            self.occi_set_applicable_action(ComputeStartActionCategory, applicable=False)
            self.occi_set_applicable_action(ComputeStopActionCategory, applicable=True)
        elif state == 'active' and action.category.term == 'stop':
            self.occi_import_attributes([('occi.compute.state', 'inactive')], validate=False)
            self.occi_set_applicable_action(ComputeStopActionCategory, applicable=False)
            self.occi_set_applicable_action(ComputeStartActionCategory, applicable=True)
        return None

def init_server(backend):
    ComputeKind.entity_type = Compute

    backend.registry.register(ComputeKind)
    backend.registry.register(NetworkKind)
    backend.registry.register(IPNetworkMixin)
    backend.registry.register(StorageKind)
    backend.registry.register(NetworkInterfaceKind)
    backend.registry.register(IPNetworkInterfaceMixin)
    backend.registry.register(StorageLinkKind)
    return backend

if __name__ == "__main__":
    parser = optparse.OptionParser( description='OCCI IaaS Demo')
    parser.add_option('-B', '--base_url', dest='base_url',
            default='http://localhost:8000/',
            help='For example "http://localhost:8000/"')
    parser.add_option('-v', '--verbose', action='count', dest='verbose', default=0,
            help="Increase verbosity level")
    (options, args) = parser.parse_args()

    if options.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif options.verbose > 1:
        logging.getLogger().setLevel(logging.DEBUG)

    # Enable JSON content type
    content_json.register()

    url = urlparse.urlparse(options.base_url)

    http_server = TornadoHttpServer(init_server(DummyBackend()),
            listen_address=url.hostname, listen_port=url.port,
            base_url=options.base_url)

    print "%s listen=%s port=%s" % (occi.http.version_string,
            http_server.address, http_server.port)
    print "base_url=%s base_path=%s" % (http_server.base_url + '/', http_server.base_path + '/')

    http_server.run()
