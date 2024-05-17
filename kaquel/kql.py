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
"""Kuery lexer."""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum, auto
import re

from pydantic import BaseModel

from kaquel.errors import DecodeError, LeadingWildcardsForbidden
from kaquel.query import (
    BooleanQuery,
    ExistsQuery,
    MatchPhraseQuery,
    MatchQuery,
    MultiMatchQuery,
    MultiMatchQueryType,
    NestedQuery,
    NestedScoreMode,
    Query,
    RangeQuery,
)
from kaquel.utils import Runk


_KQL_TOKEN_PATTERN = re.compile(
    r"(>=?|<=?|:|\(|\)|{|})"
    + r'|"((?:.*?[^\\](?:\\\\)*|))"'  # Quoted literal.
    + '|((?:[^\\\\:()<>"\\s]|\\\\.)+)',  # Unquoted literal.
    re.MULTILINE,
)
"""Pattern for reading the next token."""

_KQL_ESCAPE_PATTERN = re.compile(r"\\(.)")
"""Pattern for finding escape sequences."""


class KQLTokenType(Enum):
    """Token type."""

    END = auto()
    UNQUOTED_LITERAL = auto()
    QUOTED_LITERAL = auto()

    LTE = auto()
    GTE = auto()
    LT = auto()
    GT = auto()
    COLON = auto()
    LPAR = auto()
    RPAR = auto()
    LBRACE = auto()
    RBRACE = auto()

    OR = auto()
    AND = auto()
    NOT = auto()


_KQL_TOKEN_MAPPING: dict[str, KQLTokenType] = {
    "<=": KQLTokenType.LTE,
    ">=": KQLTokenType.GTE,
    "<": KQLTokenType.LT,
    ">": KQLTokenType.GT,
    ":": KQLTokenType.COLON,
    "(": KQLTokenType.LPAR,
    ")": KQLTokenType.RPAR,
    "{": KQLTokenType.LBRACE,
    "}": KQLTokenType.RBRACE,
    "or": KQLTokenType.OR,
    "and": KQLTokenType.AND,
    "not": KQLTokenType.NOT,
}
"""Direct token mapping."""


class KQLToken(BaseModel):
    """Token, as emitted by the lexer."""

    type: KQLTokenType
    """Type of the token."""

    value: str | None = None
    """Contents of the token, if relevant."""

    line: int
    """Line at which the token starts, counting from 1."""

    column: int
    """Column at which the token starts, counting from 1."""

    offset: int
    """Offset at which the token starts, counting from 0."""


# ---
# Lexer.
# ---


def _unescape_kql_literal(escaped_literal: str, /) -> str:
    """Unescape a KQL literal.

    :param escaped_literal: Literal with escape sequences.
    :return: Unescaped literal.
    """
    return _KQL_ESCAPE_PATTERN.sub(r"\1", escaped_literal)


def parse_kql_tokens(kuery: str, /) -> Iterator[KQLToken]:
    """Parse a string into a series of KQL tokens.

    This always ends with

    :param kuery: KQL expression from which to get the expression.
    :return: Token iterator.
    """
    runk = Runk()
    while True:
        # First, remove the leading whitespace, and check if there is still
        # contents in the string.
        stripped_kuery = kuery.lstrip()
        if not stripped_kuery:
            break

        runk.count(kuery[: len(kuery) - len(stripped_kuery)])
        kuery = stripped_kuery

        match = _KQL_TOKEN_PATTERN.match(kuery)
        if match is None:
            if len(kuery) > 30:
                kuery = kuery[:27] + "..."

            raise DecodeError(
                f"Could not parsing query starting from: {kuery}",
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )

        if match[1] is not None:
            typ, value = _KQL_TOKEN_MAPPING[match[1]], None
        elif match[2] is not None:
            typ, value = (
                KQLTokenType.QUOTED_LITERAL,
                _unescape_kql_literal(match[2]),
            )
        elif match[3] is not None:
            try:
                typ, value = _KQL_TOKEN_MAPPING[match[3].casefold()], None
            except KeyError:
                typ, value = (
                    KQLTokenType.UNQUOTED_LITERAL,
                    _unescape_kql_literal(match[3]),
                )
        else:  # pragma: no cover
            raise NotImplementedError()

        yield KQLToken(
            type=typ,
            value=value,
            line=runk.line,
            column=runk.column,
            offset=runk.offset,
        )

        runk.count(match[0])
        kuery = kuery[match.end() :]

    yield KQLToken(
        type=KQLTokenType.END,
        line=runk.line,
        column=runk.column,
        offset=runk.offset,
    )


# ---
# Parser.
# ---


class _KQLParsingOptions(BaseModel):
    """Options for the KQL parser."""

    allow_leading_wildcards: bool
    """Whether to allow leading wildcards or not."""


class UnexpectedKQLToken(DecodeError):
    """An unexpected KQL token was obtained."""

    token: KQLToken
    """Token type."""

    def __init__(self, token: KQLToken, /):
        super().__init__(
            f"Unexpected token {token.type.name} at line {token.line}, "
            + f"column {token.column}",
            line=token.line,
            column=token.column,
            offset=token.offset,
        )
        self.token = token


def _parse_kql_and_value_list(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
    field: str,
) -> tuple[Query, KQLToken]:
    """Parse a KQL "and value list.

    :param token_iter: Token iterator.
    :param options: Parsing options.
    :param field: Field name.
    :return: Query and token obtained after the query.
    """
    elements = []

    while True:
        token = next(token_iter)
        if token.type == KQLTokenType.NOT:
            is_not = True
            token = next(token_iter)
        else:
            is_not = False

        if token.type == KQLTokenType.LPAR:
            result, token = _parse_kql_or_value_list(
                token_iter,
                options=options,
                field=field,
            )
            if token.type != KQLTokenType.RPAR:
                raise UnexpectedKQLToken(token)

            token = next(token_iter)
        elif token.type == KQLTokenType.QUOTED_LITERAL:
            result = MatchPhraseQuery(
                field=field,
                query=token.value,
            )
            token = next(token_iter)
        elif token.type == KQLTokenType.UNQUOTED_LITERAL:
            query_parts = [token.value or ""]

            for token in token_iter:
                if token.type != KQLTokenType.UNQUOTED_LITERAL:
                    break
                if token.value is None:  # pragma: no cover
                    raise ValueError("Unquoted literal without a value!")

                query_parts.append(token.value)

            if not options.allow_leading_wildcards and any(
                part.startswith("*") for part in query_parts
            ):
                raise LeadingWildcardsForbidden()

            result = MatchQuery(field=field, query=" ".join(query_parts))
        else:
            raise UnexpectedKQLToken(token)

        if is_not:
            result = BooleanQuery(must_not=result)

        elements.append(result)
        if token.type != KQLTokenType.AND:
            break

    if len(elements) == 1:
        return elements[0], token

    return BooleanQuery(filter=elements), token


def _parse_kql_or_value_list(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
    field: str,
) -> tuple[Query, KQLToken]:
    """Parse a KQL "or" value list.

    :param token_iter: Token iterator.
    :param options: Parsing options.
    :param field: Field name.
    :return: Query and token obtained after the query.
    """
    elements = []

    while True:
        result, token = _parse_kql_and_value_list(
            token_iter,
            options=options,
            field=field,
        )
        elements.append(result)

        if token.type != KQLTokenType.OR:
            break

    if len(elements) == 1:
        return elements[0], token

    return (
        BooleanQuery(
            should=elements,
            minimum_should_match=1,
        ),
        token,
    )


def _parse_kql_expression(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
    prefix: str = "",
) -> tuple[Query, KQLToken]:
    """Parse a KQL expression.

    :param token_iter: Lexer token iterator.
    :param options: Parsing options.
    :param prefix: Field prefix.
    :return: The obtained query, and the token after the obtained query.
    """
    token = next(token_iter)
    result: Query

    if token.type == KQLTokenType.NOT:
        is_not = True
        token = next(token_iter)
    else:
        is_not = False

    if token.type == KQLTokenType.UNQUOTED_LITERAL:
        op_token = next(token_iter)
        if op_token.type == KQLTokenType.GT:
            # Field range expression with "gt" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = RangeQuery(
                field=prefix + (token.value or ""),
                gt=comp_token.value,
            )
            token = next(token_iter)
        elif op_token.type == KQLTokenType.GTE:
            # Field range expression with "gte" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = RangeQuery(
                field=prefix + (token.value or ""),
                gte=comp_token.value,
            )
            token = next(token_iter)
        elif op_token.type == KQLTokenType.LT:
            # Field range expression with "lt" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = RangeQuery(
                field=prefix + (token.value or ""),
                lt=comp_token.value,
            )
            token = next(token_iter)
        elif op_token.type == KQLTokenType.LTE:
            # Field range expression with "lte" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = RangeQuery(
                field=prefix + (token.value or ""),
                lte=comp_token.value,
            )
            token = next(token_iter)
        elif op_token.type == KQLTokenType.COLON:
            # Nested: "name: { ... }"
            # Value expression with unquoted literals: "name: a b c ..."
            # Value expression with quoted literal: 'name: "..."'
            # Value expression with list of values: "name: (a OR b OR ...)"
            #
            # List of values can also have "AND list of values" in them,
            # e.g. "(a OR b AND c OR d)".
            comp_token = next(token_iter)
            if comp_token.type == KQLTokenType.LBRACE:
                path = token.value or ""
                if is_not:
                    raise UnexpectedKQLToken(op_token)

                result, end_token = _parse_kql_or_query(
                    token_iter,
                    options=options,
                    prefix=path + ".",
                )
                if end_token.type != KQLTokenType.RBRACE:
                    raise UnexpectedKQLToken(end_token)

                result = NestedQuery(
                    path=path,
                    query=result,
                    score_mode=NestedScoreMode.NONE,
                )

                token = next(token_iter)
            elif comp_token.type == KQLTokenType.LPAR:
                result, token = _parse_kql_or_value_list(
                    token_iter,
                    options=options,
                    field=prefix + (token.value or ""),
                )
                if token.type != KQLTokenType.RPAR:
                    raise UnexpectedKQLToken(token)

                token = next(token_iter)
            elif comp_token.type == KQLTokenType.QUOTED_LITERAL:
                result = MatchPhraseQuery(
                    field=prefix + (token.value or ""),
                    query=comp_token.value,
                )
                token = next(token_iter)
            elif comp_token.type == KQLTokenType.UNQUOTED_LITERAL:
                query_parts: list[str] = [comp_token.value or ""]

                for comp_token in token_iter:
                    if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                        break
                    if comp_token.value is None:  # pragma: no cover
                        raise ValueError("Unquoted literal without a value!")

                    query_parts.append(comp_token.value)

                if not options.allow_leading_wildcards and any(
                    part.startswith("*") for part in query_parts
                ):
                    raise LeadingWildcardsForbidden()

                if "*" in query_parts:
                    result = ExistsQuery(field=prefix + (token.value or ""))
                else:
                    result = MatchQuery(
                        field=prefix + (token.value or ""),
                        query=" ".join(query_parts),
                    )

                token = comp_token
            else:
                raise UnexpectedKQLToken(comp_token)
        else:
            query_parts = [token.value or ""]

            if op_token.type == KQLTokenType.UNQUOTED_LITERAL:
                if op_token.value is None:  # pragma: no cover
                    raise ValueError("Unquoted literal without a value!")

                query_parts.append(op_token.value)

                for op_token in token_iter:
                    if op_token.type != KQLTokenType.UNQUOTED_LITERAL:
                        break
                    if op_token.value is None:  # pragma: no cover
                        raise ValueError("Unquoted literal without a value!")

                    query_parts.append(op_token.value)

            if not options.allow_leading_wildcards and any(
                part.startswith("*") for part in query_parts
            ):
                raise LeadingWildcardsForbidden()

            result = MultiMatchQuery(query=" ".join(query_parts), lenient=True)
            token = op_token
    elif token.type == KQLTokenType.QUOTED_LITERAL:
        result = MultiMatchQuery(
            type=MultiMatchQueryType.PHRASE,
            query=token.value,
            lenient=True,
        )
        token = next(token_iter)
    elif token.type == KQLTokenType.LPAR:
        result, token = _parse_kql_or_query(
            token_iter,
            options=options,
            prefix=prefix,
        )
        if token.type != KQLTokenType.RPAR:
            raise UnexpectedKQLToken(token)

        token = next(token_iter)
    else:
        raise UnexpectedKQLToken(token)

    if is_not:
        result = BooleanQuery(must_not=result)

    return result, token


def _parse_kql_and_query(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
    prefix: str = "",
) -> tuple[Query, KQLToken]:
    """Parse an "and" query.

    :param token_iter: Lexer token iterator.
    :param options: Parsing options.
    :param prefix: Field prefix.
    :return: Parsed query, and token after.
    """
    elements = []

    while True:
        result, token = _parse_kql_expression(
            token_iter,
            options=options,
            prefix=prefix,
        )
        elements.append(result)

        if token.type != KQLTokenType.AND:
            break

    if len(elements) == 1:
        return elements[0], token

    return BooleanQuery(filter=elements), token


def _parse_kql_or_query(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
    prefix: str = "",
) -> tuple[Query, KQLToken]:
    """Parse an "or" query.

    :param token_iter: Lexer token iterator.
    :param options: Parsing options.
    :param prefix: Field prefix.
    :return: Parsed query, and token after.
    """
    elements = []

    while True:
        result, token = _parse_kql_and_query(
            token_iter,
            options=options,
            prefix=prefix,
        )
        elements.append(result)

        if token.type != KQLTokenType.OR:
            break

    if len(elements) == 1:
        return elements[0], token

    return (
        BooleanQuery(
            should=elements,
            minimum_should_match=1,
        ),
        token,
    )


def parse_kql(
    kuery: str,
    /,
    *,
    allow_leading_wildcards: bool = True,
) -> Query:
    """Parse a KQL expression into an ElasticSearch query.

    :param kuery: KQL expression to parse.
    :param allow_leading_wildcards: Whether to allow leading wildcards.
    :raises DecodeError: A decoding error has occurred.
    :raises LeadingWildcardsForbidden: Leading wildcards were present while
        disabled.
    """
    options = _KQLParsingOptions(
        allow_leading_wildcards=allow_leading_wildcards,
    )
    token_iter = parse_kql_tokens(kuery)
    result, token = _parse_kql_or_query(token_iter, options=options)
    if token.type != KQLTokenType.END:
        raise UnexpectedKQLToken(token)

    return result
