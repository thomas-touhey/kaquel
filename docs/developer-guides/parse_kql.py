from __future__ import annotations

from json import dumps
from sys import stdin

from kaquel.kql import parse_kql


# Read the raw KQL query from standard input.
raw_query = stdin.read()

# Parse the raw KQL query into a kaquel.query.Query object.
query = parse_kql(raw_query)

# Render the Query object into a Python dictionary.
rendered_query = query.render()

# Dump the Python dictionary as a JSON document on standard output.
print(dumps(rendered_query))
