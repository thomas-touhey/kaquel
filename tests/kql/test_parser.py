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
"""Tests for the KQL parser."""

from __future__ import annotations

import pytest

from kaquel.errors import DecodeError, LeadingWildcardsForbidden
from kaquel.kql.parser import (
    KQLToken as Token,
    KQLTokenType as TokenType,
    KQLValueToken as ValueToken,
    UnexpectedKQLToken,
    parse_kql,
    parse_kql_tokens,
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
            "a:{b}",
            [
                (TokenType.UNQUOTED_LITERAL, "a"),
                (TokenType.COLON, None),
                (TokenType.LBRACE, None),
                (TokenType.UNQUOTED_LITERAL, "b"),
                (TokenType.RBRACE, None),
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
