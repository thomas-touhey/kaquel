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
"""ES query to KQL conversion."""

from __future__ import annotations

from itertools import chain

from pydantic import BaseModel, ConfigDict

from kaquel.errors import RenderError
from kaquel.query import (
    BooleanQuery,
    ExistsQuery,
    Query,
    MatchAllQuery,
    MatchPhraseQuery,
    MatchQuery,
    MultiMatchQuery,
    MultiMatchQueryType,
    NestedQuery,
    NestedScoreMode,
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
    ValueMatch as KQLValueMatch,
    ValuePhraseMatch as KQLValuePhraseMatch,
)


class _ConversionOptions(BaseModel):
    """Conversion options."""

    model_config = ConfigDict(extra="forbid")
    """Model configuration."""

    filters_in_must_clause: bool
    """Whether filters should be retrieved from the 'must' clause of boolean
    queries.
    """


def _to_kql_recursive(
    query: Query,
    /,
    *,
    prefix: str,
    options: _ConversionOptions,
) -> KQLQuery:
    """Convert an Elasticsearch query to a KQL query, recursively.

    :param query: Query to convert to KQL.
    :param prefix: Prefix to remove from the fields.
    :param options: Options.
    :return: KQL query.
    """
    if isinstance(query, BooleanQuery):
        if options.filters_in_must_clause:
            if query.filter:
                raise RenderError(
                    "Cannot render a boolean query with filter clause and "
                    + "filters_in_must_clause=True",
                )
        elif query.must:
            raise RenderError(
                "Cannot render a boolean query with must clause and "
                + "filters_in_must_clause=False",
            )

        # If 'minimum_should_match' is defined, and does not match either 1
        # (OR clause) or the number of clauses in 'should' (AND clause), it is
        # not renderable as KQL.
        if query.should and query.minimum_should_match == len(query.should):
            query = BooleanQuery(
                filter=chain(query.filter, query.must, query.should),
                must_not=query.must_not,
            )
        elif query.minimum_should_match not in (None, 1):
            raise RenderError(
                "Cannot render a boolean query with complex "
                + "minimum_should_match value",
            )

        if not query.must and not query.filter and not query.must_not:
            # We are facing an OR clause.
            if not query.should:
                raise RenderError("Cannot render an empty boolean query.")

            results = [
                _to_kql_recursive(
                    subquery,
                    prefix=prefix,
                    options=options,
                )
                for subquery in query.should
            ]
            if len(results) == 1:
                return results[0]

            return KQLOr(queries=results)

        if query.should:
            # We are facing a statement with both ORs and ANDs.
            # To simplify processing here, we want to place the OR in the
            # ANDs.
            query = BooleanQuery(
                filter=chain(
                    query.filter,
                    query.must,
                    (
                        BooleanQuery(
                            should=query.should,
                            minimum_should_match=1,
                        ),
                    ),
                ),
                must_not=query.must_not,
            )

        # We are facing an AND clause.
        results = [
            _to_kql_recursive(subquery, prefix=prefix, options=options)
            for subquery in chain(query.must, query.filter)
        ]
        not_results = [
            _to_kql_recursive(subquery, prefix=prefix, options=options)
            for subquery in query.must_not
        ]
        if len(not_results) == 1:
            results.append(KQLNot(query=not_results[0]))
        elif not_results:
            results.append(KQLNot(query=KQLOr(queries=not_results)))

        if len(results) == 1:
            return results[0]

        return KQLAnd(queries=results)

    if isinstance(query, ExistsQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        return KQLExist(field=query.field[len(prefix) :])

    if isinstance(query, MatchAllQuery):
        return KQLAll()

    if isinstance(query, MatchPhraseQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        return KQLMatch(
            field=query.field[len(prefix) :],
            condition=KQLValuePhraseMatch(value=query.query),
        )

    if isinstance(query, MatchQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        return KQLMatch(
            field=query.field[len(prefix) :],
            condition=KQLValueMatch(value=query.query),
        )

    if isinstance(query, MultiMatchQuery):
        if not query.lenient:
            raise RenderError("Expected a lenient multi-match query")

        if query.fields:
            raise RenderError(
                "Cannot render a multi-match with specific fields",
            )

        if query.type == MultiMatchQueryType.BEST_FIELDS:
            return KQLMultiMatch(condition=KQLValueMatch(value=query.query))

        if query.type == MultiMatchQueryType.PHRASE:
            return KQLMultiMatch(
                condition=KQLValuePhraseMatch(value=query.query),
            )

        raise RenderError(
            f"Cannot render a multi-match query with type {query.type}",
        )

    if isinstance(query, NestedQuery):
        if query.score_mode != NestedScoreMode.NONE:
            raise RenderError(
                "Cannot render a nested query with score mode "
                + f"{query.score_mode}",
            )

        if not query.path.startswith(prefix):
            raise RenderError(
                f"Nested query path does not start with prefix {prefix}",
            )

        return KQLNested(
            path=query.path[len(prefix) :],
            query=_to_kql_recursive(
                query.query,
                prefix=query.path + ".",
                options=options,
            ),
        )

    if isinstance(query, RangeQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        and_clauses: list[KQLQuery] = []
        field = query.field[len(prefix) :]

        if query.gt is not None:
            and_clauses.append(KQLGt(field=field, value=query.gt))
        if query.gte is not None:
            and_clauses.append(KQLGte(field=field, value=query.gte))
        if query.lt is not None:
            and_clauses.append(KQLLt(field=field, value=query.lt))
        if query.lte is not None:
            and_clauses.append(KQLLte(field=field, value=query.lte))

        if len(and_clauses) == 1:
            return and_clauses[0]

        return KQLAnd(queries=and_clauses)

    raise RenderError(  # pragma: no cover
        f"Cannot render a {query.__class__.__name__}",
    )


def to_kql(
    query: Query,
    /,
    *,
    filters_in_must_clause: bool = False,
) -> KQLQuery:
    """Convert an Elasticsearch query to a KQL query.

    :param query: Elasticsearch query to convert.
    :param filters_in_must_clause: Whether filters should be retrieved from
        the 'must' clause rather than 'filter' clause for boolean queries.
    :return: Obtained KQL query.
    """
    return _to_kql_recursive(
        query,
        prefix="",
        options=_ConversionOptions(
            filters_in_must_clause=filters_in_must_clause,
        ),
    )
