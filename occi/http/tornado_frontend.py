import tornado.web

import occi
from occi.http.handler import HttpRequest, EntityHandler, CollectionHandler, DiscoveryHandler

class OCCIHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, handler=None, args=None):
        super(OCCIHandler, self).__init__(application, request)
        self.handler = handler
        self.args = args

    def _handle_request(self, verb, *args):
        request = HttpRequest(
                self.request.headers.iteritems(),
                self.request.body,
                content_type=self.request.headers.get('Content-Type'),
                query_args=self.request.arguments)

        if self.args:
            args = self.args
        response = getattr(self.handler, verb)(request, *args)

        # Status code of response
        self.set_status(response.status)

        # Response Headers
        for name, value in response.headers:
            self.set_header(name, value)

        # Set Server header
        self.set_header('Server', 'occi-py/%s OCCI/1.1' % occi.version)

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

from occi.server import OCCIServer, DummyBackend
from occi.ext.infrastructure import *
server = OCCIServer(backend=DummyBackend())
server.registry.register(ComputeKind)
server.registry.register(StorageKind)
server.registry.register(StorageLinkKind)

application = tornado.web.Application([
    (r"/api/-/", OCCIHandler, dict(handler=DiscoveryHandler(server))),
    (r"/api/", OCCIHandler, dict(handler=CollectionHandler(server), args=[''])),
    (r"/api/(.+/)", OCCIHandler, dict(handler=CollectionHandler(server))),
    (r"/api/(.+[^/])", OCCIHandler, dict(handler=EntityHandler(server))),
    ])

if __name__ == '__main__':
    import tornado.httpserver
    import tornado.ioloop
    import tornado.options
    from tornado.options import define, options
    define("port", default=8888, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
