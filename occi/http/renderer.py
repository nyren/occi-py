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

import re

from occi.core import Category, Kind, Mixin
from occi.http.header import HttpHeaderError, HttpHeadersBase, HttpWebHeadersBase, HttpCategoryHeaders, HttpLinkHeaders, HttpAttributeHeaders
from occi.http.dataobject import DataObject, LinkRepr

_renderers= {}

class RendererError(Exception):
    pass

def register_renderer(renderer, pattern=None, media_type=None, default=False):
    if default:
        pattern = None
    else:
        media_type = media_type or renderer.MEDIA_TYPE
        pattern = pattern or media_type
    _renderers[pattern] = (renderer, media_type)

def unregister_renderer(pattern):
    del _renderers[pattern]

def get_renderer(accept_types=None):
    """Return a renderer matching the list of accepted content-types.

    :keyword accept_types: List of acceptable content types, i.e. the result of
        _parsing_ an Accept header.

    >>> p = get_renderer(['text/occi'])
    >>> isinstance(p, HeaderRenderer)
    True
    >>> p = get_renderer(['text/plain'])
    >>> isinstance(p, TextPlainRenderer)
    True
    >>> p = get_renderer()
    >>> isinstance(p, TextPlainRenderer)
    True
    >>> p = get_renderer(['text/*'])
    >>> isinstance(p, TextRenderer)
    True
    >>> p = get_renderer(['text/html', '*/*'])
    >>> isinstance(p, TextPlainRenderer)
    True
    >>> p = get_renderer(['text/html', 'image/jpeg', 'image/png'])
    Traceback (most recent call last):
        File "renderer.py", line 41, in renderer
    RendererError: No renderer found for requested media types
    """
    renderer = None
    if not accept_types:
        renderer, media_type = _renderers.get(None)
    else:
        for pattern in accept_types:
            try:
                renderer, media_type = _renderers[pattern]
            except KeyError:
                pass
            else:
                break

    if not renderer:
        raise RendererError('No renderer found for requested media types')
    return renderer(media_type=media_type)

class Renderer(object):
    """Renderer base class.

    A Renderer must implement the render() method which renders the given
    `DataObject` or list of `DataObject`s.

    The result of the render() method is stored in the following attributes:
    :var headers: A list of HTTP Header name-value tuples
    :var body: The HTTP Body as a string

    """
    MEDIA_TYPE = 'text/plain'

    def __init__(self, media_type=None):
        self.media_type = media_type or self.MEDIA_TYPE
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
    [('Content-Type', 'text/occi; charset=utf-8'), ('X-OCCI-Location', 'http://example.com/compute/123')]
    >>> r.body
    ''
    >>> r = HeaderRenderer()
    >>> r.render(obj)
    >>> r.headers
    [('Content-Type', 'text/occi; charset=utf-8'), ('Category', 'compute; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"; title="Compute Resource"'), ('Link', '<http://example.com/storage/345>; rel="http://schemas.ogf.org/occi/infrastructure#storage"; title=""'), ('X-OCCI-Attribute', 'occi.compute.memory="2.0"'), ('X-OCCI-Attribute', 'occi.compute.speed="2.667"')]

    """
    MEDIA_TYPE = 'text/occi'

    def render(self, objects):
        self.headers.append(('Content-Type', '%s; charset=utf-8' % self.media_type))
        if isinstance(objects, list) or isinstance(objects, tuple):
            self._render_obj_list(objects)
        else:
            self._render_single_obj(objects)

    @classmethod
    def category_headers(self, obj):
        # Category headers
        category_headers = HttpCategoryHeaders()
        for category in obj.categories:
            params = []
            params.append(('scheme',  category.scheme))

            cat_class = category.__class__.__name__.lower()
            # FIXME: this is a bug in the spec, fix it?
            if cat_class == 'category': cat_class = 'action'
            params.append(('class',  cat_class))

            if category.title:
                params.append(('title',  category.title))

            if 'category_discovery' in obj.render_flags:
                if category.related:
                    params.append(('rel',  category.related))
                if category.attributes:
                    attr_defs=[]
                    for attr in category.unique_attributes.itervalues():
                        attr_props=[]
                        if not attr.mutable and not attr.required:
                            attr_props.append('immutable')
                        elif attr.required:
                            attr_props.append('required')
                        attr_def = attr.name
                        if attr_props:
                            attr_def += '{%s}' % ' '.join(attr_props)
                        attr_defs.append(attr_def)
                    params.append(('attributes', ' '.join(attr_defs)))
                if hasattr(category, 'actions') and category.actions:
                    params.append(('actions', ' '.join([str(cat) for cat in category.actions])))
                if hasattr(category, 'location') and category.location:
                    params.append(('location',
                        obj.translator.url_build(category.location, path_only=True)))

            category_headers.add(category.term, params)
        return category_headers

    def _render_single_obj(self, obj):
        """Render a single `DataObject`.
        """
        # Category headers
        category_headers = self.category_headers(obj)
        [self.headers.append(('Category', h)) for h in category_headers.headers()]

        # Link headers
        link_headers = HttpLinkHeaders()
        for link in obj.links + obj.actions:
            params = []
            params.append(('rel',  ' '.join([str(cat) for cat in link.target_categories])))
            params.append(('title',  link.target_title or ''))
            if link.link_location:
                params.append(('self',  link.link_location))
                if link.link_categories and link.link_attributes:
                    params.append(('category', ' '.join([str(cat) for cat in link.link_categories])))
                    for attr, value in link.link_attributes:
                        params.append((attr,  value))

            link_headers.add(link.target_location, params)
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

class TextPlainRenderer(HeaderRenderer):
    """Renderer for the text/plain content type.

    >>> from occi.ext.infrastructure import ComputeKind, StorageKind
    >>> cats = [ComputeKind]
    >>> links = [LinkRepr(target_location='http://example.com/storage/345', target_categories=[StorageKind])]
    >>> attrs = [('occi.compute.memory', '2.0'), ('occi.compute.speed', '2.667')]
    >>> obj = DataObject(location='http://example.com/compute/123', categories=cats, links=links, attributes=attrs)
    >>> r = TextPlainRenderer()
    >>> r.render([obj])
    >>> r.headers
    [('Content-Type', 'text/plain; charset=utf-8')]
    >>> r.body
    'X-OCCI-Location: http://example.com/compute/123\\r\\n'
    >>> r = TextPlainRenderer()
    >>> r.render(obj)
    >>> r.headers
    [('Content-Type', 'text/plain; charset=utf-8')]
    >>> r.body
    'Category: compute; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"; title="Compute Resource"\\r\\nLink: <http://example.com/storage/345>; rel="http://schemas.ogf.org/occi/infrastructure#storage"; title=""\\r\\nX-OCCI-Attribute: occi.compute.memory="2.0"\\r\\nX-OCCI-Attribute: occi.compute.speed="2.667"\\r\\n'

    """
    MEDIA_TYPE = 'text/plain'

    def render(self, objects):
        super(TextPlainRenderer, self).render(objects)
        for name, value in self.headers[1:]:
            self.body += '%s: %s\r\n' % (name, value)
        self.headers = []
        self.headers.append(('Content-Type', '%s; charset=utf-8' % self.media_type))

class TextURIListRenderer(Renderer):
    """Renderer for the text/uri-list content type.

    This renderer always returns URIs, even if just one object is rendered.

    >>> from occi.ext.infrastructure import ComputeKind, StorageKind
    >>> objs = []
    >>> objs.append(DataObject(location='/compute/123', categories=[ComputeKind]))
    >>> objs.append(DataObject(location='/compute/234', categories=[ComputeKind]))
    >>> objs.append(DataObject(location='/storage/345', categories=[StorageKind]))
    >>> r = TextURIListRenderer()
    >>> r.render(objs)
    >>> r.headers
    [('Content-Type', 'text/uri-list; charset=utf-8')]
    >>> r.body
    '/compute/123\\r\\n/compute/234\\r\\n/storage/345\\r\\n'
    >>> r = TextURIListRenderer()
    >>> r.render(objs[1])
    >>> r.headers
    [('Content-Type', 'text/uri-list; charset=utf-8')]
    >>> r.body
    '/compute/234\\r\\n'
    """
    MEDIA_TYPE = 'text/uri-list'

    def render(self, objects):
        self.headers.append(('Content-Type', '%s; charset=utf-8' % self.media_type))
        if not isinstance(objects, list) and not isinstance(objects, tuple):
            objects = [objects]
        for obj in objects:
            if obj.location:
                self.body += '%s\r\n' % obj.location

class TextRenderer(Renderer):
    """The default renderer. Uses text/plain for single object rendering and
    text/uri-list for multiple objects rendering.

    >>> from occi.ext.infrastructure import ComputeKind, StorageKind
    >>> objs = []
    >>> attrs = [('occi.compute.memory', '2.0'), ('occi.compute.speed', '2.667')]
    >>> objs.append(DataObject(location='/compute/123', categories=[ComputeKind]))
    >>> objs.append(DataObject(location='/compute/234', categories=[ComputeKind], attributes=attrs))
    >>> objs.append(DataObject(location='/storage/345', categories=[StorageKind]))
    >>> r = TextRenderer()
    >>> r.render(objs)
    >>> r.headers
    [('Content-Type', 'text/uri-list; charset=utf-8')]
    >>> r.body
    '/compute/123\\r\\n/compute/234\\r\\n/storage/345\\r\\n'
    >>> r = TextRenderer()
    >>> r.render(objs[1])
    >>> r.headers
    [('Content-Type', 'text/plain; charset=utf-8')]
    >>> r.body
    'Category: compute; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"; title="Compute Resource"\\r\\nX-OCCI-Attribute: occi.compute.memory="2.0"\\r\\nX-OCCI-Attribute: occi.compute.speed="2.667"\\r\\n'
    """
    def render(self, objects):
        if isinstance(objects, list) or isinstance(objects, tuple):
            r = TextURIListRenderer()
        else:
            r = TextPlainRenderer()
        r.render(objects)
        self.headers = r.headers
        self.body = r.body

# Register required renderers
register_renderer(TextPlainRenderer, default=True)
register_renderer(HeaderRenderer)
register_renderer(TextPlainRenderer)
register_renderer(TextURIListRenderer)
register_renderer(TextRenderer, pattern='text/*')
register_renderer(TextPlainRenderer, pattern='*/*')


if __name__ == "__main__":
    import doctest
    doctest.testmod()
