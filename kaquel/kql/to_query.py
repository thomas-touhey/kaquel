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
"""KQL query to abstract conversion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from kaquel.query import (
    BooleanQuery,
    ExistsQuery,
    MatchAllQuery,
    MatchPhraseQuery,
    MatchQuery,
    MultiMatchQuery,
    MultiMatchQueryType,
    NestedQuery,
    NestedScoreMode,
    Query,
    RangeQuery,
)

from .lang import (
    All as KQLAll,
    And as KQLAnd,
    Exist as KQLExist,
    Gt as KQLGt,
    Gte as KQLGte,
    Lt as KQLLt,
    Lte as KQLLte,
    Match as KQLMatch,
    MultiMatch as KQLMultiMatch,
    Nested as KQLNested,
    Not as KQLNot,
    Or as KQLOr,
    Query as KQLQuery,
    ValueAnd as KQLValueAnd,
    ValueCondition as KQLValueCondition,
    ValueMatch as KQLValueMatch,
    ValueNot as KQLValueNot,
    ValueOr as KQLValueOr,
    ValuePhraseMatch as KQLValuePhraseMatch,
)


class _ConversionOptions(BaseModel):
    """Conversion options."""

    model_config = ConfigDict(extra="forbid")
    """Model configuration."""

    filters_in_must_clause: bool
    """Whether filters should be retrieved from the 'must' clause rather than
    'filter' for boolean queries.

    This is set using the ``filters_in_must_clause`` kwarg on
    :py:func:`from_kql`.
    """


def _from_kql_value_recursive(
    condition: KQLValueCondition,
    /,
    *,
    options: _ConversionOptions,
) -> Query:
    """Convert a KQL condition on a given field to Elasticsearch, recursively.

    :param condition: Value condition.
    :param options: Options to use.
    :return: Result of the conversion.
    """
    if isinstance(condition, KQLValueAnd):
        rendered_conditions = [
            _from_kql_value_recursive(
                subcondition,
                options=options,
            )
            for subcondition in condition.conditions
        ]

        if len(rendered_conditions) == 1:
            return rendered_conditions[0]

        if options.filters_in_must_clause:
            return BooleanQuery(must=rendered_conditions)

        return BooleanQuery(filter=rendered_conditions)

    if isinstance(condition, KQLValueOr):
        rendered_conditions = [
            _from_kql_value_recursive(
                subcondition,
                options=options,
            )
            for subcondition in condition.conditions
        ]

        if len(rendered_conditions) == 1:
            return rendered_conditions[0]

        return BooleanQuery(should=rendered_conditions, minimum_should_match=1)

    if isinstance(condition, KQLValueNot):
        return BooleanQuery(
            must_not=_from_kql_value_recursive(
                condition.condition,
                options=options,
            ),
        )

    if isinstance(condition, KQLValueMatch):
        return MultiMatchQuery(query=condition.value, lenient=True)

    if isinstance(condition, KQLValuePhraseMatch):
        return MultiMatchQuery(
            type=MultiMatchQueryType.PHRASE,
            query=condition.value,
            lenient=True,
        )

    raise NotImplementedError()  # pragma: no cover


def _from_kql_field_value_recursive(
    condition: KQLValueCondition,
    /,
    *,
    field: str,
    options: _ConversionOptions,
) -> Query:
    """Convert a KQL condition on a given field to Elasticsearch, recursively.

    :param condition: Value condition.
    :param field: Optional field on which the condition applies.
    :param options: Options to use.
    :return: Result of the conversion.
    """
    if isinstance(condition, KQLValueAnd):
        rendered_conditions = [
            _from_kql_field_value_recursive(
                subcondition,
                field=field,
                options=options,
            )
            for subcondition in condition.conditions
        ]

        if len(rendered_conditions) == 1:
            return rendered_conditions[0]

        if options.filters_in_must_clause:
            return BooleanQuery(must=rendered_conditions)

        return BooleanQuery(filter=rendered_conditions)

    if isinstance(condition, KQLValueOr):
        rendered_conditions = [
            _from_kql_field_value_recursive(
                subcondition,
                field=field,
                options=options,
            )
            for subcondition in condition.conditions
        ]

        if len(rendered_conditions) == 1:
            return rendered_conditions[0]

        return BooleanQuery(should=rendered_conditions, minimum_should_match=1)

    if isinstance(condition, KQLValueNot):
        return BooleanQuery(
            must_not=_from_kql_field_value_recursive(
                condition.condition,
                field=field,
                options=options,
            ),
        )

    if isinstance(condition, KQLValueMatch):
        return MatchQuery(field=field, query=condition.value)

    if isinstance(condition, KQLValuePhraseMatch):
        return MatchPhraseQuery(field=field, query=condition.value)

    raise NotImplementedError()  # pragma: no cover


def _from_kql_recursive(
    query: KQLQuery,
    /,
    *,
    prefix: str,
    options: _ConversionOptions,
) -> Query:
    """Convert a KQL query to Elasticsearch, recursively.

    :param query: Query to convert.
    :param prefix: Current prefix.
    :param options: Options to use.
    :return: Result of the conversion.
    """
    if isinstance(query, KQLAll):
        return MatchAllQuery()

    if isinstance(query, KQLNested):
        return NestedQuery(
            path=query.path,
            query=_from_kql_recursive(
                query.query,
                prefix=prefix + query.path + ".",
                options=options,
            ),
            score_mode=NestedScoreMode.NONE,
        )

    if isinstance(query, KQLAnd):
        rendered_subqueries = tuple(
            _from_kql_recursive(subquery, prefix=prefix, options=options)
            for subquery in query.queries
        )
        if len(rendered_subqueries) == 1:
            return rendered_subqueries[0]

        if options.filters_in_must_clause:
            return BooleanQuery(must=rendered_subqueries)

        return BooleanQuery(filter=rendered_subqueries)

    if isinstance(query, KQLOr):
        rendered_subqueries = tuple(
            _from_kql_recursive(subquery, prefix=prefix, options=options)
            for subquery in query.queries
        )
        if len(rendered_subqueries) == 1:
            return rendered_subqueries[0]

        return BooleanQuery(should=rendered_subqueries, minimum_should_match=1)

    if isinstance(query, KQLNot):
        return BooleanQuery(
            must_not=_from_kql_recursive(
                query.query,
                prefix=prefix,
                options=options,
            ),
        )

    if isinstance(query, KQLGt):
        return RangeQuery(field=prefix + query.field, gt=query.value)

    if isinstance(query, KQLGte):
        return RangeQuery(field=prefix + query.field, gte=query.value)

    if isinstance(query, KQLLt):
        return RangeQuery(field=prefix + query.field, lt=query.value)

    if isinstance(query, KQLLte):
        return RangeQuery(field=prefix + query.field, lte=query.value)

    if isinstance(query, KQLExist):
        return ExistsQuery(field=prefix + query.field)

    if isinstance(query, KQLMatch):
        return _from_kql_field_value_recursive(
            query.condition,
            field=prefix + query.field,
            options=options,
        )

    if isinstance(query, KQLMultiMatch):
        return _from_kql_value_recursive(
            query.condition,
            options=options,
        )

    raise NotImplementedError()  # pragma: no cover


def from_kql(
    query: KQLQuery,
    /,
    *,
    filters_in_must_clause: bool = False,
) -> Query:
    """Convert a KQL query to Elasticsearch query.

    :param query: KQL Query to convert.
    :param filters_in_must_clause: Whether filters should be placed into
        the 'must' clause rather than 'filter' clause for boolean queries.
    :return: Obtained Elasticsearch query.
    """
    return _from_kql_recursive(
        query,
        prefix="",
        options=_ConversionOptions(
            filters_in_must_clause=filters_in_must_clause,
        ),
    )
