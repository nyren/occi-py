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


from occi.http.parser import Parser
from occi.http.renderer import Renderer

class JSONParser(Parser):
    """Parser for the application/json content type."""
    def parse(self, headers=None, body=None):
        raise NotImplemented('yet')

class JSONRenderer(Renderer):
    """Renderer for the application/json content type."""

    def render(self, objects):
        raise NotImplemented('yet')
