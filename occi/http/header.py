import re

from occi.http.utils import escape_quotes, split_quoted

class HttpHeaderError(Exception):
    pass

class HttpHeadersBase(object):
    """Base class for representing a set of HTTP headers with the same name.
    I.e. support for comma-separated multiple headers.

    >>> h = HttpHeadersBase()
    >>> h.add('text/plain')
    >>> h.add('application/xml')
    >>> h.add('text/html')
    >>> str(h)
    'text/plain, application/xml, text/html'
    >>> h.parse(str(h))
    ['text/plain', 'application/xml', 'text/html']
    >>> h.all()
    ['text/plain', 'application/xml', 'text/html']

    """
    def __init__(self):
        self._headers = []

    def add(self, header):
        self._headers.append(header)

    def parse(self, header_value):
        self._headers = [self._from_string(value.strip()) for value in split_quoted(header_value)]
        return self._headers

    def all(self):
        return self._headers

    def headers(self):
        return [self._to_string(header) for header in self._headers]

    def _from_string(self, s):
        return s

    def _to_string(self, header):
        return header

    def __str__(self):
        return ', '.join(self.headers())

class HttpAttributeHeaders(HttpHeadersBase):
    """HTTP Attribute header containing a single key-value pair per header.

    >>> h = HttpAttributeHeaders()
    >>> h.parse('foo=bar, quote="foo,bar"')
    [('foo', 'bar'), ('quote', 'foo,bar')]
    >>> h.add('escape', 'k",inject=something')
    >>> s = str(h)
    >>> s
    'foo="bar", quote="foo,bar", escape="k\\\\",inject=something"'
    >>> x = h.parse(s)
    >>> str(h) == s
    True
    >>> h.headers() == HttpHeadersBase().parse(s)
    True

    """

    def add(self, attribute, value):
        super(HttpAttributeHeaders, self).add((attribute, value))

    def _from_string(self, s):
        try:
            k, v = split_quoted(s, delimiter='=', remove_quotes=True)
        except ValueError:
            raise HttpHeaderError
        return (k, v)

    def _to_string(self, header):
        k, v = header
        return '%s="%s"' % (k, escape_quotes(str(v)))

class HttpWebHeadersBase(HttpHeadersBase):
    """Base class for headers like Web Link/Category which have multiple
    key-value attributes separated by semicolon.
    """
    HEADER_VALUE_REGEXP = re.compile(r'^\s*([^;]+)\s*')

    def add(self, item, attributes=()):
        super(HttpWebHeadersBase, self).add((item, attributes))

    def _from_string(self, header_string, value_re=HEADER_VALUE_REGEXP):
        # Match header value and remove from string
        m = value_re.match(header_string)
        if not m:
            raise HttpHeaderError('%s: invalid header' % header_string)
        value = m.groups()[0]
        attr_string = header_string[m.end():]

        # Split and parse string of header attributes
        attributes = []
        for s in split_quoted(attr_string, delimiter=';'):
            if not s:
                continue
            try:
                k, v = split_quoted(s.strip(), delimiter='=', remove_quotes=True)
            except ValueError:
                raise HttpHeaderError("'%s': failed to parse header attribute" % s)
            attributes.append((k, v))

        return (value, attributes)

    def _to_string(self, header):
        item, attributes = header
        return '; '.join(
            ['%s' % item] +
            ['%s="%s"' % (name, escape_quotes(str(value))) for name, value in attributes])

class HttpLinkHeaders(HttpWebHeadersBase):
    """HTTP Web Link header.

    >>> h = HttpLinkHeaders()
    >>> h.add('/api/compute/vm01;start', [('rel', 'http://schemas.ogf.org/occi/action#start'), ('class', 'action'), ('title', 'Start')])
    >>> h.add('/api/storage/san1', [('rel', 'http://schemas.ogf.org/occi/kind#storage'), ('class', 'link'), ('title', 'Quorum Disk'), ('device', 'sda')])
    >>> s = str(h)
    >>> x = h.parse(s)
    >>> str(h) == s
    True
    >>> h.headers() == HttpHeadersBase().parse(s)
    True

    """
    HEADER_VALUE_REGEXP = re.compile(r'^\s*<([^>]+)>\s*')

    def _from_string(self, s):
        return super(HttpLinkHeaders, self)._from_string(s, value_re=self.HEADER_VALUE_REGEXP)

    def _to_string(self, header):
        uri, attributes = header
        return super(HttpLinkHeaders, self)._to_string(("<%s>" % uri, attributes))

class HttpCategoryHeaders(HttpWebHeadersBase):
    """HTTP Web Category header.

    >>> h = HttpCategoryHeaders()
    >>> h.add('compute', attributes=[('scheme', 'http://schemas.ogf.org/occi/kind#'), ('label', 'Compute Resource')])
    >>> h.add('ubuntu-9.10', [('scheme', 'http://schemas.ogf.org/occi/category#template'), ('label', 'Ubuntu Linux 9.10')])
    >>> s = str(h)
    >>> x = h.parse(s)
    >>> str(h) == s
    True
    >>> h.headers() == HttpHeadersBase().parse(s)
    True
    """
    pass

class HttpAcceptHeaders(HttpWebHeadersBase):
    """HTTP Accept header.

    >>> s = 'text/html, application/xml;q=0.9, application/xhtml+xml, image/png, image/x-xbitmap, */*;q=0.1'
    >>> h = HttpAcceptHeaders()
    >>> h.parse(s)
    [('text/html', []), ('application/xml', [('q', '0.9')]), ('application/xhtml+xml', []), ('image/png', []), ('image/x-xbitmap', []), ('*/*', [('q', '0.1')])]

    """
    pass


if __name__ == "__main__":
    import doctest
    doctest.testmod()
