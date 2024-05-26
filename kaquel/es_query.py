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
"""ElasticSearch query related utilities."""

from __future__ import annotations

import json
from typing import Any

from .errors import Error
from .query import (
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


class InvalidQuery(Error):
    """Invalid ElasticSearch query.

    :param message: Message to display.
    :param raw_query: Raw query that could not be decoded.
    :param context: Context at which the query could not be decoded.
    """

    def __init__(
        self,
        message: str | None = None,
        /,
        *,
        raw_query: dict,
        context: str,
    ) -> None:
        super().__init__(
            f"Invalid ElasticSearch query at {context}"
            + (
                ": " + message[0].lower() + message[1:] + "."
                if message
                else ""
            )
            + f"\n    {raw_query}",
        )
        self.raw_query = raw_query


def _parse_es_query(query: Any, /, *, context: str = ".") -> Query:
    """Parse a JSON parsed ElasticSearch query.

    :param query: Query as a dictionary.
    :param context: Context.
    :return: Parsed query.
    """
    try:
        if not isinstance(query, dict) or len(query) != 1:
            raise ValueError("Could not retrieve query type")

        ((typ, content),) = query.items()
        if not isinstance(content, dict):
            raise ValueError("Query contents was not an array")

        if typ == "bool":
            for key in ("must", "filter", "should", "must_not"):
                if key not in content:
                    continue

                if isinstance(content[key], list):
                    content[key] = [
                        _parse_es_query(
                            element,
                            context=context + f"bool[{key}{i}].",
                        )
                        for i, element in enumerate(content[key])
                    ]
                else:
                    content[key] = [
                        _parse_es_query(
                            content[key],
                            context=context + f"bool[{key}0].",
                        ),
                    ]

            return BooleanQuery(**content)
        elif typ == "exists":
            return ExistsQuery(**content)
        elif typ == "match_all":
            return MatchAllQuery(**content)
        elif typ == "match_phrase":
            ((field, query),) = content.items()
            if isinstance(query, dict):
                return MatchPhraseQuery(field=field, **query)
            else:
                return MatchPhraseQuery(field=field, query=query)
        elif typ == "match":
            ((field, query),) = content.items()
            if isinstance(query, dict):
                return MatchQuery(field=field, **query)
            else:
                return MatchQuery(field=field, query=query)
        elif typ == "multi_match":
            return MultiMatchQuery(**content)
        elif typ == "nested":
            content["query"] = _parse_es_query(
                content.get("query"),
                context=context + "nested[query].",
            )
            return NestedQuery(**content)
        elif typ == "query_string":
            return QueryStringQuery(**content)
        elif typ == "range":
            ((field, field_contents),) = content.items()
            return RangeQuery(field=field, **field_contents)
        else:
            raise ValueError(f"Unimplemented query type {typ}")
    except ValueError as exc:
        if isinstance(exc, InvalidQuery):
            raise

        raise InvalidQuery(str(exc), raw_query=query, context=context)


def parse_es_query(query: Any, /) -> Query:
    """Parse an ElasticSearch query.

    :param query: JSON-encoded query, or query decoded as a dictionary.
    :return: Parsed query.
    """
    if isinstance(query, str):
        parsed_query = json.loads(query)
        return _parse_es_query(parsed_query)

    return _parse_es_query(query)
