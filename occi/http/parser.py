
class Parser(object):
    _content_parsers = {}

    def __init__(self, headers=None, body=None):
        self.headers = headers
        self.body = body

        self.locations = []
        self.objects = []

    def parse(self):
        # Implement in sub-class
        assert(False)

    @classmethod
    def register_parser(cls, content_type, parser):
        cls._content_parsers[content_type] = parser

    @classmethod
    def unregister_parser(cls, content_type):
        del cls._content_parsers[content_type]

class HeaderParser(Parser):
    """Parser for the text/occi content type.

    Data is transmitted in the HTTP Header.
    """
    def parse(self):
        pass

class TextParser(Parser):
    """Parser for the text/plain content type.

    Data is transmitted in the HTTP Body.
    """
    def parse(self):
        pass


Parser.register_parser(None, HeaderParser)
Parser.register_parser('text/occi', HeaderParser)
Parser.register_parser('text/plain', TextParser)
