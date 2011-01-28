import re

from occi.core import Category, Kind, Mixin
from occi.server import OCCIServer
from occi.http.header import HttpHeaderError, HttpHeadersBase, HttpCategoryHeaders, HttpLinkHeaders, HttpAttributeHeaders

_parsers = {}

class ParserError(Exception):
    pass

def register_parser(content_type, parser):
    _parsers[content_type] = parser

def unregister_parser(content_type):
    del _parsers[content_type]

def get_parser(content_type=None):
    """Return a parser for the given Content-Type.

    >>> p = parser('text/occi')
    >>> isinstance(p, HeaderParser)
    True
    >>> p = parser('text/plain')
    >>> isinstance(p, TextPlainParser)
    True
    >>> p = parser()
    >>> isinstance(p, HeaderParser)
    True
    >>> p = parser('application/not-supported')
    Traceback (most recent call last):
        File "parser.py", line 41, in parser
    ParserError: ('%s: Content-Type not supported', 'application/not-supported')
    """
    p = None
    if not content_type:
        p = _parsers.get(None)
    else:
        h = HttpHeadersBase()
        h.parse(content_type or '')
        for value in h.headers():
            value = value.split(';', 1)[0].strip()
            try:
                p = _parsers[value]
            except KeyError:
                pass
            else:
                break

    if not p:
        raise ParserError('%s: Content-Type not supported', content_type)
    return p()

class Parser(object):
    """Parser base class.

    A Parser must implement the parse() method which parses the provided HTTP
    Headers and/or HTTP body into a set of data objects and/or location URLs.

    The result of the parse() method is stored in the following attributes:
    :var objects: A list of `DataObject` instances
    :var locations: A list of URL strings

    """
    def __init__(self):
        self.objects = []
        self.locations = []

    def parse(self, headers=None, body=None):
        """The parse method doing the actual work.

        :keyword headers: HTTP Headers represented as a list of tuples
            containing the header name and value of each header line.
        :keyword body: HTTP Body as a string.
        """
        raise NotImplementedError('%s: does not implement the parse() method',
                self.__class__.__name__)

class DataObject(object):
    """A data object transferred using the OCCI protocol.

    A data object cat represent a resource instance, an action invocation,
    filter parameters, etc. It is up to the handler of the particular request/response
    to interpret the contents of a `DataObject`.
    """
    def __init__(self, categories=None, attributes=None, links=None):
        self.categories = categories or []
        self.links = links or []
        self.attributes = attributes or []


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
    >>> p.locations
    []

    """
    def parse(self, headers=None, body=None):
        headers = headers or ()
        categories = []
        links = []
        attributes = []
        locations = []

        # Walk list of HTTP header name-value pairs
        for name, value in headers:
            name = name.lower()

            if name == 'category':
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
                self.locations.extend(location_headers.all())

        # Only possible to represent one data object with HTTP Headers
        self.objects.append(DataObject(
            categories=categories,
            links=links,
            attributes=attributes))

    def _parse_category_header(self, header_value):
        categories = []
        category_headers = HttpCategoryHeaders()
        category_headers.parse(header_value)
        for term, param in category_headers.all():
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
                attributes = param['attributes'].split()
            except KeyError:
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
            if isinstance(cls, Kind) or isinstance(cls, Mixin):
                kwargs['related'] = related
                kwargs['actions'] = actions
                kwargs['location'] = param.get('location')

            # Append instance to categories list
            try:
                categories.append(cls(term, scheme, **kwargs))
            except Category.Invalid:
                raise HttpHeaderError('%s: Invalid Category header' % (scheme+term))

        return categories

class TextPlainParser(Parser):
    """Parser for the text/plain content type.

    Data is transmitted in the HTTP Body.

    >>> body  = 'Category: network; scheme="http://schemes.ogf.org/occi/infrastructure#";\\r\\n'
    >>> body += '    class=kind;\\r\\n'
    >>> body += '    title="Network Resource";\\r\\n'
    >>> body += '    rel="http://schemes.ogf.org/occi/core#resource";\\r\\n'
    >>> body += '    attributes="occi.network.vlan occi.network.label";\\r\\n'
    >>> body += '    actions="http://schemas.ogf.org/occi/infrastructure/network/action#up http://schemas.ogf.org/occi/infrastructure/network/action#down"\\n'
    >>> body += 'Category: ipnetwork; scheme="http://schemes.ogf.org/occi/infrastructure#"; class="mixin"\\r\\n'
    >>> body += 'X-OCCI-Attribute: title="Test Network, testing"\\n'
    >>> body += 'X-OCCI-Attribute: occi.network.label=intranet\\r\\n'
    >>> body += 'X-OCCI-Attribute: occi.network.address="192.168.1.123", occi.netwark.gateway="192.168.1.1"\\r\\n'
    >>> p = TextPlainParser()
    >>> p.parse(body=body)
    >>> p.objects[0].categories
    [Kind('network', 'http://schemes.ogf.org/occi/infrastructure#'), Mixin('ipnetwork', 'http://schemes.ogf.org/occi/infrastructure#')]
    >>> p.objects[0].links
    []
    >>> p.objects[0].attributes
    [('title', 'Test Network, testing'), ('occi.network.label', 'intranet'), ('occi.network.address', '192.168.1.123'), ('occi.netwark.gateway', '192.168.1.1')]
    >>> body  = 'X-OCCI-Location: http://example.com/network/123\\n'
    >>> body += 'X-OCCI-Location: http://example.com/network/234\\n'
    >>> body += 'X-OCCI-Location: http://example.com/network/345\\n'
    >>> p = TextPlainParser()
    >>> p.parse(body=body)
    >>> p.locations
    ['http://example.com/network/123', 'http://example.com/network/234', 'http://example.com/network/345']
    """
    def __init__(self):
        self._header_parser = HeaderParser()

    def get_objects(self):
        return self._header_parser.objects
    objects = property(get_objects)

    def get_locations(self):
        return self._header_parser.locations
    locations = property(get_locations)

    def parse(self, headers=None, body=None):
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

# Register required parsers
register_parser(None, HeaderParser)
register_parser('text/occi', HeaderParser)
register_parser('text/plain', TextPlainParser)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
