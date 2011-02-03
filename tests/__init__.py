import os
from utils import unittest
import doctest

DOCTEST_MODULES = [
        'occi.core',
        'occi.server',
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
