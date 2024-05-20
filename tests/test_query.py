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
"""Tests for the query representations."""

from __future__ import annotations

import pytest

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
    "query,expected",
    (
        (BooleanQuery(), None),
        (BooleanQuery(minimum_should_match=0), None),
        (
            BooleanQuery(
                should=[MatchQuery(field="a", query="b")],
                minimum_should_match=1,
            ),
            1,
        ),
    ),
)
def normalize_boolean_query_minimum_should_match(
    query: BooleanQuery,
    expected: int | None,
) -> None:
    """Check minimum_should_match normalization."""
    assert query.minimum_should_match == expected


@pytest.mark.parametrize(
    "query,expected",
    (
        (BooleanQuery(), {"bool": {}}),
        (
            BooleanQuery(must=[MatchQuery(field="a", query="b")]),
            {"bool": {"must": {"match": {"a": "b"}}}},
        ),
        (
            BooleanQuery(
                should=[
                    MatchQuery(field="a", query="b"),
                    MatchQuery(field="c", query="d"),
                    MatchQuery(field="e", query="f"),
                ],
                minimum_should_match=2,
            ),
            {
                "bool": {
                    "should": [
                        {"match": {"a": "b"}},
                        {"match": {"c": "d"}},
                        {"match": {"e": "f"}},
                    ],
                    "minimum_should_match": 2,
                },
            },
        ),
        (
            ExistsQuery(field="a"),
            {"exists": {"field": "a"}},
        ),
        (
            MatchAllQuery(),
            {"match_all": {}},
        ),
        (
            MatchPhraseQuery(field="a", query="b"),
            {"match_phrase": {"a": "b"}},
        ),
        (
            MultiMatchQuery(query="a", fields=["b", "c"], lenient=True),
            {
                "multi_match": {
                    "type": "best_fields",
                    "query": "a",
                    "fields": ["b", "c"],
                    "lenient": True,
                },
            },
        ),
        (
            NestedQuery(
                path="user",
                query=MatchQuery(field="user.name", query="torvalds"),
            ),
            {
                "nested": {
                    "path": "user",
                    "query": {"match": {"user.name": "torvalds"}},
                    "score_mode": "avg",
                },
            },
        ),
        (
            QueryStringQuery(query="a:b"),
            {"query_string": {"query": "a:b"}},
        ),
        (
            RangeQuery(field="date", lt="now-2d"),
            {"range": {"date": {"lt": "now-2d"}}},
        ),
    ),
)
def test_query_rendering(query: Query, expected: dict) -> None:
    """Test query rendering as a dictionary."""
    assert query.render() == expected
