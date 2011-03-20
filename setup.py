#!/usr/bin/env python
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

from distutils.core import setup
from occi import __version__

setup(
    name='occi',
    version=__version__,
    description='Open Cloud Computing Interface Server/Client Library',
    long_description=open('README').read(),
    url='http://github.com/nyren/occi-py',
    author='Ralf Nyren',
    author_email='ralf@nyren.net',
    maintainer='Ralf Nyren',
    maintainer_email='ralf@nyren.net',
    keywords=['OCCI', 'Cloud', 'Library', 'REST', 'RESTful', 'IaaS', 'PaaS', 'SaaS'],
    license='GNU Lesser General Public License (LGPL) version 3',
    packages=['occi',],
#   test_suite='tests.all',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'],
)
