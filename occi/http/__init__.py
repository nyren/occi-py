import occi
from occi.http.parser import get_parser, register_parser, unregister_parser
from occi.http.renderer import get_renderer, register_renderer, unregister_renderer
from occi.http.dataobject import URLTranslator

# HTTP version string for use in Server/Client headers
version_string = 'occi-py/%s OCCI/%s' % (occi.version, occi.http_version)

class HttpServer(object):
    def __init__(self, occi_server,
            listen_address=None, listen_port=None,
            base_url=None):
        self.server = occi_server
        self.address = listen_address
        self.port = listen_port or 8000
        self.translator = URLTranslator(base_url or '')
        self.base_url = self.translator.base_url
        self.base_path = self.translator.base_path

    def run(self):
        raise NotImplementedError

class HttpClient(object):
    def __init__(self, occi_client,
            base_url=None):
        self.client = occi_client
        self.base_url = base_url

