from __future__ import annotations

from sys import stdin

from kaquel.kql.parser import parse_kql


# Read the raw KQL query from standard input.
raw_query = stdin.read()

# Parse the raw KQL query into a kaquel.es_query.lang.Query object.
query = parse_kql(raw_query)

# Print the result.
print(f"{type(query).__name__}({query})")
