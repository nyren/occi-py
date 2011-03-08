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
            (self.base_path + r"/-/", TornadoRequestHandler,
                dict(handler=DiscoveryHandler(self.server, translator=self.translator))),
            (self.base_path + r"/", TornadoRequestHandler,
                dict(handler=CollectionHandler(self.server, translator=self.translator), args=[''])),
            (self.base_path + r"/(.+/)", TornadoRequestHandler,
                dict(handler=CollectionHandler(self.server, translator=self.translator))),
            (self.base_path + r"/(.+[^/])", TornadoRequestHandler,
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

    http_server = TornadoHttpServer(server, base_url='/api')
    http_server.run()
