
from occi.http.parser import Parser
from occi.http.renderer import Renderer

class JSONParser(Parser):
    """Parser for the application/json content type."""
    def parse(self, headers=None, body=None):
        raise NotImplemented('yet')

class JSONRenderer(Renderer):
    """Renderer for the application/json content type."""

    def render(self, objects):
        raise NotImplemented('yet')
