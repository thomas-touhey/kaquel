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


class BaseKQLValueCondition(BaseModel):
    """KQL value condition."""

    model_config = ConfigDict(extra="forbid")
    """Model configuration."""

    def __and__(self, other: Any, /) -> KQLValueCondition:
        if not isinstance(other, BaseKQLValueCondition):
            raise TypeError()

        if isinstance(self, KQLValueAnd):
            if isinstance(other, KQLValueAnd):
                return KQLValueAnd(
                    conditions=(*self.conditions, *other.conditions),
                )

            return KQLValueAnd(conditions=(*self.conditions, other))

        if isinstance(other, KQLValueAnd):
            return KQLValueAnd(conditions=(self, *other.conditions))

        return KQLValueAnd(conditions=(self, other))

    def __or__(self, other: Any, /) -> KQLValueCondition:
        if not isinstance(other, BaseKQLValueCondition):
            raise TypeError()

        if isinstance(self, KQLValueOr):
            if isinstance(other, KQLValueOr):
                return KQLValueOr(
                    conditions=(*self.conditions, *other.conditions),
                )

            return KQLValueOr(conditions=(*self.conditions, other))

        if isinstance(other, KQLValueOr):
            return KQLValueOr(conditions=(self, *other.conditions))

        return KQLValueOr(conditions=(self, other))

    def __invert__(self, /) -> KQLQuery:
        if isinstance(self, KQLValueNot):
            return self.condition

        return KQLValueNot(condition=self)


class KQLValueAll(BaseKQLValueCondition):
    """All match for a value."""


class KQLValueMatch(BaseKQLValueCondition):
    """Match for a value."""

    value: str | int | float | date
    """Value."""


class KQLValuePhraseMatch(BaseKQLValueCondition):
    """Phrase match for a value."""

    value: str | int | float | date
    """Value."""


class KQLValueAnd(BaseKQLValueCondition):
    """AND operator on a value condition."""

    conditions: Annotated[tuple[KQLValueCondition, ...], Len(min_length=1)]
    """Conditions."""


class KQLValueOr(BaseKQLValueCondition):
    """OR operator on a value condition."""

    conditions: Annotated[tuple[KQLValueCondition, ...], Len(min_length=1)]
    """Conditions."""


class KQLValueNot(BaseKQLValueCondition):
    """NOT operator on a value condition."""

    condition: KQLValueCondition
    """Condition."""


KQLValueCondition: TypeAlias = Union[
    KQLValueAll,
    KQLValueMatch,
    KQLValuePhraseMatch,
    KQLValueAnd,
    KQLValueOr,
    KQLValueNot,
]
"""Value condition."""

# HACK: Rebuild the models for circular dependencies.
KQLValueAnd.model_rebuild()
KQLValueOr.model_rebuild()
KQLValueNot.model_rebuild()


# ---
# Query.
# ---


class BaseKQLQuery(BaseModel):
    """KQL query."""

    model_config = ConfigDict(extra="forbid")
    """Model configuration."""

    def __and__(self, other: Any, /) -> KQLQuery:
        if not isinstance(other, BaseKQLQuery):
            raise TypeError()

        if isinstance(self, KQLAnd):
            if isinstance(other, KQLAnd):
                return KQLAnd(queries=(*self.queries, *other.queries))

            return KQLAnd(queries=(*self.queries, other))

        if isinstance(other, KQLAnd):
            return KQLAnd(queries=(self, *other.queries))

        return KQLAnd(queries=(self, other))

    def __or__(self, other: Any, /) -> KQLQuery:
        if not isinstance(other, BaseKQLQuery):
            raise TypeError()

        if isinstance(self, KQLOr):
            if isinstance(other, KQLOr):
                return KQLOr(queries=(*self.queries, *other.queries))

            return KQLOr(queries=(*self.queries, other))

        if isinstance(other, KQLOr):
            return KQLOr(queries=(self, *other.queries))

        return KQLOr(queries=(self, other))

    def __invert__(self, /) -> KQLQuery:
        if isinstance(self, KQLNot):
            return self.query

        return KQLNot(query=self)


class KQLAll(BaseKQLQuery):
    """Match-all query."""


class KQLNested(BaseKQLQuery):
    """Nested operator."""

    path: str
    """Path for the nested query."""

    query: KQLQuery
    """Subquery."""


class KQLNot(BaseKQLQuery):
    """NOT operator on a query."""

    query: KQLQuery
    """Subquery."""


class KQLAnd(BaseKQLQuery):
    """AND operator between multiple queries."""

    queries: Annotated[tuple[KQLQuery, ...], Len(min_length=1)]
    """Subqueries."""


class KQLOr(BaseKQLQuery):
    """OR operator between multiple queries."""

    queries: Annotated[tuple[KQLQuery, ...], Len(min_length=1)]
    """Subqueries."""


class KQLGt(BaseKQLQuery):
    """Greater than operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be greater than."""


class KQLGte(BaseKQLQuery):
    """Greater than or equal operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be greater than or equal."""


class KQLLt(BaseKQLQuery):
    """Less than operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be less than."""


class KQLLte(BaseKQLQuery):
    """Less than or equal operator."""

    field: str
    """Field on which the comparison is operated."""

    value: str | int | float | date
    """Value the field must be less than or equal."""


class KQLExist(BaseKQLQuery):
    """Exist operation."""

    field: str
    """Field to test the existence of."""


class KQLMatch(BaseKQLQuery):
    """Match operator between a field and its values."""

    field: str
    """Field name."""

    condition: KQLValueCondition
    """Value condition."""


class KQLMultiMatch(BaseKQLQuery):
    """Match operators for all selected fields."""

    condition: KQLValueCondition
    """Value condition."""


KQLQuery: TypeAlias = Union[
    KQLAll,
    KQLNested,
    KQLAnd,
    KQLOr,
    KQLNot,
    KQLGt,
    KQLGte,
    KQLLt,
    KQLLte,
    KQLExist,
    KQLMatch,
    KQLMultiMatch,
]
"""Query."""

# HACK: Resolve circular dependencies.
KQLAnd.model_rebuild()
KQLOr.model_rebuild()
KQLNot.model_rebuild()
