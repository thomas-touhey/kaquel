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
"""KQL lexer, parser and renderer.

See :ref:`format-kql` for more information.
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum, auto
from itertools import chain
import re
from typing import Literal, Union

from pydantic import BaseModel

from kaquel.errors import DecodeError, LeadingWildcardsForbidden
from kaquel.utils import Runk

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


__all__ = ["parse_kql"]


_KQL_TOKEN_PATTERN = re.compile(
    r"(>=?|<=?|:|\(|\)|{|})"
    + r'|"((?:.*?[^\\](?:\\\\)*|))"'  # Quoted literal.
    + '|((?:[^\\\\:()<>"{}\\s]|\\\\.)+)',  # Unquoted literal.
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


_KQL_TOKEN_MAPPING: dict[
    str,
    Literal[
        KQLTokenType.END,
        KQLTokenType.LTE,
        KQLTokenType.GTE,
        KQLTokenType.LT,
        KQLTokenType.GT,
        KQLTokenType.COLON,
        KQLTokenType.LPAR,
        KQLTokenType.RPAR,
        KQLTokenType.LBRACE,
        KQLTokenType.RBRACE,
        KQLTokenType.OR,
        KQLTokenType.AND,
        KQLTokenType.NOT,
    ],
] = {
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


class KQLBasicToken(BaseModel):
    """Basic token, as emitted by the lexer."""

    type: Literal[
        KQLTokenType.END,
        KQLTokenType.LTE,
        KQLTokenType.GTE,
        KQLTokenType.LT,
        KQLTokenType.GT,
        KQLTokenType.COLON,
        KQLTokenType.LPAR,
        KQLTokenType.RPAR,
        KQLTokenType.LBRACE,
        KQLTokenType.RBRACE,
        KQLTokenType.OR,
        KQLTokenType.AND,
        KQLTokenType.NOT,
    ]
    """Type of the token."""

    line: int
    """Line at which the token starts, counting from 1."""

    column: int
    """Column at which the token starts, counting from 1."""

    offset: int
    """Offset at which the token starts, counting from 0."""


class KQLValueToken(BaseModel):
    """Token, as emitted by the lexer."""

    type: Literal[
        KQLTokenType.UNQUOTED_LITERAL,
        KQLTokenType.QUOTED_LITERAL,
    ]
    """Type of the token."""

    value: str
    """Contents of the token, if relevant."""

    line: int
    """Line at which the token starts, counting from 1."""

    column: int
    """Column at which the token starts, counting from 1."""

    offset: int
    """Offset at which the token starts, counting from 0."""


KQLToken = Union[KQLBasicToken, KQLValueToken]


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

    This always ends with an END token.

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
            yield KQLBasicToken(
                type=_KQL_TOKEN_MAPPING[match[1]],
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        elif match[2] is not None:
            yield KQLValueToken(
                type=KQLTokenType.QUOTED_LITERAL,
                value=_unescape_kql_literal(match[2]),
                line=runk.line,
                column=runk.column,
                offset=runk.offset,
            )
        elif match[3] is not None:
            try:
                typ = _KQL_TOKEN_MAPPING[match[3].casefold()]
            except KeyError:
                yield KQLValueToken(
                    type=KQLTokenType.UNQUOTED_LITERAL,
                    value=_unescape_kql_literal(match[3]),
                    line=runk.line,
                    column=runk.column,
                    offset=runk.offset,
                )
            else:
                yield KQLBasicToken(
                    type=typ,
                    line=runk.line,
                    column=runk.column,
                    offset=runk.offset,
                )
        else:  # pragma: no cover
            raise NotImplementedError()

        runk.count(match[0])
        kuery = kuery[match.end() :]

    yield KQLBasicToken(
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
) -> tuple[KQLValueCondition, KQLToken]:
    """Parse a KQL "and" value list.

    :param token_iter: Token iterator.
    :param options: Parsing options.
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
            )
            if token.type != KQLTokenType.RPAR:
                raise UnexpectedKQLToken(token)

            token = next(token_iter)
        elif token.type == KQLTokenType.QUOTED_LITERAL:
            result = KQLValuePhraseMatch(value=token.value)
            token = next(token_iter)
        elif token.type == KQLTokenType.UNQUOTED_LITERAL:
            query_parts = [token.value or ""]

            for token in token_iter:
                if token.type != KQLTokenType.UNQUOTED_LITERAL:
                    break

                query_parts.append(token.value)

            if not options.allow_leading_wildcards and any(
                part.startswith("*") for part in query_parts
            ):
                raise LeadingWildcardsForbidden()

            result = KQLValueMatch(value=" ".join(query_parts))
        else:
            raise UnexpectedKQLToken(token)

        if is_not:
            result = KQLValueNot(condition=result)

        elements.append(result)
        if token.type != KQLTokenType.AND:
            break

    if len(elements) == 1:
        return elements[0], token

    return KQLValueAnd(conditions=elements), token


def _parse_kql_or_value_list(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
) -> tuple[KQLValueCondition, KQLToken]:
    """Parse a KQL "or" value list.

    :param token_iter: Token iterator.
    :param options: Parsing options.
    :return: Query and token obtained after the query.
    """
    elements = []

    while True:
        result, token = _parse_kql_and_value_list(
            token_iter,
            options=options,
        )
        elements.append(result)

        if token.type != KQLTokenType.OR:
            break

    if len(elements) == 1:
        return elements[0], token

    return (KQLValueOr(conditions=elements), token)


def _parse_kql_expression(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
) -> tuple[KQLQuery, KQLToken]:
    """Parse a KQL expression.

    :param token_iter: Lexer token iterator.
    :param options: Parsing options.
    :return: The obtained query, and the token after the obtained query.
    """
    token = next(token_iter)
    result: KQLQuery

    if token.type == KQLTokenType.NOT:
        is_not = True
        token = next(token_iter)
    else:
        is_not = False

    if token.type in (
        KQLTokenType.UNQUOTED_LITERAL,
        KQLTokenType.QUOTED_LITERAL,
    ):
        op_token = next(token_iter)
        if op_token.type == KQLTokenType.GT:
            # Field range expression with "gt" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = KQLGt(field=token.value or "", value=comp_token.value)
            token = next(token_iter)
        elif op_token.type == KQLTokenType.GTE:
            # Field range expression with "gte" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = KQLGte(field=token.value or "", value=comp_token.value)
            token = next(token_iter)
        elif op_token.type == KQLTokenType.LT:
            # Field range expression with "lt" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = KQLLt(field=token.value or "", value=comp_token.value)
            token = next(token_iter)
        elif op_token.type == KQLTokenType.LTE:
            # Field range expression with "lte" range operator.
            comp_token = next(token_iter)
            if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                raise UnexpectedKQLToken(token)

            result = KQLLte(field=token.value or "", value=comp_token.value)
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
                if is_not:
                    raise UnexpectedKQLToken(op_token)

                result, end_token = _parse_kql_or_query(
                    token_iter,
                    options=options,
                )
                if end_token.type != KQLTokenType.RBRACE:
                    raise UnexpectedKQLToken(end_token)

                result = KQLNested(path=token.value or "", query=result)
                token = next(token_iter)
            elif comp_token.type == KQLTokenType.LPAR:
                field = token.value or ""
                condition, token = _parse_kql_or_value_list(
                    token_iter,
                    options=options,
                )
                if token.type != KQLTokenType.RPAR:
                    raise UnexpectedKQLToken(token)

                if field == "*":
                    result = KQLMultiMatch(condition=condition)
                else:
                    result = KQLMatch(field=field, condition=condition)

                token = next(token_iter)
            elif comp_token.type == KQLTokenType.QUOTED_LITERAL:
                if token.value == "*":
                    # Even in a nested context, i.e. ``prefix`` being
                    # non-empty, Kibana interprets this as the field being
                    # a lone wildcard, so we want to do the same.
                    result = KQLMultiMatch(
                        condition=KQLValuePhraseMatch(value=comp_token.value),
                    )
                else:
                    result = KQLMatch(
                        field=token.value or "",
                        condition=KQLValuePhraseMatch(value=comp_token.value),
                    )

                token = next(token_iter)
            elif comp_token.type == KQLTokenType.UNQUOTED_LITERAL:
                query_parts: list[str] = [comp_token.value or ""]

                for comp_token in token_iter:
                    if comp_token.type != KQLTokenType.UNQUOTED_LITERAL:
                        break

                    query_parts.append(comp_token.value)

                if not options.allow_leading_wildcards and any(
                    part.startswith("*") for part in query_parts
                ):
                    raise LeadingWildcardsForbidden()

                if token.value == "*":
                    # Even in a nested context, i.e. ``prefix`` being
                    # non-empty, Kibana interprets this as the field being
                    # a lone wildcard, so we want to do the same.
                    if "*" in query_parts:
                        result = KQLAll()
                    else:
                        result = KQLMultiMatch(
                            condition=KQLValueMatch(
                                value=" ".join(query_parts),
                            ),
                        )
                elif "*" in query_parts:
                    result = KQLExist(field=token.value or "")
                else:
                    result = KQLMatch(
                        field=token.value or "",
                        condition=KQLValueMatch(value=" ".join(query_parts)),
                    )

                token = comp_token
            else:
                raise UnexpectedKQLToken(comp_token)
        elif token.type == KQLTokenType.QUOTED_LITERAL:
            result = KQLMultiMatch(
                condition=KQLValuePhraseMatch(value=token.value),
            )
            token = op_token
        else:
            query_parts = [token.value or ""]

            if op_token.type == KQLTokenType.UNQUOTED_LITERAL:
                query_parts.append(op_token.value)

                for op_token in token_iter:
                    if op_token.type != KQLTokenType.UNQUOTED_LITERAL:
                        break

                    query_parts.append(op_token.value)

            if not options.allow_leading_wildcards and any(
                part.startswith("*") for part in query_parts
            ):
                raise LeadingWildcardsForbidden()

            result = KQLMultiMatch(
                condition=KQLValueMatch(value=" ".join(query_parts)),
            )
            token = op_token
    elif token.type == KQLTokenType.LPAR:
        result, token = _parse_kql_or_query(
            token_iter,
            options=options,
        )
        if token.type != KQLTokenType.RPAR:
            raise UnexpectedKQLToken(token)

        token = next(token_iter)
    else:
        raise UnexpectedKQLToken(token)

    if is_not:
        result = KQLNot(query=result)

    return result, token


def _parse_kql_and_query(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
) -> tuple[KQLQuery, KQLToken]:
    """Parse an "and" query.

    :param token_iter: Lexer token iterator.
    :param options: Parsing options.
    :return: Parsed query, and token after.
    """
    elements = []

    while True:
        result, token = _parse_kql_expression(
            token_iter,
            options=options,
        )
        elements.append(result)

        if token.type != KQLTokenType.AND:
            break

    if len(elements) == 1:
        return elements[0], token

    return KQLAnd(queries=elements), token


def _parse_kql_or_query(
    token_iter: Iterator[KQLToken],
    /,
    *,
    options: _KQLParsingOptions,
) -> tuple[KQLQuery, KQLToken]:
    """Parse an "or" query.

    :param token_iter: Lexer token iterator.
    :param options: Parsing options.
    :return: Parsed query, and token after.
    """
    elements = []

    while True:
        result, token = _parse_kql_and_query(
            token_iter,
            options=options,
        )
        elements.append(result)

        if token.type != KQLTokenType.OR:
            break

    if len(elements) == 1:
        return elements[0], token

    return (KQLOr(queries=elements), token)


def parse_kql(
    kuery: str,
    /,
    *,
    allow_leading_wildcards: bool = True,
) -> KQLQuery:
    """Parse a KQL expression into an ElasticSearch query.

    :param kuery: KQL expression to parse.
    :param allow_leading_wildcards: Whether to allow leading wildcards.
    :return: Parsed query.
    :raises DecodeError: A decoding error has occurred.
    :raises LeadingWildcardsForbidden: Leading wildcards were present while
        disabled.
    """
    options = _KQLParsingOptions(
        allow_leading_wildcards=allow_leading_wildcards,
    )
    token_iter = parse_kql_tokens(kuery)

    # Check for an empty query.
    first_token = next(token_iter)
    if first_token.type == KQLTokenType.END:
        return KQLAll()

    # Requeue the first token.
    token_iter = chain(iter((first_token,)), token_iter)

    result, token = _parse_kql_or_query(token_iter, options=options)
    if token.type != KQLTokenType.END:
        raise UnexpectedKQLToken(token)

    return result
