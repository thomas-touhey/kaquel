Rendering queries
=================

.. py:currentmodule:: kaquel.query

Kaquel provides various utilities to render queries from :py:class:`Query`
objects into different languages. In this section, we will use these utilities
in example programs.

Rendering queries from query DSN as KQL
---------------------------------------

.. py:currentmodule:: kaquel.kql

In order to parse a KQL query, you must use the :py:func:`render_as_kql`
function.

For example, say you need to make a program that converts a KQL query provided
in the standard input into an ElasticSearch query. You can do the following:

.. literalinclude:: render_as_kql.py
    :language: python

For example, when executing the program with the following input:

.. code-block:: text

    {"bool": {"filter": [{"match": {"a": "b"}}, {"match_phrase": {"c": "d"}}]}}

The output will be the following:

.. code-block:: text

    a: b and c: "d"

Rendering KQL queries
---------------------

.. py:currentmodule:: kaquel.kql.renderer

If you represent your queries using a KQL abstract trees using elements
from :py:mod:`kaquel.kql.lang`, you can use :py:func:`render_kql`.
For example:

.. literalinclude:: render_kql.py
    :language: python

The output will be the following:

.. code-block:: text

    hostname: example.org and ip: "198.51.100.104"
