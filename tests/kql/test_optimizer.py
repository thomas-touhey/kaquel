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
    All,
    And,
    Exist,
    Gt,
    Gte,
    Lt,
    Lte,
    Match,
    MultiMatch,
    Nested,
    Not,
    Or,
    Query,
    ValueAll,
    ValueAnd,
    ValueMatch,
    ValueNot,
    ValueOr,
)
from kaquel.kql.optimizer import optimize_kql


@pytest.mark.parametrize(
    "original,optimized",
    (
        (
            Not(
                query=Not(
                    query=Match(field="a", condition=ValueMatch(value="b")),
                ),
            ),
            Match(field="a", condition=ValueMatch(value="b")),
        ),
        (
            Not(query=Match(field="a", condition=ValueMatch(value="b"))),
            Not(
                query=Match(
                    field="a",
                    condition=ValueMatch(value="b"),
                ),
            ),
        ),
        (
            Not(
                query=Match(
                    field="a",
                    condition=ValueNot(condition=ValueMatch(value="b")),
                ),
            ),
            Match(field="a", condition=ValueMatch(value="b")),
        ),
        (
            Not(query=MultiMatch(condition=ValueMatch(value="b"))),
            Not(query=MultiMatch(condition=ValueMatch(value="b"))),
        ),
        (
            Not(
                query=MultiMatch(
                    condition=ValueNot(condition=ValueMatch(value="b")),
                ),
            ),
            MultiMatch(condition=ValueMatch(value="b")),
        ),
        (  # 5
            Not(
                query=And(
                    queries=[
                        Match(field="a", condition=ValueMatch(value="a")),
                        Match(field="b", condition=ValueMatch(value="b")),
                    ],
                ),
            ),
            Not(
                query=And(
                    queries=[
                        Match(field="a", condition=ValueMatch(value="a")),
                        Match(field="b", condition=ValueMatch(value="b")),
                    ],
                ),
            ),
        ),
        (
            Not(
                query=Or(
                    queries=[
                        Match(field="a", condition=ValueMatch(value="a")),
                        Match(field="b", condition=ValueMatch(value="b")),
                    ],
                ),
            ),
            Not(
                query=Or(
                    queries=[
                        Match(field="a", condition=ValueMatch(value="a")),
                        Match(field="b", condition=ValueMatch(value="b")),
                    ],
                ),
            ),
        ),
        (
            And(
                queries=[
                    Not(query=Gt(field="a", value=0)),
                    Not(query=Gte(field="b", value=1)),
                    Not(query=Lt(field="c", value=2)),
                    Not(query=Lte(field="d", value=3)),
                ],
            ),
            And(
                queries=[
                    Lte(field="a", value=0),
                    Lt(field="b", value=1),
                    Gte(field="c", value=2),
                    Gt(field="d", value=3),
                ],
            ),
        ),
        (
            Not(query=All()),
            Not(query=All()),
        ),
        # Query AND optimizations.
        (
            And(queries=[Match(field="a", condition=ValueMatch(value="a"))]),
            Match(field="a", condition=ValueMatch(value="a")),
        ),
        (
            And(
                queries=[
                    And(
                        queries=[
                            Match(field="a", condition=ValueMatch(value="a")),
                            Match(field="b", condition=ValueMatch(value="b")),
                        ],
                    ),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
            And(
                queries=[
                    Match(field="a", condition=ValueMatch(value="a")),
                    Match(field="b", condition=ValueMatch(value="b")),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
        ),
        (
            And(
                queries=[
                    Match(field="a", condition=ValueMatch(value="a")),
                    Match(
                        field="a",
                        condition=ValueAnd(
                            conditions=[
                                ValueMatch(value="b"),
                                ValueMatch(value="c"),
                            ],
                        ),
                    ),
                ],
            ),
            Match(
                field="a",
                condition=ValueAnd(
                    conditions=[
                        ValueMatch(value="a"),
                        ValueMatch(value="b"),
                        ValueMatch(value="c"),
                    ],
                ),
            ),
        ),
        (
            And(
                queries=[
                    Match(field="a", condition=ValueMatch(value="a")),
                    Gt(field="b", value=5),
                    MultiMatch(condition=ValueMatch(value="c")),
                    Match(field="a", condition=ValueMatch(value="b")),
                    MultiMatch(condition=ValueMatch(value="d")),
                ],
            ),
            And(
                queries=[
                    Match(
                        field="a",
                        condition=ValueAnd(
                            conditions=[
                                ValueMatch(value="a"),
                                ValueMatch(value="b"),
                            ],
                        ),
                    ),
                    MultiMatch(
                        condition=ValueAnd(
                            conditions=[
                                ValueMatch(value="c"),
                                ValueMatch(value="d"),
                            ],
                        ),
                    ),
                    Gt(field="b", value=5),
                ],
            ),
        ),
        (
            And(
                queries=[
                    Exist(field="a"),
                    Exist(field="b"),
                    Match(field="a", condition=ValueMatch(value="a")),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
            And(
                queries=[
                    Match(field="a", condition=ValueMatch(value="a")),
                    Exist(field="b"),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
        ),
        (
            And(
                queries=[
                    All(),
                    Match(field="a", condition=ValueMatch(value="a")),
                ],
            ),
            Match(field="a", condition=ValueMatch(value="a")),
        ),
        (And(queries=[All(), All()]), All()),
        (
            And(queries=[Match(field="a", condition=ValueAll())]),
            Exist(field="a"),
        ),
        (
            And(
                queries=[
                    Match(field="a", condition=ValueMatch(value="b")),
                    Match(field="a", condition=ValueAll()),
                ],
            ),
            Match(field="a", condition=ValueMatch(value="b")),
        ),
        # Query OR optimizations.
        (
            Or(queries=[Match(field="a", condition=ValueMatch(value="a"))]),
            Match(field="a", condition=ValueMatch(value="a")),
        ),
        (
            Or(
                queries=[
                    Or(
                        queries=[
                            Match(field="a", condition=ValueMatch(value="a")),
                            Match(field="b", condition=ValueMatch(value="b")),
                        ],
                    ),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
            Or(
                queries=[
                    Match(field="a", condition=ValueMatch(value="a")),
                    Match(field="b", condition=ValueMatch(value="b")),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
        ),
        (
            Or(
                queries=[
                    Match(field="a", condition=ValueMatch(value="a")),
                    Match(
                        field="a",
                        condition=ValueOr(
                            conditions=[
                                ValueMatch(value="b"),
                                ValueMatch(value="c"),
                            ],
                        ),
                    ),
                ],
            ),
            Match(
                field="a",
                condition=ValueOr(
                    conditions=[
                        ValueMatch(value="a"),
                        ValueMatch(value="b"),
                        ValueMatch(value="c"),
                    ],
                ),
            ),
        ),
        (
            Or(
                queries=[
                    Match(field="a", condition=ValueMatch(value="a")),
                    Gt(field="b", value=5),
                    MultiMatch(condition=ValueMatch(value="c")),
                    Match(field="a", condition=ValueMatch(value="b")),
                    MultiMatch(condition=ValueMatch(value="d")),
                ],
            ),
            Or(
                queries=[
                    Match(
                        field="a",
                        condition=ValueOr(
                            conditions=[
                                ValueMatch(value="a"),
                                ValueMatch(value="b"),
                            ],
                        ),
                    ),
                    MultiMatch(
                        condition=ValueOr(
                            conditions=[
                                ValueMatch(value="c"),
                                ValueMatch(value="d"),
                            ],
                        ),
                    ),
                    Gt(field="b", value=5),
                ],
            ),
        ),
        (
            Or(
                queries=[
                    Exist(field="a"),
                    Exist(field="b"),
                    Match(field="a", condition=ValueMatch(value="a")),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
            Or(
                queries=[
                    Exist(field="a"),
                    Exist(field="b"),
                    Match(field="c", condition=ValueMatch(value="c")),
                ],
            ),
        ),
        (
            Or(
                queries=[
                    All(),
                    Match(field="a", condition=ValueMatch(value="a")),
                ],
            ),
            All(),
        ),
        (
            Or(
                queries=[
                    MultiMatch(condition=ValueAll()),
                    All(),
                ],
            ),
            All(),
        ),
        (
            Or(
                queries=[
                    Match(field="a", condition=ValueMatch(value="b")),
                    Match(field="a", condition=ValueAll()),
                ],
            ),
            Exist(field="a"),
        ),
        # Other tests.
        (
            Not(
                query=Nested(
                    path="person",
                    query=MultiMatch(condition=ValueMatch(value="Jennifer")),
                ),
            ),
            Nested(
                path="person",
                query=Not(
                    query=MultiMatch(condition=ValueMatch(value="Jennifer")),
                ),
            ),
        ),
        (
            Not(
                query=Or(
                    queries=[
                        Match(field="a", condition=ValueMatch(value="b")),
                        Match(
                            field="b",
                            condition=ValueNot(
                                condition=ValueMatch(value="b"),
                            ),
                        ),
                    ],
                ),
            ),
            And(
                queries=[
                    Not(
                        query=Match(
                            field="a",
                            condition=ValueMatch(value="b"),
                        ),
                    ),
                    Match(
                        field="b",
                        condition=ValueMatch(value="b"),
                    ),
                ],
            ),
        ),
        (
            Match(
                field="name",
                condition=ValueAnd(
                    conditions=[
                        ValueNot(condition=ValueMatch(value="John")),
                        ValueNot(condition=ValueMatch(value="Adam")),
                    ],
                ),
            ),
            Not(
                query=Match(
                    field="name",
                    condition=ValueOr(
                        conditions=[
                            ValueMatch(value="John"),
                            ValueMatch(value="Adam"),
                        ],
                    ),
                ),
            ),
        ),
        (
            Match(
                field="name",
                condition=ValueOr(
                    conditions=[
                        ValueNot(condition=ValueMatch(value="John")),
                        ValueNot(condition=ValueMatch(value="Adam")),
                    ],
                ),
            ),
            Not(
                query=Match(
                    field="name",
                    condition=ValueAnd(
                        conditions=[
                            ValueMatch(value="John"),
                            ValueMatch(value="Adam"),
                        ],
                    ),
                ),
            ),
        ),
    ),
)
def test_optimize(original: Query, optimized: Query) -> None:
    """Check that optimizing requests work."""
    assert optimize_kql(original) == optimized
