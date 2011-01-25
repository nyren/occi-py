from occi.core import Category, Kind, Mixin
from occi.server import OCCIServer
from occi.http.header import HttpHeaderError, HttpHeadersBase, HttpCategoryHeaders, HttpLinkHeaders, HttpAttributeHeaders

class Parser(object):
    _content_parsers = {}

    def __init__(self, server, headers=None, body=None):
        self.server = server
        self.headers = headers or ()
        self.body = body or ''

        self.locations = []
        self.objects = []

    def parse(self):
        # FIXME - select parser based on content-type
        raise NotImplementedError('Parser does not implement parse method')

    @classmethod
    def register_contenttype(cls, content_type, parser):
        cls._content_parsers[content_type] = parser

    @classmethod
    def unregister_contenttype(cls, content_type):
        del cls._content_parsers[content_type]

class HeaderParser(Parser):
    """Parser for the text/occi content type.

    Data is transmitted in the HTTP Header.

    >>> server = OCCIServer(None)
    >>> server.register_category(Kind('network', 'http://schemes.ogf.org/occi/infrastructure#'))
    >>> server.register_category(Mixin('ipnetwork', 'http://schemes.ogf.org/occi/infrastructure#'))
    >>> server.register_category(Mixin('user', 'http://schemes.ogf.org/occi/credentials#'))
    >>> headers = []
    >>> headers.append(('Category', 'network; scheme="http://schemes.ogf.org/occi/infrastructure#"; class="kind", ipnetwork; scheme="http://schemes.ogf.org/occi/infrastructure#";'))
    >>> headers.append(('Category', 'user; scheme="http://schemes.ogf.org/occi/credentials#'))
    >>> headers.append(('X-OCCI-Attribute', 'title="Test Network, testing", occi.network.label=intranet'))
    >>> headers.append(('X-OCCI-Attribute', 'occi.network.address="192.168.1.123", occi.netwark.gateway="192.168.1.1"'))
    >>> p = HeaderParser(server, headers=headers)
    >>> p.parse()
    >>> p.objects[0]['category']
    [Kind('network', 'http://schemes.ogf.org/occi/infrastructure#'), Mixin('ipnetwork', 'http://schemes.ogf.org/occi/infrastructure#'), Mixin('user', 'http://schemes.ogf.org/occi/credentials#')]
    >>> p.objects[0]['link']
    []
    >>> p.objects[0]['attribute']
    [('title', 'Test Network, testing'), ('occi.network.label', 'intranet'), ('occi.network.address', '192.168.1.123'), ('occi.netwark.gateway', '192.168.1.1')]
    >>> p.locations
    []

    """
    def parse(self):
        categories = []
        links = []
        attributes = []
        locations = []

        # Walk list of HTTP header name-value pairs
        for name, value in self.headers:
            name = name.lower()

            if name == 'category':
                category_headers = HttpCategoryHeaders()
                category_headers.parse(value)
                for term, param in category_headers.all():
                    try:
                        scheme = param['scheme']
                    except KeyError:
                        raise HttpHeaderError('Category scheme not specified')
                    try:
                        categories.append(self.server.lookup_category(scheme + term))
                    except Category.DoesNotExist:
                        raise HttpHeaderError('%s: Category not found' % (scheme+term))
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

        # Only possible to represent one data object with HTTP Headers
        self.objects = [{
            'category': categories,
            'link': links,
            'attribute': attributes,
            }]
        self.locations = locations

class TextParser(Parser):
    """Parser for the text/plain content type.

    Data is transmitted in the HTTP Body.
    """
    def parse(self):
        headers = []
        for h in re.sub(r'\n\s', ' ', body).split('\n'):
            if not h.strip():
                continue
            try:
                name, value = h.split(':', 1)
            except ValueError:
                raise HttpHeaderError(h)
            if not value:
                raise HttpHeaderError(h)

            headers.append((name, value))

        return parse_header_request(headers)


Parser.register_contenttype(None, HeaderParser)
Parser.register_contenttype('text/occi', HeaderParser)
Parser.register_contenttype('text/plain', TextParser)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
