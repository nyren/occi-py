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

import os
from utils import unittest
import doctest

DOCTEST_MODULES = [
        'occi.core',
        'occi.backend',
        'occi.backend.dummy',
        'occi.http.dataobject',
        'occi.http.handler',
        'occi.http.header',
        'occi.http.json',
        'occi.http.parser',
        'occi.http.renderer',
        'occi.http.utils',
]

TEST_MODULES = [
        'tests.test_http_handler',
]

def all():
    suite = unittest.TestSuite()
    for m in DOCTEST_MODULES:
        suite.addTests(doctest.DocTestSuite(m))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES))
    return suite
