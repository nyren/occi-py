#!/usr/bin/env python

import unittest
import tests

if __name__ == '__main__':
    suite = tests.all()
    results = unittest.TextTestRunner().run(suite)
