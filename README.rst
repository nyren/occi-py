=================================================
 occi - OCCI Client/Server Library for Python
=================================================

:Version: 0.4

Synopsis
========

`occy-py` is a generic library implementation of the Open Cloud Computing
Interface.

The Open Cloud Computing Interface (OCCI) comprises a set of open
community-lead specifications delivered through the Open Grid Forum. OCCI is a
Protocol and API for all kinds of Management tasks. See http://occi-wg.org/.

The `occi` library is a complete implementation of the OCCI specification
and supports version 1.1 of the OCCI RESTful Protocol.

The goal of `occi` is to provide a high-level interface for easy integration
of the OCCI standard into both new and existing applications.

Features
========

 - Easy to use. Implement the 5 required ServerBackend methods and you are
   ready to go.

 - Supports all Content Types defined by the OCCI HTTP Rendering specification.

 - All of the OCCI Infrastructure Kind/Mixin definitions provided.

 - Easy to extend with custom Entity types as outlined in the OCCI Core specification.

Installation
============

You can install `occi` either via the Python Package Index (PyPI)
or from source.

To install using `pip`,::

    $ pip install occi

To install using `easy_install`,::

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

A demo implementation of the OCCI Infrastructure specification is provided in
`occi.demo.iaas_demo`. The demo uses the `Tornado` frontend and thus requires the
`Tornado` framework to be installed.

To start ensure the `occi` library is in your Python path and run,::

    $ python occi/demo/iaas_demo.py

You will then have an OCCI server listening to port 8000 on localhost. To use a different
base URL specify the --base_url option, e.g.:

    $ python occi/demo/iaas_demo.py --base_url http://www.example.com:80/api/

OCCI Client
===========

*soon*


