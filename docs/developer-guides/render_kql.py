from __future__ import annotations

from kaquel.kql.lang import (
    KQLAnd,
    KQLMatch,
    KQLValueMatch,
    KQLValuePhraseMatch,
)
from kaquel.kql.renderer import render_kql


q = KQLAnd(
    queries=[
        KQLMatch(
            field="hostname",
            condition=KQLValueMatch(value="example.org"),
        ),
        KQLMatch(
            field="ip",
            condition=KQLValuePhraseMatch(value="198.51.100.104"),
        ),
    ],
)
print(render_kql(q))
