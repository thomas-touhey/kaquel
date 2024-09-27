from __future__ import annotations

from sys import stdin

from kaquel.es_query import parse_es_query
from kaquel.kql import render_as_kql


# Read the ES query from standard input.
query = parse_es_query(stdin.read())

# Render the ES query into a a KQL string.
kql_query = render_as_kql(query)

# Display the resulting KQL query.
print(kql_query)
