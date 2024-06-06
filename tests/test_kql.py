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
"""Tests for the KQL related utilities."""

from __future__ import annotations

from datetime import date

import pytest

from kaquel.errors import DecodeError, LeadingWildcardsForbidden, RenderError
from kaquel.kql import (
    KQLToken as Token,
    KQLTokenType as TokenType,
    KQLValueToken as ValueToken,
    UnexpectedKQLToken,
    parse_kql,
    parse_kql_tokens,
    render_as_kql,
)
from kaquel.query import (
    BooleanQuery,
    ExistsQuery,
    MatchAllQuery,
    MatchPhraseQuery,
    MatchQuery,
    MultiMatchQuery,
    MultiMatchQueryType,
    NestedScoreMode,
    NestedQuery,
    Query,
    RangeQuery,
)


@pytest.mark.parametrize(
    "raw,tokens",
    (
        # Examples taken from the Kibana Query Language documentation:
        # https://www.elastic.co/guide/en/kibana/current/kuery-query.html
        (
            "http.request.method: *",
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "*"),
            ],
        ),
        (
            "http.request.method: GET",
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "GET"),
            ],
        ),
        ("Hello", [(TokenType.UNQUOTED_LITERAL, "Hello")]),
        (
            "http.request.body.content: null pointer",
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.body.content"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "null"),
                (TokenType.UNQUOTED_LITERAL, "pointer"),
            ],
        ),
        (
            'http.request.body.content: "null pointer"',
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.body.content"),
                (TokenType.COLON, None),
                (TokenType.QUOTED_LITERAL, "null pointer"),
            ],
        ),
        (
            'http.request.referrer: "https://example.com"',
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.referrer"),
                (TokenType.COLON, None),
                (TokenType.QUOTED_LITERAL, "https://example.com"),
            ],
        ),
        (
            r"http.request.referrer: https\://example.com",
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.referrer"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "https://example.com"),
            ],
        ),
        (
            "http.response.bytes < 10000",
            [
                (TokenType.UNQUOTED_LITERAL, "http.response.bytes"),
                (TokenType.LT, None),
                (TokenType.UNQUOTED_LITERAL, "10000"),
            ],
        ),
        (
            "http.response.bytes > 10000 and http.response.bytes <= 20000",
            [
                (TokenType.UNQUOTED_LITERAL, "http.response.bytes"),
                (TokenType.GT, None),
                (TokenType.UNQUOTED_LITERAL, "10000"),
                (TokenType.AND, None),
                (TokenType.UNQUOTED_LITERAL, "http.response.bytes"),
                (TokenType.LTE, None),
                (TokenType.UNQUOTED_LITERAL, "20000"),
            ],
        ),
        (
            "@timestamp < now-2w",
            [
                (TokenType.UNQUOTED_LITERAL, "@timestamp"),
                (TokenType.LT, None),
                (TokenType.UNQUOTED_LITERAL, "now-2w"),
            ],
        ),
        (
            "http.response.status_code: 4*",
            [
                (TokenType.UNQUOTED_LITERAL, "http.response.status_code"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "4*"),
            ],
        ),
        (
            "NOT http.request.method: GET",
            [
                (TokenType.NOT, None),
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "GET"),
            ],
        ),
        (
            "http.request.method: GET OR http.response.status_code: 400",
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "GET"),
                (TokenType.OR, None),
                (TokenType.UNQUOTED_LITERAL, "http.response.status_code"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "400"),
            ],
        ),
        (
            "http.request.method: GET AND http.response.status_code: 400",
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "GET"),
                (TokenType.AND, None),
                (TokenType.UNQUOTED_LITERAL, "http.response.status_code"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "400"),
            ],
        ),
        (
            "(http.request.method: GET AND http.response.status_code: 200) "
            + "OR\n(http.request.method: POST AND "
            + "http.response.status_code: 400)",
            [
                (TokenType.LPAR, None),
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "GET"),
                (TokenType.AND, None),
                (TokenType.UNQUOTED_LITERAL, "http.response.status_code"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "200"),
                (TokenType.RPAR, None),
                (TokenType.OR, None),
                (TokenType.LPAR, None),
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "POST"),
                (TokenType.AND, None),
                (TokenType.UNQUOTED_LITERAL, "http.response.status_code"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "400"),
                (TokenType.RPAR, None),
            ],
        ),
        (
            "http.request.method: (GET OR POST OR DELETE)",
            [
                (TokenType.UNQUOTED_LITERAL, "http.request.method"),
                (TokenType.COLON, None),
                (TokenType.LPAR, None),
                (TokenType.UNQUOTED_LITERAL, "GET"),
                (TokenType.OR, None),
                (TokenType.UNQUOTED_LITERAL, "POST"),
                (TokenType.OR, None),
                (TokenType.UNQUOTED_LITERAL, "DELETE"),
                (TokenType.RPAR, None),
            ],
        ),
        (
            "datastream.*: logs",
            [
                (TokenType.UNQUOTED_LITERAL, "datastream.*"),
                (TokenType.COLON, None),
                (TokenType.UNQUOTED_LITERAL, "logs"),
            ],
        ),
        (
            'user:{ first: "Alice" and last: "White" }',
            [
                (TokenType.UNQUOTED_LITERAL, "user"),
                (TokenType.COLON, None),
                (TokenType.LBRACE, None),
                (TokenType.UNQUOTED_LITERAL, "first"),
                (TokenType.COLON, None),
                (TokenType.QUOTED_LITERAL, "Alice"),
                (TokenType.AND, None),
                (TokenType.UNQUOTED_LITERAL, "last"),
                (TokenType.COLON, None),
                (TokenType.QUOTED_LITERAL, "White"),
                (TokenType.RBRACE, None),
            ],
        ),
        (
            'user.names:{ first: "Alice" and last: "White" }',
            [
                (TokenType.UNQUOTED_LITERAL, "user.names"),
                (TokenType.COLON, None),
                (TokenType.LBRACE, None),
                (TokenType.UNQUOTED_LITERAL, "first"),
                (TokenType.COLON, None),
                (TokenType.QUOTED_LITERAL, "Alice"),
                (TokenType.AND, None),
                (TokenType.UNQUOTED_LITERAL, "last"),
                (TokenType.COLON, None),
                (TokenType.QUOTED_LITERAL, "White"),
                (TokenType.RBRACE, None),
            ],
        ),
    ),
)
def test_parse_tokens(raw: str, tokens: list[Token]) -> None:
    """Check that we obtain the correct tokens for the given requests."""
    assert [
        (token.type, token.value if isinstance(token, ValueToken) else None)
        for token in parse_kql_tokens(raw)
    ] == tokens + [(TokenType.END, None)]


def test_parse_invalid_token() -> None:
    """Check that a decode error can be raised."""
    with pytest.raises(DecodeError):
        for _ in parse_kql_tokens('"' + "the end is never" * 8):
            print(_)


@pytest.mark.parametrize(
    "raw,query",
    (
        # Examples taken from the Kibana Query Language documentation:
        # https://www.elastic.co/guide/en/kibana/current/kuery-query.html
        (
            "http.request.method: *",
            ExistsQuery(field="http.request.method"),
        ),
        (
            "http.request.method: GET",
            MatchQuery(field="http.request.method", query="GET"),
        ),
        (
            "Hello",
            MultiMatchQuery(query="Hello", lenient=True),
        ),
        (
            "http.request.body.content: null pointer",
            MatchQuery(
                field="http.request.body.content",
                query="null pointer",
            ),
        ),
        (
            'http.request.body.content: "null pointer"',
            MatchPhraseQuery(
                field="http.request.body.content",
                query="null pointer",
            ),
        ),
        (
            'http.request.referrer: "https://example.com"',
            MatchPhraseQuery(
                field="http.request.referrer",
                query="https://example.com",
            ),
        ),
        (
            r"http.request.referrer: https\://example.com",
            MatchQuery(
                field="http.request.referrer",
                query="https://example.com",
            ),
        ),
        (
            "http.response.bytes < 10000",
            RangeQuery(field="http.response.bytes", lt="10000"),
        ),
        (
            "http.response.bytes > 10000 and http.response.bytes <= 20000",
            BooleanQuery(
                filter=[
                    RangeQuery(field="http.response.bytes", gt="10000"),
                    RangeQuery(field="http.response.bytes", lte="20000"),
                ],
            ),
        ),
        (
            "@timestamp < now-2w",
            RangeQuery(field="@timestamp", lt="now-2w"),
        ),
        (
            "http.response.status_code: 4*",
            MatchQuery(field="http.response.status_code", query="4*"),
        ),
        (
            "NOT http.request.method: GET",
            BooleanQuery(
                must_not=MatchQuery(field="http.request.method", query="GET"),
            ),
        ),
        (
            "http.request.method: GET OR http.response.status_code: 400",
            BooleanQuery(
                should=[
                    MatchQuery(field="http.request.method", query="GET"),
                    MatchQuery(field="http.response.status_code", query="400"),
                ],
                minimum_should_match=1,
            ),
        ),
        (
            "http.request.method: GET AND http.response.status_code: 400",
            BooleanQuery(
                filter=[
                    MatchQuery(field="http.request.method", query="GET"),
                    MatchQuery(field="http.response.status_code", query="400"),
                ],
            ),
        ),
        (
            "(http.request.method: GET AND http.response.status_code: 200) "
            + "OR\n (http.request.method: POST AND "
            + "http.response.status_code: 400)",
            BooleanQuery(
                should=[
                    BooleanQuery(
                        filter=[
                            MatchQuery(
                                field="http.request.method",
                                query="GET",
                            ),
                            MatchQuery(
                                field="http.response.status_code",
                                query="200",
                            ),
                        ],
                    ),
                    BooleanQuery(
                        filter=[
                            MatchQuery(
                                field="http.request.method",
                                query="POST",
                            ),
                            MatchQuery(
                                field="http.response.status_code",
                                query="400",
                            ),
                        ],
                    ),
                ],
                minimum_should_match=1,
            ),
        ),
        (
            "http.request.method: (GET OR POST OR DELETE)",
            BooleanQuery(
                should=[
                    MatchQuery(field="http.request.method", query="GET"),
                    MatchQuery(field="http.request.method", query="POST"),
                    MatchQuery(field="http.request.method", query="DELETE"),
                ],
                minimum_should_match=1,
            ),
        ),
        (
            "datastream.*: logs",
            MatchQuery(field="datastream.*", query="logs"),
        ),
        (
            'user:{ first: "Alice" and last: "White" }',
            NestedQuery(
                path="user",
                query=BooleanQuery(
                    filter=[
                        MatchPhraseQuery(field="user.first", query="Alice"),
                        MatchPhraseQuery(field="user.last", query="White"),
                    ],
                ),
                score_mode=NestedScoreMode.NONE,
            ),
        ),
        (
            'user.names:{ first: "Alice" and last: "White" }',
            NestedQuery(
                path="user.names",
                query=BooleanQuery(
                    filter=[
                        MatchPhraseQuery(
                            field="user.names.first",
                            query="Alice",
                        ),
                        MatchPhraseQuery(
                            field="user.names.last",
                            query="White",
                        ),
                    ],
                ),
                score_mode=NestedScoreMode.NONE,
            ),
        ),
        # Other tests for various code paths.
        (
            "  \t  ",
            MatchAllQuery(),
        ),
        (
            "*: *",
            MatchAllQuery(),
        ),
        (
            "*: hello",
            MultiMatchQuery(query="hello", lenient=True),
        ),
        (
            '*: "hello"',
            MultiMatchQuery(
                type=MultiMatchQueryType.PHRASE,
                query="hello",
                lenient=True,
            ),
        ),
        (
            '*: (hello or "world")',
            BooleanQuery(
                should=[
                    MultiMatchQuery(query="hello", lenient=True),
                    MultiMatchQuery(
                        type=MultiMatchQueryType.PHRASE,
                        query="world",
                        lenient=True,
                    ),
                ],
            ),
        ),
        (
            "hello: (not world)",
            BooleanQuery(
                must_not=MatchQuery(field="hello", query="world"),
            ),
        ),
        (
            "hello: (not (world or universe))",
            BooleanQuery(
                must_not=BooleanQuery(
                    should=[
                        MatchQuery(field="hello", query="world"),
                        MatchQuery(field="hello", query="universe"),
                    ],
                ),
            ),
        ),
        (
            "hello: (the world is there and i am happy)",
            BooleanQuery(
                filter=[
                    MatchQuery(field="hello", query="the world is there"),
                    MatchQuery(field="hello", query="i am happy"),
                ],
            ),
        ),
        (
            'hello: ("the world")',
            MatchPhraseQuery(field="hello", query="the world"),
        ),
        (
            "hello world lol",
            MultiMatchQuery(query="hello world lol", lenient=True),
        ),
        (
            "field >= 5",
            RangeQuery(field="field", gte="5"),
        ),
        (
            "field < 5",
            RangeQuery(field="field", lt="5"),
        ),
        (
            "field <= 5",
            RangeQuery(field="field", lte="5"),
        ),
        (
            '"hello world"',
            MultiMatchQuery(
                type=MultiMatchQueryType.PHRASE,
                query="hello world",
                lenient=True,
            ),
        ),
        (
            '"hello": "world"',
            MatchPhraseQuery(field="hello", query="world"),
        ),
        (
            '"hello"> 5',
            RangeQuery(field="hello", gt="5"),
        ),
        (
            '"hello": (world OR universe)',
            BooleanQuery(
                should=[
                    MatchQuery(field="hello", query="world"),
                    MatchQuery(field="hello", query="universe"),
                ],
            ),
        ),
        (
            '"hello": { "world": "yes" }',
            NestedQuery(
                path="hello",
                query=MatchPhraseQuery(field="hello.world", query="yes"),
                score_mode=NestedScoreMode.NONE,
            ),
        ),
    ),
)
def test_parser(raw: str, query: Query) -> None:
    """Test that the parsed result of a query is correct."""
    assert parse_kql(raw) == query

    # Also ensure that we are actually able to re-render the query here.
    render_as_kql(query)


@pytest.mark.parametrize(
    "raw,query",
    (
        (
            "a: b AND c",
            BooleanQuery(
                must=[
                    MatchQuery(field="a", query="b"),
                    MultiMatchQuery(query="c", lenient=True),
                ],
            ),
        ),
        (
            "a: (b AND c)",
            BooleanQuery(
                must=[
                    MatchQuery(field="a", query="b"),
                    MatchQuery(field="a", query="c"),
                ],
            ),
        ),
    ),
)
def test_parser_with_must_clause(raw: str, query: Query) -> None:
    """Test that the must switch works correctly for the AND function."""
    assert parse_kql(raw, filters_in_must_clause=True) == query


@pytest.mark.parametrize(
    "raw",
    (
        ":",
        "hello: (not)",
        "hello: (not (abc",
        'popcorn > "all"',
        'popcorn >= "all"',
        'popcorn < "all"',
        'popcorn <= "all"',
        "not nest: { invalid }",
        "missing_rbrace: { hello",
        "(missing rpar",
        "missing: (rpar OR cass",
        "unexpected_end:",
        'hello: "world" unexpected-suffix',
    ),
)
def test_parser_with_invalid_query(raw: str) -> None:
    """Test that a parsing error is correctly reported."""
    with pytest.raises(UnexpectedKQLToken):
        parse_kql(raw)


@pytest.mark.parametrize(
    "raw",
    (
        "*basic",
        "basic *more",
        "basic more and *more",
        "*",
        "myfield: hello *basic",
        "myfield: *",
        "myfield: (*basic)",
        "myfield: (*)",
        "myfield: (hoo *basic)",
        "myfield: (hoo *)",
    ),
)
def test_parser_with_forbidden_leading_wildcards(raw: str) -> None:
    """Test that the leading wildcard is correctly forbidden."""
    with pytest.raises(LeadingWildcardsForbidden):
        parse_kql(raw, allow_leading_wildcards=False)


@pytest.mark.parametrize(
    "query,expected",
    (
        (
            MatchAllQuery(),
            "*",
        ),
        (
            NestedQuery(
                path="user",
                query=MatchPhraseQuery(field="user.name", query="John"),
                score_mode=NestedScoreMode.NONE,
            ),
            'user: { name: "John" }',
        ),
        (
            BooleanQuery(
                filter=[
                    MatchQuery(field="a", query="a"),
                    BooleanQuery(
                        should=[
                            MatchQuery(field="b", query="b"),
                            MatchQuery(field="c", query="c"),
                        ],
                    ),
                ],
            ),
            "a: a and (b: b or c: c)",
        ),
        (
            BooleanQuery(
                should=[
                    MatchQuery(field="a", query="a"),
                    BooleanQuery(
                        filter=[
                            MatchQuery(field="b", query="b"),
                            MatchQuery(field="c", query="c"),
                        ],
                    ),
                ],
            ),
            "a: a or b: b and c: c",
        ),
        (
            BooleanQuery(
                must_not=[
                    BooleanQuery(
                        filter=[
                            MatchQuery(field="a", query="a"),
                            MatchQuery(field="b", query="b"),
                        ],
                    ),
                ],
            ),
            "not (a: a and b: b)",
        ),
        (
            BooleanQuery(must_not=[MatchQuery(field="a", query="a")]),
            "not a: a",
        ),
        (
            BooleanQuery(
                filter=[MatchQuery(field="a", query="a")],
                must_not=[MatchQuery(field="b", query="b")],
            ),
            "a: a and not b: b",
        ),
        (
            BooleanQuery(
                filter=[MatchQuery(field="a", query="a")],
                should=[MatchQuery(field="b", query="b")],
            ),
            "a: a and b: b",
        ),
        (
            BooleanQuery(
                filter=[
                    MatchQuery(field="a", query="a"),
                    MatchQuery(field="b", query="b"),
                ],
                should=[
                    MatchQuery(field="c", query="c"),
                    MatchQuery(field="d", query="d"),
                ],
                must_not=[
                    MatchQuery(field="e", query="e"),
                    MatchQuery(field="f", query="f"),
                ],
            ),
            "a: a and b: b and (c: c or d: d) and not (e: e or f: f)",
        ),
        (
            BooleanQuery(
                should=[
                    MatchQuery(field="a", query="a"),
                    MatchQuery(field="b", query="b"),
                ],
                minimum_should_match=2,
            ),
            "a: a and b: b",
        ),
        (ExistsQuery(field="a"), "a: *"),
        (
            MatchQuery(field="a", query=date(2012, 12, 21)),
            "a: 2012-12-21",
        ),
        (
            MultiMatchQuery(query="a b", lenient=True),
            "a b",
        ),
        (
            MultiMatchQuery(
                type=MultiMatchQueryType.PHRASE,
                query="a b",
                lenient=True,
            ),
            '"a b"',
        ),
        (
            RangeQuery(field="year", gt=1999, gte=2000, lt=2021, lte=2020),
            "year > 1999 and year >= 2000 and year < 2021 and year <= 2020",
        ),
        (
            BooleanQuery(must_not=[RangeQuery(field="year", gt=1999)]),
            "not year > 1999",
        ),
        (
            BooleanQuery(
                must_not=[RangeQuery(field="year", gt=1999, lte=2020)],
            ),
            "not (year > 1999 and year <= 2020)",
        ),
    ),
)
def test_render(query: Query, expected: str) -> None:
    """Test that KQL query rendering works correctly."""
    assert render_as_kql(query) == expected


@pytest.mark.parametrize(
    "query,pattern",
    (
        (BooleanQuery(), "empty boolean query"),
        (
            BooleanQuery(
                should=[
                    MatchQuery(field="a", query="a"),
                    MatchQuery(field="b", query="b"),
                    MatchQuery(field="c", query="c"),
                ],
                minimum_should_match=2,
            ),
            "minimum_should_match",
        ),
        (
            MultiMatchQuery(query="a b"),
            "lenient",
        ),
        (
            MultiMatchQuery(
                query="John",
                fields=["firstName", "lastName"],
                lenient=True,
            ),
            "fields",
        ),
        (
            MultiMatchQuery(
                type=MultiMatchQueryType.CROSS_FIELDS,
                query="a b",
                lenient=True,
            ),
            "with type",
        ),
        (
            NestedQuery(
                path="user",
                query=MatchQuery(field="user.name", query="John"),
            ),
            "score mode",
        ),
        (
            NestedQuery(
                path="user",
                query=ExistsQuery(field="name"),
                score_mode=NestedScoreMode.NONE,
            ),
            "prefix",
        ),
        (
            NestedQuery(
                path="user",
                query=MatchQuery(field="name", query="John"),
                score_mode=NestedScoreMode.NONE,
            ),
            "prefix",
        ),
        (
            NestedQuery(
                path="user",
                query=MatchPhraseQuery(field="name", query="John"),
                score_mode=NestedScoreMode.NONE,
            ),
            "prefix",
        ),
        (
            NestedQuery(
                path="user",
                query=NestedQuery(
                    path="names",
                    query=MatchQuery(field="user.names.first", query="John"),
                    score_mode=NestedScoreMode.NONE,
                ),
                score_mode=NestedScoreMode.NONE,
            ),
            "prefix",
        ),
        (
            NestedQuery(
                path="now",
                query=RangeQuery(
                    field="year",
                    lt=2020,
                ),
                score_mode=NestedScoreMode.NONE,
            ),
            "prefix",
        ),
    ),
)
def test_render_error(query: Query, pattern: str) -> None:
    """Test that KQL render errors are correctly raised."""
    with pytest.raises(RenderError, match=pattern):
        render_as_kql(query)


def test_render_with_must_clause() -> None:
    """Test that we can switch the AND clause if need be."""
    assert (
        render_as_kql(
            BooleanQuery(
                should=[BooleanQuery(must=[MatchQuery(field="a", query="b")])],
            ),
            filters_in_must_clause=True,
        )
        == "a: b"
    )

    with pytest.raises(RenderError, match=r"filters_in_must_clause"):
        render_as_kql(
            BooleanQuery(
                should=[
                    BooleanQuery(filter=[MatchQuery(field="a", query="b")]),
                ],
            ),
            filters_in_must_clause=True,
        )

    with pytest.raises(RenderError, match=r"filters_in_must_clause"):
        render_as_kql(
            BooleanQuery(
                should=[BooleanQuery(must=[MatchQuery(field="a", query="b")])],
            ),
            filters_in_must_clause=False,
        )
