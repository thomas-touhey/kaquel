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
"""Tests for ``kaquel.kql.to_query``."""

from __future__ import annotations

import pytest

from kaquel.kql.lang import (
    And as KQLAnd,
    Match as KQLMatch,
    MultiMatch as KQLMultiMatch,
    Not as KQLNot,
    Or as KQLOr,
    Query as KQLQuery,
    ValueAnd as KQLValueAnd,
    ValueMatch as KQLValueMatch,
    ValueNot as KQLValueNot,
    ValueOr as KQLValueOr,
)
from kaquel.kql.to_query import from_kql
from kaquel.query import BooleanQuery, MatchQuery, MultiMatchQuery, Query


@pytest.mark.parametrize(
    "kql_query,es_query",
    (
        (
            KQLAnd(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="b")),
                ],
            ),
            MatchQuery(field="a", query="b"),
        ),
        (
            KQLOr(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="b")),
                ],
            ),
            MatchQuery(field="a", query="b"),
        ),
        (
            KQLMatch(
                field="a",
                condition=KQLValueAnd(conditions=[KQLValueMatch(value="b")]),
            ),
            MatchQuery(field="a", query="b"),
        ),
        (
            KQLMultiMatch(
                condition=KQLValueAnd(conditions=[KQLValueMatch(value="b")]),
            ),
            MultiMatchQuery(query="b", lenient=True),
        ),
        (
            KQLMatch(
                field="a",
                condition=KQLValueOr(conditions=[KQLValueMatch(value="b")]),
            ),
            MatchQuery(field="a", query="b"),
        ),
        (
            KQLMultiMatch(
                condition=KQLValueOr(conditions=[KQLValueMatch(value="b")]),
            ),
            MultiMatchQuery(query="b", lenient=True),
        ),
        (
            KQLMatch(
                field="a",
                condition=KQLValueNot(condition=KQLValueMatch(value="b")),
            ),
            BooleanQuery(must_not=[MatchQuery(field="a", query="b")]),
        ),
        (
            KQLNot(
                query=KQLMatch(
                    field="a",
                    condition=KQLValueMatch(value="b"),
                ),
            ),
            BooleanQuery(must_not=[MatchQuery(field="a", query="b")]),
        ),
        (
            KQLMultiMatch(
                condition=KQLValueNot(condition=KQLValueMatch(value="b")),
            ),
            BooleanQuery(must_not=[MultiMatchQuery(query="b", lenient=True)]),
        ),
        (
            KQLNot(
                query=KQLMultiMatch(
                    condition=KQLValueMatch(value="b"),
                ),
            ),
            BooleanQuery(must_not=[MultiMatchQuery(query="b", lenient=True)]),
        ),
        (
            KQLMultiMatch(
                condition=KQLValueAnd(
                    conditions=[
                        KQLValueMatch(value="a"),
                        KQLValueMatch(value="b"),
                    ],
                ),
            ),
            BooleanQuery(
                filter=[
                    MultiMatchQuery(query="a", lenient=True),
                    MultiMatchQuery(query="b", lenient=True),
                ],
            ),
        ),
    ),
)
def test_to_query(kql_query: KQLQuery, es_query: Query) -> None:
    """Test :py:func:`to_query`."""
    assert from_kql(kql_query) == es_query
