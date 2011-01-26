import re

from occi.core import Category, Kind, Mixin
from occi.http.header import HttpHeaderError, HttpHeadersBase, HttpCategoryHeaders, HttpLinkHeaders, HttpAttributeHeaders

_renderers= {}

class RendererError(Exception):
    pass

def renderer(accept_header=None):
    """Return a renderer matching the list of accepted content-types.
    """
    pass

def register_renderer(content_type, renderer):
    _renderers[content_type] = renderer

def unregister_renderer(content_type):
    del _renderers[content_type]

class Renderer(object):
    """Renderer base class.

    A Renderer must implement the render() method which renders the given
    entity or list of entities.

    The result of the render() method is stored in the following attributes:
    :var headers: A list of HTTP Header name-value tuples
    :var body: The HTTP Body as a string

    """
    def __init__(self):
        self.objects = []
        self.locations = []

    def render(self, entities=None):
        """The render method doing the actual work.

        :keyword entities: resource instances to render
        """
        raise NotImplementedError('%s: does not implement the render() method',
                self.__class__.__name__)

# Register required renderers
#register_renderer(None, TextPlainRenderer)
#register_renderer('text/plain', TextPlainRenderer)
#register_renderer('text/occi', HeaderRenderer)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
