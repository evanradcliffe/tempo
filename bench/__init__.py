"""Perft benchmark against python-chess.

    python -m ccc26.user.eradcliffe.bench           measure, save raw JSON, write the report
    python -m ccc26.user.eradcliffe.bench.report    rebuild a report from saved JSON
        [--nojit <run>]                             add a no-JIT run's bar to staircase.png

Each run gets its own folder under bench/results/: results.json holds every raw
timing and is the source of truth; README.md and the PNG charts are generated
from it alone, so a report can always be rebuilt and checked against the data.
"""
