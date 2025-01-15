Optimizing KQL queries
======================

By default, when rendering queries as KQL:

* If using :py:func:`kaquel.kql.render_as_kql` to render a KQL query from
  query DSN, optimization is enabled by default. See
  :ref:`devguide-render-kql-from-query` for more detail;
* If using :py:func:`kaquel.kql.renderer.render_kql` to render a KQL query,
  optimization is disabled by default. See :ref:`devguide-render-kql`
  for more detail.

It is possible to toggle this feature by explicitely setting the ``optimize``
keyword parameter, or in the second case, calling
:py:func:`kaquel.kql.optimizer.optimize_kql` directly to get the optimized
version of the query.

An example of optimizing a KQL query directly from its textual form can be
found in the form of the following program:

.. literalinclude:: optimize_kql.py
    :language: python

An example run of the query is the following:

.. code-block:: text

    > first_name: Adam or first_name: John
    first_name: (Adam or John)
    > first_name: (not John and not Adam)
    not first_name: (John or Adam)
