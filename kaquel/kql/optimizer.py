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
"""KQL query optimization / canonicalization."""

from __future__ import annotations

from collections import defaultdict

from .lang import (
    All,
    And,
    Exist,
    Gt,
    Gte,
    Lt,
    Lte,
    Match,
    MultiMatch,
    Nested,
    Not,
    Or,
    Query,
    ValueAll,
    ValueAnd,
    ValueCondition,
    ValueNot,
    ValueOr,
)


def _step1_negate_recursive(query: Query, /) -> Query:
    """Negate recursively in order not to keep a Not in the tree.

    :param query: Query to negate.
    :return: Negated query.
    """
    if isinstance(query, Nested):
        return Nested(
            path=query.path,
            query=_step1_negate_recursive(query.query),
        )

    if isinstance(query, Not):
        return query.query

    if isinstance(query, And):
        return Or(
            queries=(
                _step1_negate_recursive(subquery) for subquery in query.queries
            ),
        )

    if isinstance(query, Or):
        return And(
            queries=(
                _step1_negate_recursive(subquery) for subquery in query.queries
            ),
        )

    if isinstance(query, Match):
        return Match(
            field=query.field,
            condition=ValueNot(condition=query.condition),
        )

    if isinstance(query, MultiMatch):
        return MultiMatch(condition=ValueNot(condition=query.condition))

    if isinstance(query, Gt):
        return Lte(field=query.field, value=query.value)

    if isinstance(query, Gte):
        return Lt(field=query.field, value=query.value)

    if isinstance(query, Lt):
        return Gte(field=query.field, value=query.value)

    if isinstance(query, Lte):
        return Gt(field=query.field, value=query.value)

    return Not(query=query)


def _step1_recursive(query: Query, /) -> Query:
    """Run step 1 of the KQL query optimization procedure.

    This function does the following operation:

    * Flatten logical query operators AND, OR and NOT, i.e. transform
      ``a AND (b AND c)`` into ``a AND b AND c``, ``a OR (b OR c)`` into
      ``a OR b OR c`` and ``NOT (NOT a)`` into ``a``;
    * Group matches, multi-matches and exist queries recursively into common
      matches if possible, i.e. transform ``a: 1 AND (a: 2 OR a: 3)`` into
      ``a: (1 AND (2 OR 3))``, and ``1 AND (2 OR 3)`` into
      ``*: (1 AND (2 OR 3))``;
    * Group exist and match queries for the same fields, i.e. transform
      ``a: * AND a: 5 AND a: 6`` into ``a: (5 AND 6)`` and
      ``a: * OR a: 5 OR a: 6`` into ``a: *`` (and equiv. for multi-matches).

    :param query: Query to optimize.
    :return: Optimized query.
    """
    if isinstance(query, Not):
        return _step1_negate_recursive(query.query)

    if isinstance(query, And):
        # First, we want to flatten subqueries on all levels.
        subqueries: list[Query] = []
        for subquery in query.queries:
            subquery = _step1_recursive(subquery)

            if isinstance(subquery, And):
                subqueries.extend(subquery.queries)
            else:
                subqueries.append(subquery)

        # Now, we want to group all matches by the field they are impacting.
        multi_conditions: list[ValueCondition] = []
        field_exist: set[str] = set()
        conditions_by_field: defaultdict[
            str,
            list[ValueCondition],
        ] = defaultdict(list)
        other_subqueries: list[Query] = []
        for subquery in subqueries:
            if isinstance(subquery, Match):
                conditions_by_field[subquery.field].append(
                    subquery.condition,
                )
            elif isinstance(subquery, MultiMatch):
                multi_conditions.append(subquery.condition)
            elif isinstance(subquery, Exist):
                field_exist.add(subquery.field)
            else:
                other_subqueries.append(subquery)

        subqueries = []
        for field in sorted(set(field_exist).union(conditions_by_field)):
            conditions = conditions_by_field[field]
            if conditions:
                subqueries.append(
                    Match(
                        field=field,
                        condition=ValueAnd(conditions=conditions),
                    ),
                )
            else:
                subqueries.append(Exist(field=field))

        if multi_conditions:
            subqueries.append(
                MultiMatch(condition=ValueAnd(conditions=multi_conditions)),
            )

        subqueries.extend(other_subqueries)
        return And(queries=subqueries)

    if isinstance(query, Or):
        # First, we want to flatten subqueries on all levels.
        subqueries = []
        for subquery in query.queries:
            subquery = _step1_recursive(subquery)

            if isinstance(subquery, Or):
                subqueries.extend(subquery.queries)
            else:
                subqueries.append(subquery)

        # Now, we want to group all matches by the field they are impacting.
        multi_conditions = []
        field_exist = set()
        conditions_by_field = defaultdict(list)
        other_subqueries = []
        for subquery in subqueries:
            if isinstance(subquery, Match):
                conditions_by_field[subquery.field].append(
                    subquery.condition,
                )
            elif isinstance(subquery, MultiMatch):
                multi_conditions.append(subquery.condition)
            elif isinstance(subquery, Exist):
                field_exist.add(subquery.field)
            else:
                other_subqueries.append(subquery)

        subqueries = []
        for field in sorted(set(field_exist).union(conditions_by_field)):
            conditions = conditions_by_field[field]
            # As opposed to AND, the winning condition here is the weakest,
            # being the simple existence of the field.
            if field in field_exist:
                subqueries.append(Exist(field=field))
            else:
                subqueries.append(
                    Match(
                        field=field,
                        condition=ValueOr(conditions=conditions),
                    ),
                )

        if multi_conditions:
            subqueries.append(
                MultiMatch(condition=ValueOr(conditions=multi_conditions)),
            )

        subqueries.extend(other_subqueries)
        return Or(queries=subqueries)

    return query


def _step2_recursive(
    condition: ValueCondition,
    /,
) -> ValueCondition:
    """Run step 2 of the KQL optimization procedure recursively.

    This function does the following operations:

    * Flatten logical query operators AND, OR and NOT, i.e. transform
      ``a AND (b AND c)`` into ``a AND b AND c``, ``a OR (b OR c)`` into
      ``a OR b OR c`` and ``NOT (NOT a)`` into ``a``;
    * Eliminates all ORs that have at least one ``*``, recursively, i.e.
      transform ``a OR (b OR *)`` into ``*``;
    * Eliminate ``*`` from all ANDs and transform ANDs with no conditions left
      with ``*``, i.e. transform ``a AND *`` into ``a`` and ``* AND *`` into
      ``*``.

    :param condition: Value condition to canonicalize.
    :return: Canonical value condition.
    """
    if isinstance(condition, ValueNot):
        # We want to eliminate double NOTs.
        subcondition = condition.condition
        if isinstance(subcondition, ValueNot):
            return _step2_recursive(
                subcondition.condition,
            )

        subcondition = _step2_recursive(subcondition)
        return ValueNot(condition=subcondition)

    if isinstance(condition, ValueAnd):
        # We want to merge ANDs.
        subconditions: list[ValueCondition] = []
        for subcondition in condition.conditions:
            subcondition = _step2_recursive(
                subcondition,
            )

            if isinstance(subcondition, ValueAll):
                continue

            if isinstance(subcondition, ValueAnd):
                subconditions.extend(subcondition.conditions)
            else:
                subconditions.append(subcondition)

        if not subconditions:
            return ValueAll()

        if len(subconditions) == 1:
            return subconditions[0]

        # "(NOT a AND NOT b)" is equivalent to "NOT (a OR b)", which is a form
        # we prefer.
        if any(
            not isinstance(subcondition, ValueNot)
            for subcondition in subconditions
        ):
            return ValueAnd(conditions=subconditions)

        negated_subconditions = (
            subcondition.condition for subcondition in subconditions
        )

        return ValueNot(condition=ValueOr(conditions=negated_subconditions))

    if isinstance(condition, ValueOr):
        # We want to merge ORs.
        subconditions = []
        for subcondition in condition.conditions:
            subcondition = _step2_recursive(subcondition)

            if isinstance(subcondition, ValueAll):
                return ValueAll()

            if isinstance(subcondition, ValueOr):
                subconditions.extend(subcondition.conditions)
            else:
                subconditions.append(subcondition)

        if len(subconditions) == 1:
            return subconditions[0]

        # "(NOT a OR NOT b)" is equivalent to "NOT (a AND b)", which is a form
        # we prefer.
        if any(
            not isinstance(subcondition, ValueNot)
            for subcondition in subconditions
        ):
            return ValueOr(conditions=subconditions)

        negated_subconditions = (
            subcondition.condition for subcondition in subconditions
        )

        return ValueNot(condition=ValueAnd(conditions=negated_subconditions))

    return condition


def _step3_recursive(query: Query, /) -> Query:
    """Run step 3 of the KQL optimization procedure recursively.

    This function does the following operations:

    * Replace any match or multi-match with a proeminent NOT into a query-wise
      NOT, i.e. replace ``a: (NOT b)`` into ``NOT a: b``;
    * Replace any match with a ``*`` condition into an exists, i.e. replace
      ``a: (*)`` into ``a: *``;
    * Replace any multi-match with a ``*`` condition into a ``*``, i.e. replace
      ``*: (*)`` into ``*``;
    * Eliminates all ORs that have at least one ``*``, recursively, i.e.
      transform ``a OR (b OR *)`` into ``*``;
    * Eliminate ``*`` from all ANDs and transform ANDs with no conditions left
      with ``*``, i.e. transform ``a AND *`` into ``a`` and ``* AND *`` into
      ``*``.

    For convenience, rather than exploring recursively after step 2, this
    function also step 3 directly on any match or multi-match leaf.

    :param query: Query for which to optimize and canonicalize conditions.
    :return: Obtained query.
    """
    if isinstance(query, Nested):
        return Nested(path=query.path, query=_step3_recursive(query.query))

    if isinstance(query, And):
        subqueries = [
            _step3_recursive(subquery)
            for subquery in query.queries
            if not isinstance(subquery, All)
        ]
        if not subqueries or any(
            isinstance(subquery, Not) and isinstance(subquery.query, All)
            for subquery in subqueries
        ):
            return All()

        if len(subqueries) == 1:
            return subqueries[0]

        # "(NOT a AND NOT b)" is equivalent to "NOT (a OR b)", which is a form
        # we prefer.
        if all(
            not isinstance(subquery, Not) for subquery in subqueries
        ) or any(
            not isinstance(subquery, (Not, Gt, Gte, Lt, Lte))
            for subquery in subqueries
        ):
            return And(queries=subqueries)

        negated_subqueries = (
            subquery.query
            if isinstance(subquery, Not)
            else Lte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Gt)
            else Lt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Gte)
            else Gte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Lt)
            else Gt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Lte)
            else Not(query=subquery)
            for subquery in subqueries
        )

        return Not(query=Or(queries=negated_subqueries))

    if isinstance(query, Or):
        subqueries = [
            _step3_recursive(subquery)
            for subquery in query.queries
            if not isinstance(subquery, Not)
            or not isinstance(subquery.query, All)
        ]
        if not subqueries or any(
            isinstance(subquery, All) for subquery in subqueries
        ):
            return All()

        if len(subqueries) == 1:
            return subqueries[0]

        # "(NOT a OR NOT b)" is equivalent to "NOT (a AND b)", which is a form
        # we prefer.
        if all(
            not isinstance(subquery, Not) for subquery in subqueries
        ) or any(
            not isinstance(subquery, (Not, Gt, Gte, Lt, Lte))
            for subquery in subqueries
        ):
            return Or(queries=subqueries)

        negated_subqueries = (
            subquery.query
            if isinstance(subquery, Not)
            else Lte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Gt)
            else Lt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Gte)
            else Gte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Lt)
            else Gt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, Lte)
            else Not(query=subquery)
            for subquery in subqueries
        )

        return Not(query=And(queries=negated_subqueries))

    if isinstance(query, Match):
        condition = _step2_recursive(query.condition)
        is_not = False
        if isinstance(condition, ValueNot):
            is_not = True
            condition = condition.condition

        if isinstance(condition, ValueAll):
            query = Exist(field=query.field)
        else:
            query = Match(field=query.field, condition=condition)

        if is_not:
            query = Not(query=query)

        return query

    if isinstance(query, MultiMatch):
        condition = _step2_recursive(query.condition)
        is_not = False
        if isinstance(condition, ValueNot):
            is_not = True
            condition = condition.condition

        if isinstance(condition, ValueAll):
            query = All()
        else:
            query = MultiMatch(condition=condition)

        if is_not:
            query = Not(query=query)

        return query

    return query


def optimize_kql(query: Query, /) -> Query:
    """Optimize a KQL query.

    :param query: Query to optimize.
    :return: Optimized query.
    """
    query = _step1_recursive(query)
    return _step3_recursive(query)
