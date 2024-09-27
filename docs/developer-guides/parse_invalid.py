from __future__ import annotations

from kaquel.errors import DecodeError
from kaquel.kql import parse_kql


raw_string = "double_it:: and_give_it_to_the_next_person"

try:
    parse_kql(raw_string)
except DecodeError as exc:
    print(f"At line {exc.line}, column {exc.column}:")
    print("Syntax error starting at:")
    print(" ", raw_string[exc.offset :])
