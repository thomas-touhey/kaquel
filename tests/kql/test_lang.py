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
"""Tests for ``kaquel.kql.lang``."""

from __future__ import annotations

import pytest

from kaquel.kql.lang import (
    And,
    Match,
    Not,
    Or,
    ValueAnd,
    ValueMatch,
    ValueNot,
    ValueOr,
)


def test_value_condition_operators() -> None:
    """Check that native operators on value conditions work correctly."""
    a = ValueMatch(value="a")
    b = ValueMatch(value="b")
    c = ValueMatch(value="c")
    d = ValueMatch(value="d")

    assert a & b == ValueAnd(conditions=(a, b))
    assert ValueAnd(conditions=(a, b)) & c == ValueAnd(conditions=(a, b, c))
    assert a & ValueAnd(conditions=(b, c)) == ValueAnd(conditions=(a, b, c))
    assert ValueAnd(conditions=(a, b)) & ValueAnd(
        conditions=(c, d),
    ) == ValueAnd(conditions=(a, b, c, d))

    assert a | b == ValueOr(conditions=(a, b))
    assert ValueOr(conditions=(a, b)) | c == ValueOr(conditions=(a, b, c))
    assert a | ValueOr(conditions=(b, c)) == ValueOr(conditions=(a, b, c))
    assert ValueOr(conditions=(a, b)) | ValueOr(conditions=(c, d)) == ValueOr(
        conditions=(a, b, c, d),
    )

    assert ~a == ValueNot(condition=a)
    assert ~ValueNot(condition=a) == a

    with pytest.raises(TypeError):
        a & 5

    with pytest.raises(TypeError):
        a | 5


def test_query_operators() -> None:
    """Check that native operators on queries work correctly."""
    a = Match(field="a", condition=ValueMatch(value="a"))
    b = Match(field="b", condition=ValueMatch(value="b"))
    c = Match(field="c", condition=ValueMatch(value="c"))
    d = Match(field="d", condition=ValueMatch(value="d"))

    assert a & b == And(queries=(a, b))
    assert And(queries=(a, b)) & c == And(queries=(a, b, c))
    assert a & And(queries=(b, c)) == And(queries=(a, b, c))
    assert And(queries=(a, b)) & And(queries=(c, d)) == And(
        queries=(a, b, c, d),
    )

    assert a | b == Or(queries=(a, b))
    assert Or(queries=(a, b)) | c == Or(queries=(a, b, c))
    assert a | Or(queries=(b, c)) == Or(queries=(a, b, c))
    assert Or(queries=(a, b)) | Or(queries=(c, d)) == Or(queries=(a, b, c, d))

    assert ~a == Not(query=a)
    assert ~Not(query=a) == a

    with pytest.raises(TypeError):
        a & 5

    with pytest.raises(TypeError):
        a | 5
