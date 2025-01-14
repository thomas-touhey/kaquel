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
"""KQL abstract language elements.

See :ref:`format-kql` for more information.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Union

from annotated_types import Len
from pydantic import BaseModel, ConfigDict
from typing_extensions import TypeAlias


# ---
# Value conditions.
# ---


class BaseValueCondition(BaseModel):
    """KQL value condition."""

    model_config = ConfigDict(extra="forbid")
    """Model configuration."""

    def __and__(self, other: Any, /) -> ValueCondition:
        if not isinstance(other, BaseValueCondition):
            raise TypeError()

        if isinstance(self, ValueAnd):
            if isinstance(other, ValueAnd):
                return ValueAnd(
                    conditions=(*self.conditions, *other.conditions),
                )

            return ValueAnd(conditions=(*self.conditions, other))

        if isinstance(other, ValueAnd):
            return ValueAnd(conditions=(self, *other.conditions))

        return ValueAnd(conditions=(self, other))

    def __or__(self, other: Any, /) -> Query:
        if not isinstance(other, BaseValueCondition):
            raise TypeError()

        if isinstance(self, ValueOr):
            if isinstance(other, ValueOr):
                return ValueOr(
                    conditions=(*self.conditions, *other.conditions),
                )

            return ValueOr(conditions=(*self.conditions, other))

        if isinstance(other, ValueOr):
            return ValueOr(conditions=(self, *other.conditions))

        return ValueOr(conditions=(self, other))

    def __invert__(self, /) -> Query:
        if isinstance(self, ValueNot):
            return self.condition

        return ValueNot(condition=self)


class ValueAll(BaseValueCondition):
    """All match for a value."""


class ValueMatch(BaseValueCondition):
    """Match for a value."""

    value: str | int | float | date
    """Value."""


class ValuePhraseMatch(BaseValueCondition):
    """Phrase match for a value."""

    value: str | int | float | date
    """Value."""


class ValueAnd(BaseValueCondition):
    """AND operator on a value condition."""

    conditions: Annotated[tuple[ValueCondition, ...], Len(min_length=1)]
    """Conditions."""


class ValueOr(BaseValueCondition):
    """OR operator on a value condition."""

    conditions: Annotated[tuple[ValueCondition, ...], Len(min_length=1)]
    """Conditions."""


class ValueNot(BaseValueCondition):
    """NOT operator on a value condition."""

    condition: ValueCondition
    """Condition."""


ValueCondition: TypeAlias = Union[
    ValueAll,
    ValueMatch,
    ValuePhraseMatch,
    ValueAnd,
    ValueOr,
    ValueNot,
]
"""Value condition."""

# HACK: Rebuild the models for circular dependencies.
ValueAnd.model_rebuild()
ValueOr.model_rebuild()
ValueNot.model_rebuild()


# ---
# Query.
# ---


class BaseQuery(BaseModel):
    """KQL query."""

    model_config = ConfigDict(extra="forbid")
    """Model configuration."""

    def __and__(self, other: Any, /) -> Query:
        if not isinstance(other, BaseQuery):
            raise TypeError()

        if isinstance(self, And):
            if isinstance(other, And):
                return And(queries=(*self.queries, *other.queries))

            return And(queries=(*self.queries, other))

        if isinstance(other, And):
            return And(queries=(self, *other.queries))

        return And(queries=(self, other))

    def __or__(self, other: Any, /) -> Query:
        if not isinstance(other, BaseQuery):
            raise TypeError()

        if isinstance(self, Or):
            if isinstance(other, Or):
                return Or(queries=(*self.queries, *other.queries))

            return Or(queries=(*self.queries, other))

        if isinstance(other, Or):
            return Or(queries=(self, *other.queries))

        return Or(queries=(self, other))

    def __invert__(self, /) -> Query:
        if isinstance(self, Not):
            return self.query

        return Not(query=self)


class All(BaseQuery):
    """Match-all query."""


class Nested(BaseQuery):
    """Nested operator."""

    path: str
    """Path for the nested query."""

    query: Query
    """Subquery."""


class Not(BaseQuery):
    """NOT operator on a query."""

    query: Query
    """Subquery."""


class And(BaseQuery):
    """AND operator between multiple queries."""

    queries: Annotated[tuple[Query, ...], Len(min_length=1)]
    """Subqueries."""


class Or(BaseQuery):
    """OR operator between multiple queries."""

    queries: Annotated[tuple[Query, ...], Len(min_length=1)]
    """Subqueries."""


class Gt(BaseQuery):
    """Greater than operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be greater than."""


class Gte(BaseQuery):
    """Greater than or equal operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be greater than or equal."""


class Lt(BaseQuery):
    """Less than operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be less than."""


class Lte(BaseQuery):
    """Less than or equal operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be less than or equal."""


class Exist(BaseQuery):
    """Exist operation."""

    field: str
    """Field to test the existence of."""


class Match(BaseQuery):
    """Match operator between a field and its values."""

    field: str
    """Field name."""

    condition: ValueCondition
    """Value condition."""


class MultiMatch(BaseQuery):
    """Match operators for all selected fields."""

    condition: ValueCondition
    """Value condition."""


Query: TypeAlias = Union[
    All,
    Nested,
    And,
    Or,
    Not,
    Gt,
    Gte,
    Lt,
    Lte,
    Exist,
    Match,
    MultiMatch,
]
"""Query."""

# HACK: Resolve circular dependencies.
And.model_rebuild()
Or.model_rebuild()
Not.model_rebuild()
