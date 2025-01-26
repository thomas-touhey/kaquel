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
    KQLAll,
    KQLAnd,
    KQLExist,
    KQLGt,
    KQLGte,
    KQLLt,
    KQLLte,
    KQLMatch,
    KQLMultiMatch,
    KQLNested,
    KQLNot,
    KQLOr,
    KQLQuery,
    KQLValueAll,
    KQLValueAnd,
    KQLValueCondition,
    KQLValueNot,
    KQLValueOr,
)


def _step1_negate_recursive(query: KQLQuery, /) -> KQLQuery:
    """Negate recursively in order not to keep a Not in the tree.

    :param query: Query to negate.
    :return: Negated query.
    """
    if isinstance(query, KQLNested):
        return KQLNested(
            path=query.path,
            query=_step1_negate_recursive(query.query),
        )

    if isinstance(query, KQLNot):
        return query.query

    if isinstance(query, KQLAnd):
        return KQLOr(
            queries=(
                _step1_negate_recursive(subquery) for subquery in query.queries
            ),
        )

    if isinstance(query, KQLOr):
        return KQLAnd(
            queries=(
                _step1_negate_recursive(subquery) for subquery in query.queries
            ),
        )

    if isinstance(query, KQLMatch):
        return KQLMatch(
            field=query.field,
            condition=KQLValueNot(condition=query.condition),
        )

    if isinstance(query, KQLMultiMatch):
        return KQLMultiMatch(condition=KQLValueNot(condition=query.condition))

    if isinstance(query, KQLGt):
        return KQLLte(field=query.field, value=query.value)

    if isinstance(query, KQLGte):
        return KQLLt(field=query.field, value=query.value)

    if isinstance(query, KQLLt):
        return KQLGte(field=query.field, value=query.value)

    if isinstance(query, KQLLte):
        return KQLGt(field=query.field, value=query.value)

    return KQLNot(query=query)


def _step1_recursive(query: KQLQuery, /) -> KQLQuery:
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
    if isinstance(query, KQLNot):
        return _step1_negate_recursive(query.query)

    if isinstance(query, KQLAnd):
        # First, we want to flatten subqueries on all levels.
        subqueries: list[KQLQuery] = []
        for subquery in query.queries:
            subquery = _step1_recursive(subquery)

            if isinstance(subquery, KQLAnd):
                subqueries.extend(subquery.queries)
            else:
                subqueries.append(subquery)

        # Now, we want to group all matches by the field they are impacting.
        multi_conditions: list[KQLValueCondition] = []
        field_exist: set[str] = set()
        conditions_by_field: defaultdict[
            str,
            list[KQLValueCondition],
        ] = defaultdict(list)
        other_subqueries: list[KQLQuery] = []
        for subquery in subqueries:
            if isinstance(subquery, KQLMatch):
                conditions_by_field[subquery.field].append(
                    subquery.condition,
                )
            elif isinstance(subquery, KQLMultiMatch):
                multi_conditions.append(subquery.condition)
            elif isinstance(subquery, KQLExist):
                field_exist.add(subquery.field)
            else:
                other_subqueries.append(subquery)

        subqueries = []
        for field in sorted(set(field_exist).union(conditions_by_field)):
            conditions = conditions_by_field[field]
            if conditions:
                subqueries.append(
                    KQLMatch(
                        field=field,
                        condition=KQLValueAnd(conditions=conditions),
                    ),
                )
            else:
                subqueries.append(KQLExist(field=field))

        if multi_conditions:
            subqueries.append(
                KQLMultiMatch(
                    condition=KQLValueAnd(
                        conditions=multi_conditions,
                    ),
                ),
            )

        subqueries.extend(other_subqueries)
        return KQLAnd(queries=subqueries)

    if isinstance(query, KQLOr):
        # First, we want to flatten subqueries on all levels.
        subqueries = []
        for subquery in query.queries:
            subquery = _step1_recursive(subquery)

            if isinstance(subquery, KQLOr):
                subqueries.extend(subquery.queries)
            else:
                subqueries.append(subquery)

        # Now, we want to group all matches by the field they are impacting.
        multi_conditions = []
        field_exist = set()
        conditions_by_field = defaultdict(list)
        other_subqueries = []
        for subquery in subqueries:
            if isinstance(subquery, KQLMatch):
                conditions_by_field[subquery.field].append(
                    subquery.condition,
                )
            elif isinstance(subquery, KQLMultiMatch):
                multi_conditions.append(subquery.condition)
            elif isinstance(subquery, KQLExist):
                field_exist.add(subquery.field)
            else:
                other_subqueries.append(subquery)

        subqueries = []
        for field in sorted(set(field_exist).union(conditions_by_field)):
            conditions = conditions_by_field[field]
            # As opposed to AND, the winning condition here is the weakest,
            # being the simple existence of the field.
            if field in field_exist:
                subqueries.append(KQLExist(field=field))
            else:
                subqueries.append(
                    KQLMatch(
                        field=field,
                        condition=KQLValueOr(conditions=conditions),
                    ),
                )

        if multi_conditions:
            subqueries.append(
                KQLMultiMatch(
                    condition=KQLValueOr(
                        conditions=multi_conditions,
                    ),
                ),
            )

        subqueries.extend(other_subqueries)
        return KQLOr(queries=subqueries)

    return query


def _step2_recursive(
    condition: KQLValueCondition,
    /,
) -> KQLValueCondition:
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
    if isinstance(condition, KQLValueNot):
        # We want to eliminate double NOTs.
        subcondition = condition.condition
        if isinstance(subcondition, KQLValueNot):
            return _step2_recursive(
                subcondition.condition,
            )

        subcondition = _step2_recursive(subcondition)
        return KQLValueNot(condition=subcondition)

    if isinstance(condition, KQLValueAnd):
        # We want to merge ANDs.
        subconditions: list[KQLValueCondition] = []
        for subcondition in condition.conditions:
            subcondition = _step2_recursive(
                subcondition,
            )

            if isinstance(subcondition, KQLValueAll):
                continue

            if isinstance(subcondition, KQLValueAnd):
                subconditions.extend(subcondition.conditions)
            else:
                subconditions.append(subcondition)

        if not subconditions:
            return KQLValueAll()

        if len(subconditions) == 1:
            return subconditions[0]

        # "(NOT a AND NOT b)" is equivalent to "NOT (a OR b)", which is a form
        # we prefer.
        if any(
            not isinstance(subcondition, KQLValueNot)
            for subcondition in subconditions
        ):
            return KQLValueAnd(conditions=subconditions)

        negated_subconditions = (
            subcondition.condition for subcondition in subconditions
        )

        return KQLValueNot(
            condition=KQLValueOr(conditions=negated_subconditions),
        )

    if isinstance(condition, KQLValueOr):
        # We want to merge ORs.
        subconditions = []
        for subcondition in condition.conditions:
            subcondition = _step2_recursive(subcondition)

            if isinstance(subcondition, KQLValueAll):
                return KQLValueAll()

            if isinstance(subcondition, KQLValueOr):
                subconditions.extend(subcondition.conditions)
            else:
                subconditions.append(subcondition)

        if len(subconditions) == 1:
            return subconditions[0]

        # "(NOT a OR NOT b)" is equivalent to "NOT (a AND b)", which is a form
        # we prefer.
        if any(
            not isinstance(subcondition, KQLValueNot)
            for subcondition in subconditions
        ):
            return KQLValueOr(conditions=subconditions)

        negated_subconditions = (
            subcondition.condition for subcondition in subconditions
        )

        return KQLValueNot(
            condition=KQLValueAnd(
                conditions=negated_subconditions,
            ),
        )

    return condition


def _step3_recursive(query: KQLQuery, /) -> KQLQuery:
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
    if isinstance(query, KQLNested):
        return KQLNested(path=query.path, query=_step3_recursive(query.query))

    if isinstance(query, KQLAnd):
        subqueries = [
            _step3_recursive(subquery)
            for subquery in query.queries
            if not isinstance(subquery, KQLAll)
        ]
        if not subqueries or any(
            isinstance(subquery, KQLNot) and isinstance(subquery.query, KQLAll)
            for subquery in subqueries
        ):
            return KQLAll()

        if len(subqueries) == 1:
            return subqueries[0]

        # "(NOT a AND NOT b)" is equivalent to "NOT (a OR b)", which is a form
        # we prefer.
        if all(
            not isinstance(subquery, KQLNot) for subquery in subqueries
        ) or any(
            not isinstance(subquery, (KQLNot, KQLGt, KQLGte, KQLLt, KQLLte))
            for subquery in subqueries
        ):
            return KQLAnd(queries=subqueries)

        negated_subqueries = (
            subquery.query
            if isinstance(subquery, KQLNot)
            else KQLLte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLGt)
            else KQLLt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLGte)
            else KQLGte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLLt)
            else KQLGt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLLte)
            else KQLNot(query=subquery)
            for subquery in subqueries
        )

        return KQLNot(query=KQLOr(queries=negated_subqueries))

    if isinstance(query, KQLOr):
        subqueries = [
            _step3_recursive(subquery)
            for subquery in query.queries
            if not isinstance(subquery, KQLNot)
            or not isinstance(subquery.query, KQLAll)
        ]
        if not subqueries or any(
            isinstance(subquery, KQLAll) for subquery in subqueries
        ):
            return KQLAll()

        if len(subqueries) == 1:
            return subqueries[0]

        # "(NOT a OR NOT b)" is equivalent to "NOT (a AND b)", which is a form
        # we prefer.
        if all(
            not isinstance(subquery, KQLNot) for subquery in subqueries
        ) or any(
            not isinstance(subquery, (KQLNot, KQLGt, KQLGte, KQLLt, KQLLte))
            for subquery in subqueries
        ):
            return KQLOr(queries=subqueries)

        negated_subqueries = (
            subquery.query
            if isinstance(subquery, KQLNot)
            else KQLLte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLGt)
            else KQLLt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLGte)
            else KQLGte(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLLt)
            else KQLGt(field=subquery.field, value=subquery.value)
            if isinstance(subquery, KQLLte)
            else KQLNot(query=subquery)
            for subquery in subqueries
        )

        return KQLNot(query=KQLAnd(queries=negated_subqueries))

    if isinstance(query, KQLMatch):
        condition = _step2_recursive(query.condition)
        is_not = False
        if isinstance(condition, KQLValueNot):
            is_not = True
            condition = condition.condition

        if isinstance(condition, KQLValueAll):
            query = KQLExist(field=query.field)
        else:
            query = KQLMatch(field=query.field, condition=condition)

        if is_not:
            query = KQLNot(query=query)

        return query

    if isinstance(query, KQLMultiMatch):
        condition = _step2_recursive(query.condition)
        is_not = False
        if isinstance(condition, KQLValueNot):
            is_not = True
            condition = condition.condition

        if isinstance(condition, KQLValueAll):
            query = KQLAll()
        else:
            query = KQLMultiMatch(condition=condition)

        if is_not:
            query = KQLNot(query=query)

        return query

    return query


def optimize_kql(query: KQLQuery, /) -> KQLQuery:
    """Optimize a KQL query.

    :param query: Query to optimize.
    :return: Optimized query.
    """
    query = _step1_recursive(query)
    return _step3_recursive(query)
