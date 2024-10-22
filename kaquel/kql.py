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
from datetime import date
from enum import Enum, auto
from itertools import chain
import re
from typing import Literal, Union

from pydantic import BaseModel

from kaquel.errors import DecodeError, LeadingWildcardsForbidden, RenderError
from kaquel.query import (
    BooleanQuery,
    ExistsQuery,
    MatchAllQuery,
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


__all__ = ["parse_kql", "render_as_kql"]


_KQL_TOKEN_PATTERN = re.compile(
    r"(>=?|<=?|:|\(|\)|{|})"
    + r'|"((?:.*?[^\\](?:\\\\)*|))"'  # Quoted literal.
    + '|((?:[^\\\\:()<>"{}\\s]|\\\\.)+)',  # Unquoted literal.
    re.MULTILINE,
)
"""Pattern for reading the next token."""

_KQL_ESCAPE_PATTERN = re.compile(r"\\(.)")
"""Pattern for finding escape sequences."""

_KQL_TO_ESCAPE_PATTERN = re.compile(r'([\\\\():<>"])')
"""Pattern for finding sequences to escape."""


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

    filters_in_must_clause: bool
    """Whether filters should be in the 'filter' or 'must' clause."""


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
            if field == "*":
                result = MultiMatchQuery(
                    type=MultiMatchQueryType.PHRASE,
                    query=token.value,
                    lenient=True,
                )
            else:
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

                query_parts.append(token.value)

            if not options.allow_leading_wildcards and any(
                part.startswith("*") for part in query_parts
            ):
                raise LeadingWildcardsForbidden()

            if field == "*":
                result = MultiMatchQuery(
                    query=" ".join(query_parts),
                    lenient=True,
                )
            else:
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

    if options.filters_in_must_clause:
        return BooleanQuery(must=elements), token

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
                if token.value == "*":
                    # Even in a nested context, i.e. ``prefix`` being
                    # non-empty, Kibana interprets this as the field being
                    # a lone wildcard, so we want to do the same.
                    result = MultiMatchQuery(
                        type=MultiMatchQueryType.PHRASE,
                        query=comp_token.value,
                        lenient=True,
                    )
                else:
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
                        result = MatchAllQuery()
                    else:
                        result = MultiMatchQuery(
                            query=" ".join(query_parts),
                            lenient=True,
                        )
                elif "*" in query_parts:
                    result = ExistsQuery(field=prefix + (token.value or ""))
                else:
                    result = MatchQuery(
                        field=prefix + (token.value or ""),
                        query=" ".join(query_parts),
                    )

                token = comp_token
            else:
                raise UnexpectedKQLToken(comp_token)
        elif token.type == KQLTokenType.QUOTED_LITERAL:
            result = MultiMatchQuery(
                type=MultiMatchQueryType.PHRASE,
                query=token.value,
                lenient=True,
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

            result = MultiMatchQuery(query=" ".join(query_parts), lenient=True)
            token = op_token
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

    if options.filters_in_must_clause:
        return BooleanQuery(must=elements), token

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
    filters_in_must_clause: bool = False,
) -> Query:
    """Parse a KQL expression into an ElasticSearch query.

    :param kuery: KQL expression to parse.
    :param allow_leading_wildcards: Whether to allow leading wildcards.
    :param filters_in_must_clause: Whether filters should be in the
        'filter' or 'must' clause.
    :return: Parsed query.
    :raises DecodeError: A decoding error has occurred.
    :raises LeadingWildcardsForbidden: Leading wildcards were present while
        disabled.
    """
    options = _KQLParsingOptions(
        allow_leading_wildcards=allow_leading_wildcards,
        filters_in_must_clause=filters_in_must_clause,
    )
    token_iter = parse_kql_tokens(kuery)

    # Check for an empty query.
    first_token = next(token_iter)
    if first_token.type == KQLTokenType.END:
        return MatchAllQuery()

    # Requeue the first token.
    token_iter = chain(iter((first_token,)), token_iter)

    result, token = _parse_kql_or_query(token_iter, options=options)
    if token.type != KQLTokenType.END:
        raise UnexpectedKQLToken(token)

    return result


# ---
# Renderer.
# ---


def _render_kql_literal(literal: str | int | float | date, /) -> str:
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


def _render_as_kql_recursive(
    query: Query,
    /,
    *,
    filters_in_must_clause: bool,
    prefix: str = "",
    in_and: bool = False,
    in_not: bool = False,
) -> str:
    """Render the KQL query recursively.

    :param query: Query to render recursively.
    :param filters_in_must_clause: Filters should be retrieved from the 'must'
        clause rather than 'filter' clause for boolean queries.
    :param prefix: Prefix to remove from the field.
    :param in_and: Whether we are in an AND context, i.e. we need to add
        parenthesis if we have an OR.
    :param in_not: Whether we are in a NOT context.
    :return: Rendered query as KQL.
    """
    if isinstance(query, BooleanQuery):
        # TODO: Check if we can produce the short syntax field: (a OR b AND c)

        if filters_in_must_clause:
            if query.filter:
                raise RenderError(
                    "Cannot render a boolean query with filter clause and "
                    + "filters_in_must_clause=True",
                )
        elif query.must:
            raise RenderError(
                "Cannot render a boolean query with must clause and "
                + "filters_in_must_clause=False",
            )

        # If 'minimum_should_match' is defined, and does not match either 1
        # (OR clause) or the number of clauses in 'should' (AND clause), it is
        # not renderable as KQL.
        if query.should and query.minimum_should_match == len(query.should):
            query = BooleanQuery(
                filter=query.filter + query.should,
                must_not=query.must_not,
            )
        elif query.minimum_should_match not in (None, 1):
            raise RenderError(
                "Cannot render a boolean query with complex "
                + "minimum_should_match value",
            )

        if not query.must and not query.filter and not query.must_not:
            # We are facing an OR clause.
            if not query.should:
                raise RenderError("Cannot render an empty boolean query.")

            multiple_clauses_expected = len(query.should) > 1
            result = " or ".join(
                _render_as_kql_recursive(
                    sub_query,
                    filters_in_must_clause=filters_in_must_clause,
                    prefix=prefix,
                    in_and=in_and and not multiple_clauses_expected,
                    in_not=in_not and not multiple_clauses_expected,
                )
                for sub_query in query.should
            )

            if multiple_clauses_expected and (in_and or in_not):
                return f"({result})"

            return result

        # We are facing an AND clause.
        multiple_clauses_expected = (
            len(query.must)
            + len(query.filter)
            + (len(query.must_not) > 0)
            + (len(query.should) > 0)
            > 1
        )

        and_clauses = []
        for sub_query in chain(query.must, query.filter):
            and_clauses.append(
                _render_as_kql_recursive(
                    sub_query,
                    filters_in_must_clause=filters_in_must_clause,
                    prefix=prefix,
                    in_and=in_and or multiple_clauses_expected,
                    in_not=in_not and not multiple_clauses_expected,
                ),
            )

        if len(query.should) == 1:
            and_clauses.append(
                _render_as_kql_recursive(
                    query.should[0],
                    filters_in_must_clause=filters_in_must_clause,
                    prefix=prefix,
                    in_and=in_and or multiple_clauses_expected,
                    in_not=in_not and not multiple_clauses_expected,
                ),
            )
        elif query.should:
            and_clauses.append(
                "("
                + " or ".join(
                    _render_as_kql_recursive(
                        sub_query,
                        filters_in_must_clause=filters_in_must_clause,
                        prefix=prefix,
                    )
                    for sub_query in query.should
                )
                + ")",
            )

        if len(query.must_not) == 1:
            and_clauses.append(
                "not "
                + _render_as_kql_recursive(
                    query.must_not[0],
                    filters_in_must_clause=filters_in_must_clause,
                    in_not=True,
                ),
            )
        elif len(query.must_not) > 1:
            and_clauses.append(
                "not ("
                + " or ".join(
                    _render_as_kql_recursive(
                        sub_query,
                        filters_in_must_clause=filters_in_must_clause,
                    )
                    for sub_query in query.must_not
                )
                + ")",
            )

        result = " and ".join(and_clauses)
        if in_not and multiple_clauses_expected:
            return f"({result})"

        return result
    elif isinstance(query, ExistsQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        return query.field[len(prefix) :] + ": *"
    elif isinstance(query, MatchAllQuery):
        return "*"
    elif isinstance(query, MatchPhraseQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        return (
            query.field[len(prefix) :]
            + ': "'
            + _render_kql_literal(query.query)
            + '"'
        )
    elif isinstance(query, MatchQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        return (
            query.field[len(prefix) :]
            + ": "
            + _render_kql_literal(query.query)
        )
    elif isinstance(query, MultiMatchQuery):
        if not query.lenient:
            raise RenderError("Expected a lenient multi-match query")
        if query.fields:
            raise RenderError(
                "Cannot render a multi-match with specific fields",
            )

        if query.type == MultiMatchQueryType.BEST_FIELDS:
            return _render_kql_literal(query.query)
        elif query.type == MultiMatchQueryType.PHRASE:
            return '"' + _render_kql_literal(query.query) + '"'
        else:
            raise RenderError(
                f"Cannot render a multi-match query with type {query.type}",
            )
    elif isinstance(query, NestedQuery):
        if query.score_mode != NestedScoreMode.NONE:
            raise RenderError(
                "Cannot render a nested query with score mode "
                + f"{query.score_mode}",
            )
        if not query.path.startswith(prefix):
            raise RenderError(
                f"Nested query path does not start with prefix {prefix}",
            )

        return (
            query.path[len(prefix) :]
            + ": { "
            + _render_as_kql_recursive(
                query.query,
                filters_in_must_clause=filters_in_must_clause,
                prefix=query.path + ".",
            )
            + " }"
        )
    elif isinstance(query, RangeQuery):
        if not query.field.startswith(prefix):
            raise RenderError(
                f"Match query field does not start with prefix {prefix}",
            )

        and_clauses = []
        field = query.field[len(prefix) :]

        if query.gt is not None:
            and_clauses.append(f"{field} > {_render_kql_literal(query.gt)}")
        if query.gte is not None:
            and_clauses.append(f"{field} >= {_render_kql_literal(query.gte)}")
        if query.lt is not None:
            and_clauses.append(f"{field} < {_render_kql_literal(query.lt)}")
        if query.lte is not None:
            and_clauses.append(f"{field} <= {_render_kql_literal(query.lte)}")

        if len(and_clauses) > 1 and in_not:
            return "(" + " and ".join(and_clauses) + ")"

        return " and ".join(and_clauses)

    raise RenderError(  # pragma: no cover
        f"Cannot render a {query.__class__.__name__}",
    )


def render_as_kql(
    query: Query,
    /,
    *,
    filters_in_must_clause: bool = False,
) -> str:
    """Render the query as a KQL query.

    :param query: Query to render as KQL.
    :param filters_in_must_clause: Whether filters should be retrieved from
        the 'must' clause rather than 'filter' clause for boolean queries.
    :return: Rendered query as KQL.
    :raises RenderError: An error has occurred while rendering the query;
        usually, the query makes use of a feature that cannot be translated
        into KQL.
    """
    return _render_as_kql_recursive(
        query,
        filters_in_must_clause=filters_in_must_clause,
    )
