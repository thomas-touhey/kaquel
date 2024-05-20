.. _format-lucene:

Lucene Query Language
=====================

.. py:currentmodule:: kaquel.lucene

The `Apache Lucene query language`_, as documented in `Lucene query syntax`_
in ElasticSearch's documentation, is available as a possible query syntax
for Kibana.

Kaquel only supports converting to the query DSN from a Lucene query, in the
form of its :py:func:`parse_lucene` function.

.. _Apache Lucene query language:
    https://lucene.apache.org/core/2_9_4/queryparsersyntax.html
.. _Lucene query syntax:
    https://www.elastic.co/guide/en/kibana/current/lucene-query.html
