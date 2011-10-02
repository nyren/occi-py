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

import json

from occi import OrderedDict
from occi.http.parser import Parser, register_parser
from occi.http.renderer import Renderer, RendererError, register_renderer, HeaderRenderer
from occi.http.dataobject import DataObject, LinkRepr


class JSONParser(Parser):
    """Parser for the application/occi+json content type."""
    def parse(self, headers=None, body=None):
        raise NotImplemented('yet')

class JSONRenderer(Renderer):
    """Renderer for the application/occi+json content type.

    >>> from occi.ext.infrastructure import ComputeKind, StorageKind
    >>> cats = [ComputeKind]
    >>> links = [LinkRepr(target_location='http://example.com/storage/345', target_categories=[StorageKind])]
    >>> attrs = [('occi.compute.cores', 3), ('occi.compute.speed', 2.667)]
    >>> obj = DataObject(location='http://example.com/compute/123', categories=cats, links=links, attributes=attrs)
    >>> obj.render_flags['resource_instance'] = True
    >>> JSONRenderer.INDENT = None
    >>> r = JSONRenderer()
    >>> r.render(obj)
    >>> r.headers
    [('Content-Type', 'application/occi+json; charset=utf-8'), ('Category', 'compute; scheme="http://schemas.ogf.org/occi/infrastructure#"; class="kind"; title="Compute Resource"')]
    >>> response = json.loads(r.body)
    >>> response['kind']['term']
    u'compute'
    >>> response['links'][0]['target_uri']
    u'http://example.com/storage/345'
    >>> response['links'][0]['target_type'][0] == str(StorageKind)
    True
    >>> response['attributes']['occi.compute.cores']
    3
    >>> response['attributes']['occi.compute.speed'] == 2.667
    True
    """
    OCCI_SPECIFICATION = ('occi', 'json', '1.1')
    MEDIA_TYPE = 'application/occi+json'
    INDENT = 4

    def render(self, objects):
        self.headers.append(('Content-Type', '%s; charset=utf-8' % self.media_type))
        if isinstance(objects, list) or isinstance(objects, tuple):
            json_data = self._render_obj_list(objects)
        else:
            json_data = self._render_single_obj(objects)
        self.body = json.dumps(json_data, indent=self.INDENT)

    def _render_single_obj(self, obj):
        """Render a single `DataObject`.
        """
        if 'resource_instance' in obj.render_flags:
            category_headers = HeaderRenderer.category_headers(obj)
            [self.headers.append(('Category', h)) for h in category_headers.headers()]
        return self._json_obj(obj)

    def _render_obj_list(self, objects):
        """Render a list of `DataObject` instances.
        """
        json_data = []
        for obj in objects:
            json_data.append(self._json_obj(obj))

        # Workaround JSON array vulnerability in browser JavaScript
        # implementations
        return { 'collection': json_data }

    def _json_obj(self, obj):
        """Render a `DataObject` into a JSON-friendly dictionary structure.
        """
        json_obj = OrderedDict()
        json_obj['kind'] = None
        json_obj['kinds'] = []
        json_obj['mixins'] = []
        json_obj['categories'] = []
        json_obj['actions'] = []
        json_obj['links'] = []
        json_obj['attributes'] = OrderedDict()

        # Categories
        for category in obj.categories:
            d = OrderedDict()
            d['term'] = category.term
            d['scheme'] = category.scheme

            d['title'] = category.title
            if category.related:
                d['related'] = str(category.related)
            if category.attributes:
                attr_defs = OrderedDict()
                for attr in category.unique_attributes.itervalues():
                    attr_props = OrderedDict()
                    attr_props['mutable'] = attr.mutable
                    attr_props['required'] = attr.required
                    attr_props['type'] = attr.type_name
                    attr_defs[attr.name] = attr_props
                d['attributes'] = attr_defs
            if category.defaults:
                d['defaults'] = category.defaults
            if hasattr(category, 'actions') and category.actions:
                d['actions'] = [str(cat) for cat in category.actions]
            if hasattr(category, 'location') and category.location:
                d['location'] = obj.translator.url_build(category.location, path_only=True)

            cat_class = category.__class__.__name__.lower()
            if cat_class == 'kind':
                json_obj['kinds'].append(d)
            elif cat_class == 'mixin':
                json_obj['mixins'].append(d)
            else:
                json_obj['categories'].append(d)

        # Links
        for link in obj.links:
            d = OrderedDict()
            if link.target_title:
                d['title'] = link.target_title
            d['target_uri'] = link.target_location
            d['target_type'] = [str(cat) for cat in link.target_categories]
            if link.link_location:
                d['link_uri'] = link.link_location
            if link.link_categories:
                d['link_type'] = [str(cat) for cat in link.link_categories]
            if link.link_attributes:
                attrs = OrderedDict()
                for name, value in link.link_attributes:
                    attrs[name] = value
                d['attributes'] = attrs
            json_obj['links'].append(d)

        # Actions
        for action in obj.actions:
            d = OrderedDict()
            if action.target_title:
                d['title'] = action.target_title
            d['uri'] = action.target_location
            assert(len(action.target_categories) == 1)
            d['type'] = str(action.target_categories[0])
            json_obj['actions'].append(d)

        # Attributes
        for name, value in obj.attributes:
            json_obj['attributes'][name] = value

        # If this is a resource instance ...
        if 'resource_instance' in obj.render_flags:
            try:
                json_obj['kind'] = json_obj['kinds'][0]
                del json_obj['kinds']
            except KeyError, IndexError:
                raise RendererError('Resource instance MUST be of one and only one Kind')
        else:
            del json_obj['kind']

        # Remove empty entries
        for k in json_obj.keys():
            if not json_obj[k]:
                del json_obj[k]

        return json_obj

def register():
    #register_parser(JSONParser)
    register_renderer(JSONRenderer)
    register_renderer(JSONRenderer, media_type='application/json')

if __name__ == "__main__":
    import doctest
    doctest.testmod()

