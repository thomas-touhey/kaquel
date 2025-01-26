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
    KQLAnd,
    KQLMatch,
    KQLNot,
    KQLOr,
    KQLValueAnd,
    KQLValueMatch,
    KQLValueNot,
    KQLValueOr,
)


def test_value_condition_operators() -> None:
    """Check that native operators on value conditions work correctly."""
    a = KQLValueMatch(value="a")
    b = KQLValueMatch(value="b")
    c = KQLValueMatch(value="c")
    d = KQLValueMatch(value="d")

    assert a & b == KQLValueAnd(conditions=(a, b))
    assert KQLValueAnd(conditions=(a, b)) & c == KQLValueAnd(
        conditions=(a, b, c),
    )
    assert a & KQLValueAnd(conditions=(b, c)) == KQLValueAnd(
        conditions=(a, b, c),
    )
    assert KQLValueAnd(conditions=(a, b)) & KQLValueAnd(
        conditions=(c, d),
    ) == KQLValueAnd(conditions=(a, b, c, d))

    assert a | b == KQLValueOr(conditions=(a, b))
    assert KQLValueOr(conditions=(a, b)) | c == KQLValueOr(
        conditions=(a, b, c),
    )
    assert a | KQLValueOr(conditions=(b, c)) == KQLValueOr(
        conditions=(a, b, c),
    )
    assert KQLValueOr(conditions=(a, b)) | KQLValueOr(
        conditions=(c, d),
    ) == KQLValueOr(
        conditions=(a, b, c, d),
    )

    assert ~a == KQLValueNot(condition=a)
    assert ~KQLValueNot(condition=a) == a

    with pytest.raises(TypeError):
        a & 5

    with pytest.raises(TypeError):
        a | 5


def test_query_operators() -> None:
    """Check that native operators on queries work correctly."""
    a = KQLMatch(field="a", condition=KQLValueMatch(value="a"))
    b = KQLMatch(field="b", condition=KQLValueMatch(value="b"))
    c = KQLMatch(field="c", condition=KQLValueMatch(value="c"))
    d = KQLMatch(field="d", condition=KQLValueMatch(value="d"))

    assert a & b == KQLAnd(queries=(a, b))
    assert KQLAnd(queries=(a, b)) & c == KQLAnd(queries=(a, b, c))
    assert a & KQLAnd(queries=(b, c)) == KQLAnd(queries=(a, b, c))
    assert KQLAnd(queries=(a, b)) & KQLAnd(queries=(c, d)) == KQLAnd(
        queries=(a, b, c, d),
    )

    assert a | b == KQLOr(queries=(a, b))
    assert KQLOr(queries=(a, b)) | c == KQLOr(queries=(a, b, c))
    assert a | KQLOr(queries=(b, c)) == KQLOr(queries=(a, b, c))
    assert KQLOr(queries=(a, b)) | KQLOr(queries=(c, d)) == KQLOr(
        queries=(a, b, c, d),
    )

    assert ~a == KQLNot(query=a)
    assert ~KQLNot(query=a) == a

    with pytest.raises(TypeError):
        a & 5

    with pytest.raises(TypeError):
        a | 5
