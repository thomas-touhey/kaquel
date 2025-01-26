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
"""KQL renderer.

See :ref:`format-kql` for more information.
"""

from __future__ import annotations

from datetime import date
import re

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
    KQLValueAnd,
    KQLValueCondition,
    KQLValueMatch,
    KQLValueNot,
    KQLValueOr,
    KQLValuePhraseMatch,
)
from .optimizer import optimize_kql as _optimize_kql


_KQL_TO_ESCAPE_PATTERN = re.compile(r'([\\\\():<>"])')
"""Pattern for finding sequences to escape."""


def _render_literal(literal: str | int | float | date, /) -> str:
    """Render a string as a KQL literal.

    This utility is able to escape said literal.

    :param literal: Literal to render.
    :return: Rendered literal.
    """
    if isinstance(literal, date):
        raw = literal.isoformat()
    else:
        raw = str(literal)

    return _KQL_TO_ESCAPE_PATTERN.sub(r"\\\1", raw)


def _render_value_condition_recursive(
    condition: KQLValueCondition,
    /,
    *,
    in_and: bool = False,
    in_not: bool = False,
) -> str:
    """Render the KQL query recursively.

    :param query: Query to render recursively.
    :param prefix: Prefix to remove from the field.
    :param in_and: Whether we are in an AND context, i.e. we need to add
        parenthesis if we have an OR.
    :param in_not: Whether we are in a NOT context.
    :return: Rendered query as KQL.
    """
    if isinstance(condition, KQLValueAnd):
        if len(condition.conditions) == 1:
            return _render_value_condition_recursive(
                condition.conditions[0],
                in_and=in_and,
                in_not=in_not,
            )

        result = " and ".join(
            _render_value_condition_recursive(subcondition, in_and=True)
            for subcondition in condition.conditions
        )
        if in_not:
            result = f"({result})"

        return result

    if isinstance(condition, KQLValueOr):
        if len(condition.conditions) == 1:
            return _render_value_condition_recursive(
                condition.conditions[0],
                in_and=in_and,
                in_not=in_not,
            )

        result = " or ".join(
            _render_value_condition_recursive(subcondition)
            for subcondition in condition.conditions
        )
        if in_and or in_not:
            result = f"({result})"

        return result

    if isinstance(condition, KQLValueNot):
        result = _render_value_condition_recursive(
            condition.condition,
            in_not=True,
        )
        return f"not {result}"

    if isinstance(condition, KQLValueMatch):
        return _render_literal(condition.value)

    if isinstance(condition, KQLValuePhraseMatch):
        return f'"{_render_literal(condition.value)}"'

    raise NotImplementedError()  # pragma: no cover


def _render_recursive(
    query: KQLQuery,
    /,
    *,
    in_and: bool = False,
    in_not: bool = False,
) -> str:
    """Render the KQL query recursively.

    :param query: Query to render recursively.
    :param prefix: Prefix to remove from the field.
    :param in_and: Whether we are in an AND context, i.e. we need to add
        parenthesis if we have an OR.
    :param in_not: Whether we are in a NOT context.
    :return: Rendered query as KQL.
    """
    if isinstance(query, KQLAll):
        return "*"

    if isinstance(query, KQLNested):
        result = _render_recursive(query.query)
        return f"{query.path}: {{ {result} }}"

    if isinstance(query, KQLAnd):
        if len(query.queries) == 1:
            return _render_recursive(
                query.queries[0],
                in_and=in_and,
                in_not=in_not,
            )

        result = " and ".join(
            _render_recursive(subquery, in_and=True)
            for subquery in query.queries
        )
        if in_not:
            result = f"({result})"

        return result

    if isinstance(query, KQLOr):
        if len(query.queries) == 1:
            return _render_recursive(
                query.queries[0],
                in_and=in_and,
                in_not=in_not,
            )

        result = " or ".join(
            _render_recursive(subquery) for subquery in query.queries
        )
        if in_and or in_not:
            result = f"({result})"

        return result

    if isinstance(query, KQLNot):
        result = _render_recursive(query.query, in_not=True)
        return f"not {result}"

    if isinstance(query, KQLGt):
        field = _render_literal(query.field)
        value = _render_literal(query.value)
        return f"{field} > {value}"

    if isinstance(query, KQLGte):
        field = _render_literal(query.field)
        value = _render_literal(query.value)
        return f"{field} >= {value}"

    if isinstance(query, KQLLt):
        field = _render_literal(query.field)
        value = _render_literal(query.value)
        return f"{field} < {value}"

    if isinstance(query, KQLLte):
        field = _render_literal(query.field)
        value = _render_literal(query.value)
        return f"{field} <= {value}"

    if isinstance(query, KQLExist):
        return f"{_render_literal(query.field)}: *"

    if isinstance(query, KQLMatch):
        field = _render_literal(query.field)
        value = _render_value_condition_recursive(query.condition, in_not=True)
        return f"{field}: {value}"

    if isinstance(query, KQLMultiMatch):
        return _render_value_condition_recursive(query.condition, in_not=True)

    raise NotImplementedError()  # pragma: no cover


def render_kql(query: KQLQuery, /, *, optimize: bool = False) -> str:
    """Render the KQL query.

    :param query: Query to render.
    :param optimize: Whether to optimize the request before rendering.
    :return: Rendered query.
    """
    if optimize:
        query = _optimize_kql(query)
    return _render_recursive(query)
