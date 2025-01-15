from __future__ import annotations

from kaquel.kql.parser import parse_kql
from kaquel.kql.renderer import render_kql


try:
    while True:
        query = parse_kql(input("> "))
        print(render_kql(query, optimize=True))
except (EOFError, KeyboardInterrupt):
    pass
