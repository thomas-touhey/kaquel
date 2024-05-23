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
"""ElasticSearch query domain-specific language.

See `Query DSL`_ for more information.

.. _Query DSL:
    https://www.elastic.co/guide/en/elasticsearch/reference/current
    /query-dsl.html
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class Query(BaseModel, ABC):
    """Any query."""

    model_config = ConfigDict(extra="forbid")
    """Model configuration."""

    @abstractmethod
    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        """


class BooleanQuery(Query):
    """Boolean query.

    See `Boolean query`_ for more information.

    .. _Boolean query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-bool-query.html
    """

    must: Annotated[list[Query], Field(default_factory=list)]
    """Clauses that must appear in matching documents."""

    filter: Annotated[list[Query], Field(default_factory=list)]
    """Clauses that must appear in matching documents."""

    should: Annotated[list[Query], Field(default_factory=list)]
    """Clauses that should appear in the matching document."""

    must_not: Annotated[list[Query], Field(default_factory=list)]
    """Clauses that must not appear in the matching document."""

    minimum_should_match: int | None = None
    """Number or percentage of "should" clauses the document must match."""

    @field_validator("must", "filter", "should", "must_not", mode="before")
    @classmethod
    def _make_clauses_lists(cls, value: Any) -> Any:
        """Ensure that clauses are transformed into a list.

        :param value: Value to transform.
        :return: Transformed value.
        """
        if isinstance(value, Query):
            return [value]
        return value

    @model_validator(mode="after")
    def _normalize_minimum_should_match(self, /) -> BooleanQuery:
        """Normalize the minimum should clauses a document should match.

        :return: Normalized object.
        """
        minimum_should_match = self.minimum_should_match
        if self.should and not self.must and not self.filter:
            if minimum_should_match == 1:
                self.minimum_should_match = None
        elif minimum_should_match == 0:
            self.minimum_should_match = None

        return self

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        result = {}

        for key in ("must", "filter", "should", "must_not"):
            value = getattr(self, key)
            if not value:
                pass
            elif len(value) == 1:
                result[key] = value[0].render()
            else:
                result[key] = [query.render() for query in value]

        if self.minimum_should_match is not None:
            result["minimum_should_match"] = self.minimum_should_match

        return {"bool": result}


class ExistsQuery(Query):
    """Exists query.

    See `Exists query`_ for more information.

    .. _Exists query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-exists-query.html
    """

    field: Annotated[str, StringConstraints(min_length=1)]
    """Name of the field to check the existence of."""

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        return {"exists": {"field": self.field}}


class MatchAllQuery(Query):
    """Match all query.

    See `Match all query`_ for more information.

    .. _Match all query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-match-all-query.html
    """

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        return {"match_all": {}}


class MatchPhraseQuery(Query):
    """Match phrase query.

    See `Match phrase query`_ for more information.

    .. _Match phrase query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-match-query-phrase.html
    """

    field: Annotated[str, StringConstraints(min_length=1)]
    """Name of the field on which to make the query."""

    query: str | bool | int | float | date
    """Query."""

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        return {"match_phrase": {self.field: self.query}}


class MatchQuery(Query):
    """Match query.

    See `Match query`_ for more information.

    .. _Match query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-match-query.html
    """

    field: Annotated[str, StringConstraints(min_length=1)]
    """Name of the field on which to make the query."""

    query: str | bool | int | float | date
    """Query."""

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        return {"match": {self.field: self.query}}


class MultiMatchQueryType(str, Enum):
    """Multi-match query type.

    See `multi_match query types`_ for more information.

    .. _multi_match query types:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-multi-match-query.html#multi-match-types
    """

    BEST_FIELDS = "best_fields"
    """Find documents which match any field, but use the best field's score."""

    MOST_FIELDS = "most_fields"
    """Find documents which match any field, and combines each score."""

    CROSS_FIELDS = "cross_fields"
    """Treat fields with the same analyzer as if they were one field."""

    PHRASE = "phrase"
    """Run a ``match_phrase`` query on each field."""

    PHRASE_PREFIX = "phrase_prefix"
    """Run a ``match_phrase_prefix`` query on each field."""

    BOOL_PREFIX = "bool_prefix"
    """Run a ``match_bool_prefix`` query on each field."""


class MultiMatchQuery(Query):
    """Multi-match query.

    See `Multi-match query`_ and `Query string query`_ for more information.

    .. _Multi-match query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-multi-match-query.html
    .. _Query string query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-query-string-query.html
    """

    type: MultiMatchQueryType = MultiMatchQueryType.BEST_FIELDS
    """Multi-match query type."""

    query: str
    """Query string."""

    fields: list[Annotated[str, StringConstraints(min_length=1)]] | None = None
    """Fields to be queried, with optional wildcards."""

    lenient: bool = False
    """Whether to ignore format-based errors or not."""

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        result: dict[str, Any] = {
            "type": self.type.value,
            "query": self.query,
        }
        if self.fields is not None:
            result["fields"] = self.fields
        if self.lenient:
            result["lenient"] = True

        return {"multi_match": result}


class NestedScoreMode(str, Enum):
    """Mode in which a nested query affects the root document's score."""

    AVG = "avg"
    """Use the mean relevance score of all matching child objects."""

    MAX = "max"
    """Use the highest relevance score of all matching child objects."""

    MIN = "min"
    """Use the lowest relevance score of all matching child objects."""

    NONE = "none"
    """Do not use the relevance score of matching child objects."""

    SUM = "sum"
    """Add together the relevance scores of all matching child objects."""


class NestedQuery(Query):
    """Nested query.

    See `Nested query`_ for more information.

    .. _Nested query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-nested-query.html
    """

    path: Annotated[str, StringConstraints(min_length=1)]
    """Path to the nested object to search."""

    query: Query
    """Nested query."""

    score_mode: NestedScoreMode = NestedScoreMode.AVG
    """Score mode."""

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        result = {
            "path": self.path,
            "query": self.query.render(),
            "score_mode": self.score_mode.value,
        }

        return {"nested": result}


class QueryStringQuery(Query):
    """Query string query.

    See `Query string query`_ for more information.

    .. _Query string query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-query-string-query.html
    """

    query: Annotated[str, StringConstraints(min_length=1)]
    """Query to parse and use for search.

    See `Query string syntax`_ for more information.

    .. _Query string syntax:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-query-string-query.html#query-string-syntax
    """

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        result = {"query": self.query}
        return {"query_string": result}


class RangeQuery(Query):
    """Range query.

    See `Range query`_ for more information.

    .. _Range query:
        https://www.elastic.co/guide/en/elasticsearch/reference/current/
        query-dsl-range-query.html
    """

    field: Annotated[str, StringConstraints(min_length=1)]
    """Name of the field on which to make the query."""

    gt: str | int | float | date | None = None
    """Value the field should be greater than."""

    gte: str | int | float | date | None = None
    """Value the field should be greater or equal than."""

    lt: str | int | float | date | None = None
    """Value the field should be less than."""

    lte: str | int | float | date | None = None
    """Value the field should be less or equal than."""

    def render(self, /) -> dict:
        """Render as a Python dictionary.

        :return: Rendered query.
        :meta private:
        """
        result = {}
        for key in ("gt", "gte", "lt", "lte"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value

        return {"range": {self.field: result}}
