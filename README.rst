``kaquel`` -- Tools for handling ElasticSearch queries in various languages
===========================================================================

Kaquel, pronounced */kækyɛl/*, is a toolset for parsing and rendering
query languages for ElasticSearch.

As described in `Parsing queries`_, you can parse Kibana Query Language (KQL),
Apache Lucene and ElasticSearch queries, and render them using the
`ElasticSearch Query DSL`_. For example, with KQL:

.. code-block:: python

    from kaquel.kql import parse_kql

    query = parse_kql('identity: { first_name: "John" }')
    print(query.render())

The project is present at the following locations:

* `Official website and documentation at kaquel.touhey.pro <Kaquel website_>`_;
* `Kaquel repository on Gitlab <Kaquel on Gitlab_>`_;
* `kaquel project on PyPI <Kaquel on PyPI_>`_.

.. _Kaquel website: https://kaquel.touhey.pro/
.. _Kaquel on Gitlab: https://gitlab.com/kaquel/kaquel
.. _Kaquel on PyPI: https://pypi.org/project/kaquel/
.. _Parsing queries: https://kaquel.touhey.pro/guides/parse.html
.. _ElasticSearch Query DSL:
    https://www.elastic.co/guide/en/elasticsearch/reference/current/
    query-dsl.html
