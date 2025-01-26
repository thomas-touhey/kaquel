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
"""Tests for ``kaquel.kql.optimizer``."""

from __future__ import annotations

import pytest

from kaquel.kql.lang import (
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
    KQLValueAll,
    KQLValueAnd,
    KQLValueMatch,
    KQLValueNot,
    KQLValueOr,
)
from kaquel.kql.optimizer import optimize_kql


@pytest.mark.parametrize(
    "original,optimized",
    (
        (
            KQLNot(
                query=KQLNot(
                    query=KQLMatch(
                        field="a",
                        condition=KQLValueMatch(value="b"),
                    ),
                ),
            ),
            KQLMatch(field="a", condition=KQLValueMatch(value="b")),
        ),
        (
            KQLNot(
                query=KQLMatch(field="a", condition=KQLValueMatch(value="b")),
            ),
            KQLNot(
                query=KQLMatch(
                    field="a",
                    condition=KQLValueMatch(value="b"),
                ),
            ),
        ),
        (
            KQLNot(
                query=KQLMatch(
                    field="a",
                    condition=KQLValueNot(condition=KQLValueMatch(value="b")),
                ),
            ),
            KQLMatch(field="a", condition=KQLValueMatch(value="b")),
        ),
        (
            KQLNot(query=KQLMultiMatch(condition=KQLValueMatch(value="b"))),
            KQLNot(query=KQLMultiMatch(condition=KQLValueMatch(value="b"))),
        ),
        (
            KQLNot(
                query=KQLMultiMatch(
                    condition=KQLValueNot(condition=KQLValueMatch(value="b")),
                ),
            ),
            KQLMultiMatch(condition=KQLValueMatch(value="b")),
        ),
        (  # 5
            KQLNot(
                query=KQLAnd(
                    queries=[
                        KQLMatch(
                            field="a",
                            condition=KQLValueMatch(value="a"),
                        ),
                        KQLMatch(
                            field="b",
                            condition=KQLValueMatch(value="b"),
                        ),
                    ],
                ),
            ),
            KQLNot(
                query=KQLAnd(
                    queries=[
                        KQLMatch(
                            field="a",
                            condition=KQLValueMatch(value="a"),
                        ),
                        KQLMatch(
                            field="b",
                            condition=KQLValueMatch(value="b"),
                        ),
                    ],
                ),
            ),
        ),
        (
            KQLNot(
                query=KQLOr(
                    queries=[
                        KQLMatch(
                            field="a",
                            condition=KQLValueMatch(value="a"),
                        ),
                        KQLMatch(
                            field="b",
                            condition=KQLValueMatch(value="b"),
                        ),
                    ],
                ),
            ),
            KQLNot(
                query=KQLOr(
                    queries=[
                        KQLMatch(
                            field="a",
                            condition=KQLValueMatch(value="a"),
                        ),
                        KQLMatch(
                            field="b",
                            condition=KQLValueMatch(value="b"),
                        ),
                    ],
                ),
            ),
        ),
        (
            KQLAnd(
                queries=[
                    KQLNot(query=KQLGt(field="a", value=0)),
                    KQLNot(query=KQLGte(field="b", value=1)),
                    KQLNot(query=KQLLt(field="c", value=2)),
                    KQLNot(query=KQLLte(field="d", value=3)),
                ],
            ),
            KQLAnd(
                queries=[
                    KQLLte(field="a", value=0),
                    KQLLt(field="b", value=1),
                    KQLGte(field="c", value=2),
                    KQLGt(field="d", value=3),
                ],
            ),
        ),
        (
            KQLNot(query=KQLAll()),
            KQLNot(query=KQLAll()),
        ),
        # Query AND optimizations.
        (
            KQLAnd(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                ],
            ),
            KQLMatch(field="a", condition=KQLValueMatch(value="a")),
        ),
        (
            KQLAnd(
                queries=[
                    KQLAnd(
                        queries=[
                            KQLMatch(
                                field="a",
                                condition=KQLValueMatch(value="a"),
                            ),
                            KQLMatch(
                                field="b",
                                condition=KQLValueMatch(value="b"),
                            ),
                        ],
                    ),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
            KQLAnd(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLMatch(field="b", condition=KQLValueMatch(value="b")),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
        ),
        (
            KQLAnd(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLMatch(
                        field="a",
                        condition=KQLValueAnd(
                            conditions=[
                                KQLValueMatch(value="b"),
                                KQLValueMatch(value="c"),
                            ],
                        ),
                    ),
                ],
            ),
            KQLMatch(
                field="a",
                condition=KQLValueAnd(
                    conditions=[
                        KQLValueMatch(value="a"),
                        KQLValueMatch(value="b"),
                        KQLValueMatch(value="c"),
                    ],
                ),
            ),
        ),
        (
            KQLAnd(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLGt(field="b", value=5),
                    KQLMultiMatch(condition=KQLValueMatch(value="c")),
                    KQLMatch(field="a", condition=KQLValueMatch(value="b")),
                    KQLMultiMatch(condition=KQLValueMatch(value="d")),
                ],
            ),
            KQLAnd(
                queries=[
                    KQLMatch(
                        field="a",
                        condition=KQLValueAnd(
                            conditions=[
                                KQLValueMatch(value="a"),
                                KQLValueMatch(value="b"),
                            ],
                        ),
                    ),
                    KQLMultiMatch(
                        condition=KQLValueAnd(
                            conditions=[
                                KQLValueMatch(value="c"),
                                KQLValueMatch(value="d"),
                            ],
                        ),
                    ),
                    KQLGt(field="b", value=5),
                ],
            ),
        ),
        (
            KQLAnd(
                queries=[
                    KQLExist(field="a"),
                    KQLExist(field="b"),
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
            KQLAnd(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLExist(field="b"),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
        ),
        (
            KQLAnd(
                queries=[
                    KQLAll(),
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                ],
            ),
            KQLMatch(field="a", condition=KQLValueMatch(value="a")),
        ),
        (KQLAnd(queries=[KQLAll(), KQLAll()]), KQLAll()),
        (
            KQLAnd(queries=[KQLMatch(field="a", condition=KQLValueAll())]),
            KQLExist(field="a"),
        ),
        (
            KQLAnd(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="b")),
                    KQLMatch(field="a", condition=KQLValueAll()),
                ],
            ),
            KQLMatch(field="a", condition=KQLValueMatch(value="b")),
        ),
        # Query OR optimizations.
        (
            KQLOr(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                ],
            ),
            KQLMatch(field="a", condition=KQLValueMatch(value="a")),
        ),
        (
            KQLOr(
                queries=[
                    KQLOr(
                        queries=[
                            KQLMatch(
                                field="a",
                                condition=KQLValueMatch(value="a"),
                            ),
                            KQLMatch(
                                field="b",
                                condition=KQLValueMatch(value="b"),
                            ),
                        ],
                    ),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
            KQLOr(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLMatch(field="b", condition=KQLValueMatch(value="b")),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
        ),
        (
            KQLOr(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLMatch(
                        field="a",
                        condition=KQLValueOr(
                            conditions=[
                                KQLValueMatch(value="b"),
                                KQLValueMatch(value="c"),
                            ],
                        ),
                    ),
                ],
            ),
            KQLMatch(
                field="a",
                condition=KQLValueOr(
                    conditions=[
                        KQLValueMatch(value="a"),
                        KQLValueMatch(value="b"),
                        KQLValueMatch(value="c"),
                    ],
                ),
            ),
        ),
        (
            KQLOr(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLGt(field="b", value=5),
                    KQLMultiMatch(condition=KQLValueMatch(value="c")),
                    KQLMatch(field="a", condition=KQLValueMatch(value="b")),
                    KQLMultiMatch(condition=KQLValueMatch(value="d")),
                ],
            ),
            KQLOr(
                queries=[
                    KQLMatch(
                        field="a",
                        condition=KQLValueOr(
                            conditions=[
                                KQLValueMatch(value="a"),
                                KQLValueMatch(value="b"),
                            ],
                        ),
                    ),
                    KQLMultiMatch(
                        condition=KQLValueOr(
                            conditions=[
                                KQLValueMatch(value="c"),
                                KQLValueMatch(value="d"),
                            ],
                        ),
                    ),
                    KQLGt(field="b", value=5),
                ],
            ),
        ),
        (
            KQLOr(
                queries=[
                    KQLExist(field="a"),
                    KQLExist(field="b"),
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
            KQLOr(
                queries=[
                    KQLExist(field="a"),
                    KQLExist(field="b"),
                    KQLMatch(field="c", condition=KQLValueMatch(value="c")),
                ],
            ),
        ),
        (
            KQLOr(
                queries=[
                    KQLAll(),
                    KQLMatch(field="a", condition=KQLValueMatch(value="a")),
                ],
            ),
            KQLAll(),
        ),
        (
            KQLOr(
                queries=[
                    KQLMultiMatch(condition=KQLValueAll()),
                    KQLAll(),
                ],
            ),
            KQLAll(),
        ),
        (
            KQLOr(
                queries=[
                    KQLMatch(field="a", condition=KQLValueMatch(value="b")),
                    KQLMatch(field="a", condition=KQLValueAll()),
                ],
            ),
            KQLExist(field="a"),
        ),
        # Other tests.
        (
            KQLNot(
                query=KQLNested(
                    path="person",
                    query=KQLMultiMatch(
                        condition=KQLValueMatch(value="Jennifer"),
                    ),
                ),
            ),
            KQLNested(
                path="person",
                query=KQLNot(
                    query=KQLMultiMatch(
                        condition=KQLValueMatch(value="Jennifer"),
                    ),
                ),
            ),
        ),
        (
            KQLNot(
                query=KQLOr(
                    queries=[
                        KQLMatch(
                            field="a",
                            condition=KQLValueMatch(value="b"),
                        ),
                        KQLMatch(
                            field="b",
                            condition=KQLValueNot(
                                condition=KQLValueMatch(value="b"),
                            ),
                        ),
                    ],
                ),
            ),
            KQLAnd(
                queries=[
                    KQLNot(
                        query=KQLMatch(
                            field="a",
                            condition=KQLValueMatch(value="b"),
                        ),
                    ),
                    KQLMatch(
                        field="b",
                        condition=KQLValueMatch(value="b"),
                    ),
                ],
            ),
        ),
        (
            KQLMatch(
                field="name",
                condition=KQLValueAnd(
                    conditions=[
                        KQLValueNot(condition=KQLValueMatch(value="John")),
                        KQLValueNot(condition=KQLValueMatch(value="Adam")),
                    ],
                ),
            ),
            KQLNot(
                query=KQLMatch(
                    field="name",
                    condition=KQLValueOr(
                        conditions=[
                            KQLValueMatch(value="John"),
                            KQLValueMatch(value="Adam"),
                        ],
                    ),
                ),
            ),
        ),
        (
            KQLMatch(
                field="name",
                condition=KQLValueOr(
                    conditions=[
                        KQLValueNot(condition=KQLValueMatch(value="John")),
                        KQLValueNot(condition=KQLValueMatch(value="Adam")),
                    ],
                ),
            ),
            KQLNot(
                query=KQLMatch(
                    field="name",
                    condition=KQLValueAnd(
                        conditions=[
                            KQLValueMatch(value="John"),
                            KQLValueMatch(value="Adam"),
                        ],
                    ),
                ),
            ),
        ),
    ),
)
def test_optimize(original: KQLQuery, optimized: KQLQuery) -> None:
    """Check that optimizing requests work."""
    assert optimize_kql(original) == optimized
