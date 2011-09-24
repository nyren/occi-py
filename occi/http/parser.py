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

from occi.core import Category, Kind, Mixin, Attribute
from occi.http.header import (HttpHeaderError, HttpHeadersBase,
        HttpWebHeadersBase, HttpCategoryHeaders, HttpLinkHeaders,
        HttpAttributeHeaders, HttpAcceptHeaders)
from occi.http.dataobject import DataObject, LinkRepr, URLTranslator

_parsers = {}

class ParserError(Exception):
    pass

def register_parser(content_type, parser):
    _parsers[content_type] = parser

def unregister_parser(content_type):
    del _parsers[content_type]

def get_parser(content_type=None, translator=None):
    """Return a parser for the given Content-Type.

    >>> p = get_parser('text/occi')
    >>> isinstance(p, HeaderParser)
    True
    >>> p = get_parser('text/plain; charset=utf-8')
    >>> isinstance(p, TextPlainParser)
    True
    >>> p = get_parser()
    >>> isinstance(p, HeaderParser)
    True
    >>> p = get_parser('application/not-supported')
    Traceback (most recent call last):
        File "parser.py", line 41, in parser
    ParserError: "application/not-supported": Content-Type not supported
    """
    p = None
    if not content_type:
        p = _parsers.get(None)
    else:
        h = HttpWebHeadersBase()
        h.parse(content_type or '')
        for c_type, c_params in h.all():
            try:
                p = _parsers[c_type]
            except KeyError:
                pass
            else:
                break

    if not p:
        raise ParserError('"%s": Content-Type not supported' % content_type)
    return p(translator=translator)

class Parser(object):
    """Parser base class.

    A Parser must implement the parse() method which parses the provided HTTP
    Headers and/or HTTP body into a set of data objects and/or location URLs.

    The result of the parse() method is stored in the following attributes:
    :var objects: A list of `DataObject` instances
    :var accept_types: A list of content types (populated by Parser.parse())

    """
    def __init__(self, translator=None):
        self.objects = []
        self.accept_types = []
        self.translator = translator or URLTranslator('')

    def parse(self, headers=None, body=None):
        """The parse method doing the actual work. This method must be called
        from the child-class parse method.

        :keyword headers: HTTP Headers represented as a list of tuples
            containing the header name and value of each header line.
        :keyword body: HTTP Body as a string.
        """
        # Extract and parse Accept header
        for name, value in headers or ():
            if name.lower() == 'accept':
                self._parse_accept_header(value)

    def _parse_accept_header(self, header_value):
        """Parse Accept header and store the accepted content types in
        :var accept_types:
        """
        h = HttpAcceptHeaders()
        h.parse(header_value)
        for c_type, c_params in h.all_sorted():
            self.accept_types.append(c_type)

class HeaderParser(Parser):
    """Parser for the text/occi content type.

    Data is transmitted in the HTTP Header. Only a single data object can be
    represented using the text/occi content type.

    >>> headers = []
    >>> headers.append(('Category', 'network; scheme="http://schemes.ogf.org/occi/infrastructure#"; class="kind", ipnetwork; scheme="http://schemes.ogf.org/occi/infrastructure#";'))
    >>> headers.append(('Category', 'user; scheme="http://schemes.ogf.org/occi/credentials#"; class="mixin"'))
    >>> headers.append(('X-OCCI-Attribute', 'title="Test Network, testing", occi.network.label=intranet'))
    >>> headers.append(('X-OCCI-Attribute', 'occi.network.address="192.168.1.123", occi.netwark.gateway="192.168.1.1"'))
    >>> p = HeaderParser()
    >>> p.parse(headers=headers)
    >>> p.objects[0].categories
    [Kind('network', 'http://schemes.ogf.org/occi/infrastructure#'), Category('ipnetwork', 'http://schemes.ogf.org/occi/infrastructure#'), Mixin('user', 'http://schemes.ogf.org/occi/credentials#')]
    >>> p.objects[0].links
    []
    >>> p.objects[0].attributes
    [('title', 'Test Network, testing'), ('occi.network.label', 'intranet'), ('occi.network.address', '192.168.1.123'), ('occi.netwark.gateway', '192.168.1.1')]

    >>> p.objects[0].location

    """
    def parse(self, headers=None, body=None):
        categories = []
        links = []
        attributes = []
        locations = []

        # Walk list of HTTP header name-value pairs
        for name, value in headers or ():
            name = name.lower()

            if name == 'accept':
                self._parse_accept_header(value)
            elif name == 'category':
                categories.extend(self._parse_category_header(value))
            elif name == 'link':
                # FIXME - not allowing Link create/update using POST/PUT yet
                pass
            elif name == 'x-occi-attribute':
                attribute_headers = HttpAttributeHeaders()
                attribute_headers.parse(value)
                attributes.extend(attribute_headers.all())
            elif name == 'x-occi-location':
                location_headers = HttpHeadersBase()
                location_headers.parse(value)
                locations.extend(location_headers.all())

        # Only possible to represent one "full" data object with HTTP Headers.
        # Multiple data objects can only be represented with a location.
        locations = locations or [None]
        self.objects.append(DataObject(
            categories=categories,
            links=links,
            attributes=attributes,
            location=locations[0]))
        for loc in locations[1:]:
            self.objects.append(DataObject(location=loc))

    def _parse_category_header(self, header_value):
        categories = []
        category_headers = HttpCategoryHeaders()
        category_headers.parse(header_value)
        for term, attributes in category_headers.all():
            param = {}
            for k, v in attributes:
                param[k] = v

            # Category scheme
            try:
                scheme = param['scheme']
            except KeyError:
                raise HttpHeaderError('Category scheme not specified')

            # Category, Kind or Mixin?
            t = param.get('class')
            cls = Category
            if t and t.lower() == 'kind':
                cls = Kind
            elif t and t.lower() == 'mixin':
                cls = Mixin
            elif not t and param.get('location'):
                cls = Mixin

            # Related Kind/Mixin
            try:
                t = param['rel']
                r_scheme, r_term = t.split('#', 1)
                r_scheme += '#'
                related = cls(r_term, r_scheme)
            except KeyError, ValueError:
                related = None

            # Supported attributes (mutable)
            try:
                attributes = []
                SPEC_PLAIN = re.compile(r'^([a-z0-9._-]+)$')
                SPEC_PROPS = re.compile(r'^([a-z0-9._-]+){(.*)}$')
                for attr_spec in param['attributes'].split():
                    attr_kwargs = {}
                    m = SPEC_PLAIN.match(attr_spec)
                    if not m:
                        m = SPEC_PROPS.match(attr_spec)
                        if not m:
                            raise HttpHeaderError('%s: Invalid attribute specification in Category header' % attr_spec)
                        else:
                            for prop in m.groups()[1].split():
                                if prop == 'required':
                                    attr_kwargs['required'] = True
                                if prop == 'immutable':
                                    attr_kwargs['mutable'] = False
                    attributes.append(Attribute(m.groups()[0], **attr_kwargs))
            except KeyError, IndexError:
                attributes = None

            # Supported actions
            try:
                t =  param['actions'].split()
            except KeyError:
                actions = None
            else:
                actions = []
                for action in param['actions'].split():
                    try:
                        a_term, a_scheme = action.split('#', 1)
                    except ValueError:
                        pass
                    else:
                        actions.append(Category(a_term, a_scheme))

            # Keyword args for Category
            kwargs = {
                    'title': param.get('title'),
                    'attributes': attributes
            }

            # Additional keyword args for Kind/Mixin
            if cls == Kind or cls == Mixin:
                kwargs['related'] = related
                kwargs['actions'] = actions
                location = param.get('location')
                if location:
                    kwargs['location'] = self.translator.url_strip(location)

            # Append instance to categories list
            try:
                categories.append(cls(term, scheme, **kwargs))
            except Category.Invalid as e:
                raise HttpHeaderError('%s: Invalid Category header: %s' % (scheme+term, e))

        return categories

class TextPlainParser(Parser):
    """Parser for the text/plain content type.

    Data is transmitted in the HTTP Body.

    >>> headers = [('Accept', 'text/*, */*;q=0.1')]
    >>> body  = 'Category: network; scheme="http://schemes.ogf.org/occi/infrastructure#";\\r\\n'
    >>> body += '    class=kind;\\r\\n'
    >>> body += '    title="Network Resource";\\r\\n'
    >>> body += '    rel="http://schemes.ogf.org/occi/core#resource";\\r\\n'
    >>> body += '    attributes="occi.network.vlan occi.network.label occi.network.state{immutable}";\\r\\n'
    >>> body += '    actions="http://schemas.ogf.org/occi/infrastructure/network/action#up http://schemas.ogf.org/occi/infrastructure/network/action#down"\\n'
    >>> body += 'Category: ipnetwork; scheme="http://schemes.ogf.org/occi/infrastructure#"; class="mixin"\\r\\n'
    >>> body += 'X-OCCI-Attribute: title="Test Network, testing"\\n'
    >>> body += 'X-OCCI-Attribute: occi.network.label=intranet\\r\\n'
    >>> body += 'X-OCCI-Attribute: occi.network.address="192.168.1.123", occi.netwark.gateway="192.168.1.1"\\r\\n'
    >>> p = TextPlainParser()
    >>> p.parse(headers=headers, body=body)
    >>> p.accept_types
    ['*/*', 'text/*']
    >>> p.objects[0].categories
    [Kind('network', 'http://schemes.ogf.org/occi/infrastructure#'), Mixin('ipnetwork', 'http://schemes.ogf.org/occi/infrastructure#')]
    >>> network_kind = p.objects[0].categories[0]
    >>> network_kind.term
    'network'
    >>> network_kind.attributes['occi.network.state']
    Attribute('occi.network.state', required=True, mutable=False)
    >>> p.objects[0].links
    []
    >>> p.objects[0].attributes
    [('title', 'Test Network, testing'), ('occi.network.label', 'intranet'), ('occi.network.address', '192.168.1.123'), ('occi.netwark.gateway', '192.168.1.1')]
    >>> body  = 'X-OCCI-Location: http://example.com/network/123\\n'
    >>> body += 'X-OCCI-Location: http://example.com/network/234\\n'
    >>> body += 'X-OCCI-Location: http://example.com/network/345\\n'
    >>> p = TextPlainParser()
    >>> p.parse(body=body)
    >>> [obj.location for obj in p.objects]
    ['http://example.com/network/123', 'http://example.com/network/234', 'http://example.com/network/345']
    """
    def __init__(self, translator=None):
        self._header_parser = HeaderParser(translator=translator)

    def get_objects(self):
        return self._header_parser.objects
    objects = property(get_objects)

    def get_accept_types(self):
        return self._header_parser.accept_types
    accept_types = property(get_accept_types)

    def parse(self, headers=None, body=None):
        super(TextPlainParser, self).parse(headers, body)
        body = body or ''
        headers = []
        for h in re.sub(r'\n\s', ' ', body.replace('\r', '')).split('\n'):
            if not h.strip():
                continue
            try:
                name, value = h.split(':', 1)
            except ValueError:
                raise HttpHeaderError(h)
            if not value:
                raise HttpHeaderError(h)

            headers.append((name, value))

        self._header_parser.parse(headers=headers)

class TextURIListParser(Parser):
    """Parser for the text/uri-list content type.

    Data is transmitted in the HTTP Body.

    >>> body  = 'http://example.com/network/123\\n'
    >>> body += 'http://example.com/network/234\\r\\n'
    >>> body += 'http://example.com/network/345 \\n'
    >>> body += '\\r\\n'
    >>> p = TextURIListParser()
    >>> p.parse(body=body)
    >>> [obj.location for obj in p.objects]
    ['http://example.com/network/123', 'http://example.com/network/234', 'http://example.com/network/345']
    """
    def parse(self, headers=None, body=None):
        super(TextURIListParser, self).parse(headers, body)
        body = body or ''
        for loc in body.replace('\r', '').split('\n'):
            loc = loc.strip()
            if loc:
                self.objects.append(DataObject(location=loc))

# Register required parsers
register_parser(None, HeaderParser)
register_parser('text/occi', HeaderParser)
register_parser('text/plain', TextPlainParser)
register_parser('text/uri-list', TextURIListParser)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
