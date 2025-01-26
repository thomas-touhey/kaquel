#!/usr/bin/env python
# *****************************************************************************
# Copyright (C) 2024 Thomas Touhey <thomas@touhey.fr>
#
# This software is governed by the CeCILL-C license under French law and
# abiding by the rules of distribution of free software. You can use, modify
# and/or redistribute the software under the terms of the CeCILL-C license
# as circulated by CEA, CNRS and INRIA at the following
# URL: https://cecill.info
#
# As a counterpart to the access to the source code and rights to copy, modify
# and redistribute granted by the license, users are provided only with a
# limited warranty and the software's author, the holder of the economic
# rights, and the successive licensors have only limited liability.
#
# In this respect, the user's attention is drawn to the risks associated with
# loading, using, modifying and/or developing or reproducing the software by
# the user in light of its specific status of free software, that may mean
# that it is complicated to manipulate, and that also therefore means that it
# is reserved for developers and experienced professionals having in-depth
# computer knowledge. Users are therefore encouraged to load and test the
# software's suitability as regards their requirements in conditions enabling
# the security of their systems and/or data to be ensured and, more generally,
# to use and operate it in the same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.
# *****************************************************************************
"""KQL language handling."""

from __future__ import annotations

from kaquel.es_query.lang import Query

from .from_query import to_kql as _to_kql
from .parser import parse_kql as _parse_kql
from .renderer import render_kql as _render_kql
from .to_query import from_kql as _from_kql


__all__ = ["parse_kql", "render_as_kql"]


def parse_kql(
    kuery: str,
    /,
    *,
    allow_leading_wildcards: bool = True,
    filters_in_must_clause: bool = False,
) -> Query:
    """Parse a KQL expression into an ElasticSearch query.

    :param kuery: KQL expression to parse.
    :param allow_leading_wildcards: Whether to allow leading wildcards.
    :param filters_in_must_clause: Whether filters should be in the
        'filter' or 'must' clause.
    :return: Parsed query.
    :raises DecodeError: A decoding error has occurred.
    :raises LeadingWildcardsForbidden: Leading wildcards were present while
        disabled.
    """
    kql_query = _parse_kql(
        kuery,
        allow_leading_wildcards=allow_leading_wildcards,
    )
    return _from_kql(kql_query, filters_in_must_clause=filters_in_must_clause)


def render_as_kql(
    query: Query,
    /,
    *,
    filters_in_must_clause: bool = False,
    optimize: bool = True,
) -> str:
    """Render an Elasticsearch query as KQL.

    :param query: Query to render as KQL.
    :param filters_in_must_clause: Whether filters should be retrieved from
        the 'must' clause rather than 'filter' clause for boolean queries.
    :param optimize: Whether to optimize the query first.
    :return: Rendered query as KQL.
    :raises RenderError: An error has occurred while rendering the query;
        usually, the query makes use of a feature that cannot be translated
        into KQL.
    """
    kql_query = _to_kql(query, filters_in_must_clause=filters_in_must_clause)
    return _render_kql(kql_query, optimize=optimize)
