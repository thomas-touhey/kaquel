Rendering queries
=================

.. py:currentmodule:: kaquel.query

Kaquel provides various utilities to render queries from :py:class:`Query`
objects into different languages. In this section, we will use these utilities
in example programs.

Rendering queries as KQL
------------------------

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
