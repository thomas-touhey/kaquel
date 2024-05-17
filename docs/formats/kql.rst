.. _format-kql:

Kibana Query Language
=====================

.. py:currentmodule:: kaquel.kql

The `Kibana Query Language`_ (KQL), known in the Kibana source as "Kuery", is
a full text query language that resolves into ElasticSearch queries.
It follows the `Kuery grammar`_.

Kaquel only supports parsing with KQL, in the form of its :py:func:`parse_kql`
function.

.. _Kibana Query Language:
    https://www.elastic.co/guide/en/kibana/current/kuery-query.html
.. _Kuery grammar:
    https://github.com/elastic/kibana/blob
    /d6af74431c22ff837e018b71f47619f4d4c2480d/packages/kbn-es-query
    /src/kuery/grammar/grammar.peggy
