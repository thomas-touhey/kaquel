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
"""Tests for the ElasticSearch query related utilities."""

from __future__ import annotations

from typing import Any

import pytest

from kaquel.es_query import InvalidQuery, parse_es_query
from kaquel.query import (
    BooleanQuery,
    ExistsQuery,
    MatchAllQuery,
    MatchPhraseQuery,
    MatchQuery,
    MultiMatchQuery,
    NestedQuery,
    Query,
    QueryStringQuery,
    RangeQuery,
)


@pytest.mark.parametrize(
    "raw_query,query",
    (
        (
            {"bool": {"filter": {"match": {"message": "hello world"}}}},
            BooleanQuery(
                filter=[MatchQuery(field="message", query="hello world")],
            ),
        ),
        (
            {
                "bool": {
                    "filter": [
                        {"match": {"message": {"query": "hello world"}}},
                    ],
                },
            },
            BooleanQuery(
                filter=[MatchQuery(field="message", query="hello world")],
            ),
        ),
        (
            {"exists": {"field": "hello"}},
            ExistsQuery(field="hello"),
        ),
        (
            {"match_all": {}},
            MatchAllQuery(),
        ),
        (
            {"match_phrase": {"hello": "world"}},
            MatchPhraseQuery(field="hello", query="world"),
        ),
        (
            {"match_phrase": {"hello": {"query": "world"}}},
            MatchPhraseQuery(field="hello", query="world"),
        ),
        (
            {"multi_match": {"query": "hello world", "lenient": True}},
            MultiMatchQuery(query="hello world", lenient=True),
        ),
        (
            {
                "nested": {
                    "path": "user.names",
                    "query": {"match": {"first": "Thomas"}},
                },
            },
            NestedQuery(
                path="user.names",
                query=MatchQuery(field="first", query="Thomas"),
            ),
        ),
        (
            {"query_string": {"query": "a: b"}},
            QueryStringQuery(query="a: b"),
        ),
        (
            {"range": {"hello": {"lt": "200", "gt": "200"}}},
            RangeQuery(field="hello", lt="200", gt="200"),
        ),
        # JSON-encoded.
        (
            '{"match":{"hello":"world"}}',
            MatchQuery(field="hello", query="world"),
        ),
    ),
)
def test_es_query_parsing(raw_query: str | dict, query: Query) -> None:
    """Test that ElasticSearch query parsing works correctly."""
    assert parse_es_query(raw_query) == query


@pytest.mark.parametrize(
    "raw_query",
    (
        5,  # not a dictionary
        {"first_key": "wow", "second_key": "wow"},  # multiple types
        {"first_key": "wow"},  # content is not a dictionary
        {"bool": {"must": {"first_key": None}}},  # inner exception
        {"unknown_query": {}},
        {"match_all": {"hello": "world"}},  # match_all with contents.
    ),
)
def test_invalid_es_query_parsing(raw_query: Any) -> None:
    """Test invalid ElasticSearch query parsing."""
    with pytest.raises(InvalidQuery):
        parse_es_query(raw_query)
