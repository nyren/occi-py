import re

from occi.core import Category, Kind, Mixin
from occi.http.header import HttpHeaderError, HttpHeadersBase, HttpWebHeadersBase, HttpCategoryHeaders, HttpLinkHeaders, HttpAttributeHeaders
from occi.http.dataobject import DataObject, LinkRepr

_renderers= {}

class RendererError(Exception):
    pass

def register_renderer(content_type, renderer):
    _renderers[content_type] = renderer

def unregister_renderer(content_type):
    del _renderers[content_type]

def get_renderer(accept_header=None):
    """Return a renderer matching the list of accepted content-types.

    >>> p = get_renderer('text/occi')
    >>> isinstance(p, HeaderRenderer)
    True
    >>> p = get_renderer('text/plain; q=0.1 ')
    >>> isinstance(p, TextPlainRenderer)
    True
    >>> p = get_renderer()
    >>> isinstance(p, HeaderRenderer)
    True
    >>> p = get_renderer('application/not-supported')
    Traceback (most recent call last):
        File "renderer.py", line 41, in renderer
    RendererError: "application/not-supported": No renderer found for requested content types
    """
    r = None
    if not accept_header:
        r = _renderers.get(None)
    else:
        h = HttpWebHeadersBase()
        h.parse(accept_header or '')
        for c_type, c_params in h.all():
            try:
                r = _renderers[c_type]
            except KeyError:
                pass
            else:
                break

    if not r:
        raise RendererError('"%s": No renderer found for requested content types' % accept_header)
    return r()

class Renderer(object):
    """Renderer base class.

    A Renderer must implement the render() method which renders the given
    `DataObject` or list of `DataObject`s.

    The result of the render() method is stored in the following attributes:
    :var headers: A list of HTTP Header name-value tuples
    :var body: The HTTP Body as a string

    """
    def __init__(self):
        self.headers = []
        self.body = ''

    def render(self, objects):
        """The render method doing the actual work.

        :keyword objects: A `DataObject` or a list of `DataObject` instances
        """
        raise NotImplementedError('%s: does not implement the render() method',
                self.__class__.__name__)

class HeaderRenderer(Renderer):
    """Renderer for the text/occi content type.

    >>> from occi.ext.infrastructure import ComputeKind, StorageKind
    >>> cats = [ComputeKind]
    >>> links = [LinkRepr(target_location='http://example.com/storage/345', target_categories=[StorageKind])]
    >>> attrs = [('occi.compute.memory', '2.0'), ('occi.compute.speed', '2.667')]
    >>> obj = DataObject(location='http://example.com/compute/123', categories=cats, links=links, attributes=attrs)
    >>> r = HeaderRenderer()
    >>> r.render([obj])
    >>> r.headers
    [('X-OCCI-Location', 'http://example.com/compute/123')]
    >>> r.body
    ''
    >>> r = HeaderRenderer()
    >>> r.render(obj)
    >>> r.headers
    [('Category', 'compute; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"; rel="http://schemas.ogf.org/occi/core#resource"; title="Compute Resource"'), ('Link', '<http://example.com/storage/345>; rel="http://schemas.ogf.org/occi/infrastructure#storage"; title=""'), ('X-OCCI-Attribute', 'occi.compute.memory="2.0"'), ('X-OCCI-Attribute', 'occi.compute.speed="2.667"')]

    """
    def render(self, objects):
        if isinstance(objects, list) or isinstance(objects, tuple):
            self._render_obj_list(objects)
        else:
            self._render_single_obj(objects)

    def _render_single_obj(self, obj):
        """Render a single `DataObject`.
        """
        # Category headers
        category_headers = HttpCategoryHeaders()
        for category in obj.categories:
            kwargs = {}
            kwargs['scheme'] = category.scheme
            kwargs['class'] = category.__class__.__name__.lower()

            # FIXME: this is a bug in the spec, fix it?
            if kwargs['class'] == 'category': kwargs['class'] = 'action'

            if category.related:
                kwargs['rel'] = category.related
            if category.title:
                kwargs['title'] = category.title
            category_headers.add(category.term, **kwargs)
        [self.headers.append(('Category', h)) for h in category_headers.headers()]

        # Link headers
        link_headers = HttpLinkHeaders()
        for link in obj.links:
            kwargs = {}
            kwargs['rel'] = ' '.join([str(cat) for cat in link.target_categories])
            kwargs['title'] = link.target_title or ''
            if link.link_location:
                kwargs['self'] = link.link_location
                for attr, value in link.link_attributes:
                    kwargs[attr] = value

            link_headers.add(link.target_location, **kwargs)
        [self.headers.append(('Link', h)) for h in link_headers.headers()]

        # Attribute headers
        attribute_headers = HttpAttributeHeaders()
        [attribute_headers.add(attr, value) for attr, value in obj.attributes]
        [self.headers.append(('X-OCCI-Attribute', h)) for h in attribute_headers.headers()]

    def _render_obj_list(self, objects):
        """Render a list of `DataObject` instances. Only the location of each
        `DataObject` will be displayed by the Http Header rendering.
        """
        for obj in objects:
            if not obj.location:
                raise RendererError('DataObject has no location')
            self.headers.append(('X-OCCI-Location', obj.location))

class TextPlainRenderer(Renderer):
    pass

class TextURIListRenderer(Renderer):
    pass

class TextRenderer(Renderer):
    """The default renderer. Uses text/plain for single object rendering and
    text/uri-list for multiple objects rendering.
    """
    pass

# Register required renderers
register_renderer(None, HeaderRenderer)
register_renderer('text/occi', HeaderRenderer)
register_renderer('text/plain', TextPlainRenderer)
register_renderer('text/uri-list', TextURIListRenderer)
register_renderer('text/*', TextRenderer)
register_renderer('*/*', TextRenderer)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
