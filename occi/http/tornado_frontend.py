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
import re

import tornado.web
import tornado.httpserver
import tornado.ioloop

import occi
from occi.http.handler import HttpRequest, EntityHandler, CollectionHandler, DiscoveryHandler
from occi.http import HttpServer, HttpClient

class TornadoHttpServer(HttpServer):
    def __init__(self, *args, **kwargs):
        super(TornadoHttpServer, self).__init__(*args, **kwargs)

        self.application = tornado.web.Application([
            (self.base_path + r'/*/-/', TornadoRequestHandler,
                dict(handler=DiscoveryHandler(self.server, translator=self.translator))),
            (self.base_path + r'/.well-known/org/ogf/occi/-/', TornadoRequestHandler,
                dict(handler=DiscoveryHandler(self.server, translator=self.translator))),
            (self.base_path + r'/', TornadoRequestHandler,
                dict(handler=CollectionHandler(self.server, translator=self.translator), args=[''])),
            (self.base_path + r'/(.+/)', TornadoRequestHandler,
                dict(handler=CollectionHandler(self.server, translator=self.translator))),
            (self.base_path + r'/(.+[^/])', TornadoRequestHandler,
                dict(handler=EntityHandler(self.server, translator=self.translator))),
            ])

    def run(self):
        http_server = tornado.httpserver.HTTPServer(self.application)
        http_server.listen(self.port, self.address or '')
        tornado.ioloop.IOLoop.instance().start()

class TornadoRequestHandler(tornado.web.RequestHandler):
    """Tornado RequestHandler for OCCI."""
    def __init__(self, application, request, handler=None, args=None):
        super(TornadoRequestHandler, self).__init__(application, request)
        self.handler = handler
        self.args = args
        self.logger = logging.getLogger()

    def _handle_request(self, verb, *args):
        request = HttpRequest(
                self.request.headers.iteritems(),
                self.request.body,
                content_type=self.request.headers.get('Content-Type'),
                query_args=self.request.arguments)

        if self.args:
            args = self.args
        response = getattr(self.handler, verb)(request, *args)

        # Debugging
        if self.logger.isEnabledFor(logging.DEBUG):
            request_str = '%s %s HTTP/x.x\n' % (self.request.method, self.request.uri)
            request_str += '\n'.join(['%s: %s' % (h, v) for h, v in self.request.headers.iteritems()])
            request_str += '\n'
            if self.request.body:
                request_str += '\n'
                request_str += self.request.body.rstrip()
            response_str = 'HTTP/x.x %d\n' % response.status
            response_str += '\n'.join(['%s: %s' % (h, v) for h, v in response.headers])
            response_str += '\n'
            if response.body:
                response_str += '\n'
                response_str += response.body.rstrip()
            logging.debug("""%s.%s(%s): status=%d'
-------- Request ---------
%s
-------- Response --------
%s
--------------------------""" % (
                self.handler.__class__.__name__, verb, args, response.status,
                request_str, response_str,
                ))

        # Status code of response
        self.set_status(response.status)

        # Response Headers
        headers = {}
        for name, value in response.headers:
            values = headers.get(name)
            if values:
                values += ', ' + value
            else:
                values = value
            headers[name] = values
        for name, value in headers.iteritems():
            try:
                self.set_header(name, value)
            except ValueError:
                value = tornado.web._utf8(value)
                value = re.sub(r"[\x00-\x1f]", " ", value)
                self._headers[name] = value

        # Set Server header
        self.set_header('Server', occi.http.version_string)

        # Response Body
        self.write(response.body)

    def get(self, *args):
        self._handle_request('get', *args)
    def post(self, *args):
        self._handle_request('post', *args)
    def put(self, *args):
        self._handle_request('put', *args)
    def delete(self, *args):
        self._handle_request('delete', *args)


if __name__ == '__main__':
    from occi.server import OCCIServer, DummyBackend
    from occi.ext.infrastructure import *
    server = OCCIServer(backend=DummyBackend())
    server.registry.register(ComputeKind)
    server.registry.register(StorageKind)
    server.registry.register(StorageLinkKind)

    http_server = TornadoHttpServer(server, base_url='http://localhost:8000/api')
    http_server.run()
