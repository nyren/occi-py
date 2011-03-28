=================================================
 occi-py - OCCI Client/Server Library for Python
=================================================

:Version: 0.6

Synopsis
========

`occy-py` is a generic library implementation of the Open Cloud Computing
Interface.

The Open Cloud Computing Interface (OCCI) comprises a set of open
community-lead specifications delivered through the Open Grid Forum. OCCI is a
Protocol and API for all kinds of Management tasks. See http://occi-wg.org/.

The `occi-py` library is a complete implementation of the OCCI specification
and supports version 1.1 of the OCCI RESTful Protocol.

The aim of `occi-py` is to provide a high-level interface for easy integration
of the OCCI Standard Protocol into both new and existing applications.

Features
========

 - Easy to use. Implement the 5 required ServerBackend methods and you are
   ready to go.

 - Pluggable HTTP server front-end. A `Tornado` front-end is included.

 - Focused on robustness and standard compliance.

 - Supports all Content Types defined by the OCCI HTTP Rendering specification
   and all of the OCCI Infrastructure Kind/Mixin definitions.

 - Easy to extend with custom Entity types as outlined in the OCCI Core specification.

Installation
============

You can install `occi-py` either via the Python Package Index (PyPI)
or from source.

To install using `pip`::

    $ pip install occi

To install using `easy_install`::

    $ easy_install occi

If you have downloaded a source tarball you can install it
by doing the following,::

    $ python setup.py build
    # python setup.py install # as root

OCCI Server
===========

To enable OCCI server support in your application you must implement the
`occi.server.ServerBackend` class. See the stub method documentation for
further information.

IaaS Demo
---------

A demo implementation of the OCCI Infrastructure specification is provided by
`occi_iaas_demo.py` script. The demo uses the `Tornado` front-end and thus
requires the `Tornado` framework to be installed.

To start the demo install `occi-py` and run::

    $ occi_iaas_demo.py

You will then have an OCCI server listening to port 8000 on localhost. To use a
different base URL specify the --base_url option, e.g.::

    $ occi_iaas_demo.py --base_url http://www.example.com:8000/api/

OCCI Client
===========

*soon*

Status
======

The `occi-py` library is fairly stable but it is still under development and
subject to internal API changes.

A `Redis` backend is in the works and will provide a better example on how to
use the library in real applications.

Bug tracker
===========

If you have any suggestions, bug reports or annoyances please report them
to our issue tracker at http://github.com/nyren/occi-py/issues/

Contributing
============

Development of `occi-py` happens at Github: http://github.com/nyren/occi-py

You are highly encouraged to participate in the development. If you don't
like Github (for some reason) you're welcome to send regular patches.

License
=======

This software is licensed under the `GNU Lesser General Public License (LGPL)
version 3`. See the `LICENSE` file in the top distribution directory for the
full license text.
