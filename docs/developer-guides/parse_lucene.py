from __future__ import annotations

from json import dumps
from sys import stdin

from kaquel.lucene import parse_lucene


# Read the raw Lucene query from standard input.
raw_query = stdin.read()

# Parse the raw Lucene query into a kaquel.query.Query object.
query = parse_lucene(raw_query)

# Render the Query object into a Python dictionary.
rendered_query = query.render()

# Dump the Python dictionary as a JSON document on standard output.
print(dumps(rendered_query))
