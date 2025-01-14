from __future__ import annotations

from kaquel.kql.lang import And, Match, ValueMatch, ValuePhraseMatch
from kaquel.kql.renderer import render_kql


q = And(
    queries=[
        Match(field="hostname", condition=ValueMatch(value="example.org")),
        Match(field="ip", condition=ValuePhraseMatch(value="198.51.100.104")),
    ],
)
print(render_kql(q))
