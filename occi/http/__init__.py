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

import occi
from occi.http.parser import get_parser, register_parser, unregister_parser
from occi.http.renderer import get_renderer, register_renderer, unregister_renderer
from occi.http.dataobject import URLTranslator

# OCCI Http Rendering version
__http_version__ = '1.1'

# HTTP version string for use in Server/Client headers
version_string = 'occi-py/%s OCCI/%s' % (occi.__version__, __http_version__)

class HttpServer(object):
    def __init__(self, occi_server,
            listen_address=None, listen_port=None,
            base_url=None):
        self.server = occi_server
        self.address = listen_address
        self.port = listen_port or 8000
        self.translator = URLTranslator(base_url or '')
        self.base_url = self.translator.base_url
        self.base_path = self.translator.base_path

    def run(self):
        raise NotImplementedError

class HttpClient(object):
    def __init__(self, occi_client,
            base_url=None):
        self.client = occi_client
        self.base_url = base_url

