Parsing queries
===============

.. py:currentmodule:: kaquel.query

Kaquel provides various utilities to parse queries into :py:class:`Query`
objects that can be rendered. In this section, we will use these utilities
in example programs.

Parsing KQL queries
-------------------

.. py:currentmodule:: kaquel.kql

In order to parse a KQL query, you must use the :py:func:`parse_kql` function.

For example, say you need to make a program that converts a KQL query provided
in the standard input into an ElasticSearch query. You can do the following:

.. literalinclude:: parse_kql.py
    :language: python

For example, when executing the program with the following input:

.. code-block:: text

    NOT http.request.method: GET

The output will be the following:

.. code-block:: json

    {"bool": {"must_not": {"match": {"http.request.method": "GET"}}}}

Parsing Lucene queries
----------------------

.. py:currentmodule:: kaquel.lucene

In order to parse a Lucene query, as for KQL queries, you must use the
:py:func:`parse_lucene` function.

For example, say you need to make a program that converts a Lucene query
provided in the standard input into an ElasticSearch query.
You can do the following:

.. literalinclude:: parse_lucene.py
    :language: python

For example, when executing the program with the following input:

.. code-block:: text

    a:b AND c:d

The output will be the following:

.. code-block:: json

    {"query_string": {"query": "a:b AND c:d"}}

Detecting invalid input
-----------------------

.. py:currentmodule:: kaquel.errors

In case of an invalid input, parsing functions will raise a
:py:class:`DecodeError`, that holds the location of the error within the
source string. You can thus catch it and display the error to the end user.

An example program doing exactly that is the following:

.. literalinclude:: parse_invalid.py
    :language: python

The output of the above program will be the following:

.. code-block:: text

    At line 1, column 11:
    Syntax error starting at:
      : and_give_it_to_the_next_person
