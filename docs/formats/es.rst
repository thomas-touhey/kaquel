.. _formats-es:

ElasticSearch Query DSL
=======================

.. py:currentmodule:: kaquel.query

Kaquel's query language, represented as :py:class:`Query` subclasses in
:py:mod:`kaquel.query`, is actually a subset to ElasticSearch's
`Query DSL`_ (Domain Specific Language), and implements what is needed
to render parsed trees from other query languages.

.. _Query DSL:
    https://www.elastic.co/guide/en/elasticsearch/reference/current/
    query-dsl.html
