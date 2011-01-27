def escape_quotes(s, quotechar='"', escapechar='\\'):
    """Escape quote character and also escape the escape character itself.
    """
    buf = ''
    for c in s:
        if c == quotechar or c == escapechar:
            buf += escapechar
        buf += c
    return buf

def split_quoted(s, delimiter=',', quotechar='"', escapechar='\\', remove_quotes=False):
    """Split string on delimiter if and only if delimiter is not within a quote
    nor escaped by the escape character. An escaped quote character will not
    affect the quote state during parsing.

    >>> split_quoted(r'name="foo,bar",size=40, key="value",')
    ['name="foo,bar"', 'size=40', ' key="value"']
    >>> split_quoted(r'name="foo,bar",size=40, key="value",', remove_quotes=True)
    ['name=foo,bar', 'size=40', ' key=value']
    >>> split_quoted(r'name="foo,bar\\",size=40, key=", value=bar\\,foo, items=3', remove_quotes=True)
    ['name=foo,bar",size=40, key=', ' value=bar,foo', ' items=3']
    """
    l = []
    quote = False
    escape = False
    buf = None
    for c in s:
        #print "e=%s q=%s\t%s" % (escape, quote, buf)
        if c == escapechar:
            escape = not escape
            if escape and remove_quotes:
                if buf is None:
                    buf = ''
                continue
        elif c == quotechar and not escape:
            quote = not quote
            if remove_quotes:
                if buf is None:
                    buf = ''
                continue
        elif c == delimiter and not escape and not quote:
            l.append(buf)
            buf = None
            continue
        elif escape:
            escape = False

        if buf is None:
            buf = ''
        buf += c
    if buf is not None:
        l.append(buf)
    return l


if __name__ == "__main__":
    import doctest
    doctest.testmod()
