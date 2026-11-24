"""Measure the compiled search against a python-chess negamax, and save every raw timing.

Run from the root of the winter26 repo:
    python -m ccc26.user.eradcliffe.bench.search            # depths 1-4, python-chess to 3, 5 runs per cell
    python -m ccc26.user.eradcliffe.bench.search -d 3 -r 3 --reference-depth 2

Every position and depth is searched three ways, all with the material eval and the
same leaf rules (see search.py):
    tempo · alpha-beta     search.search_root with SEARCH_ALPHABETA
    tempo · negamax        search.search_root with SEARCH_NEGAMAX: every move searched
    python-chess negamax   reference_negamax from tests/test_search.py on chess.Board,
                           at depths 1..--reference-depth only (it is slow)
For the tempo engines each run records nodes visited, root score and best move; for
python-chess, the root score.

Evaluation speed is timed separately, on every node of seeded random games from the
same positions (each timed run passes over the set enough times to last 20 ms):
python-chess's material count (tests/test_evaluate.py), the compiled
evaluate() called once per position from Python, and evaluate() in a compiled loop.

Before timing, every engine runs once per position at a shallow depth so the JIT has
compiled (or loaded from cache) everything; those times are saved but kept out of the
results. Within a cell the engines take turns run by run, and the garbage collector is
off while timing, as in the perft bench.

Output goes to bench/results/<date>_<time>_<commit>_search/: results.json with every
run, then README.md and charts generated from it by bench/search/report.py. After
saving, exits with 1 if any check fails:
    alpha-beta and negamax root scores differ,
    python-chess's root score differs from ours,
    alpha-beta visits more nodes than negamax,
    an engine gives different nodes, score or move across its own runs,
    the python-chess material count and evaluate() disagree on any position.
"""

import argparse
import gc
import json
import random
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import chess
import numpy as np
from numba import njit

from ...bitboard import STARTING_FEN
from ...evaluate import EVAL_MATERIAL, evaluate
from ...notation import move_to_uci, parse_fen
from ...search import NO_MOVE, SEARCH_ALPHABETA, SEARCH_NEGAMAX, search_root
from ...tests.test_evaluate import material
from ...tests.test_search import reference_negamax
from .. import runinfo
from ..runinfo import JIT, RESULTS_DIR, commit, machine, timer_settings, versions
from . import report

SCHEMA_VERSION = 1

POSITIONS = [  # the perft bench's positions
    ("Start", STARTING_FEN),
    ("Kiwi-Pete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
    ("En Passant & Pins", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"),
]
WARMUP_DEPTH = 2
EVAL_SEED = 2026
EVAL_GAMES = 20  # per position
EVAL_PLIES = 40
EVAL_REPEAT = 5
EVAL_MIN_RUN_S = 0.02  # each timed run repeats the whole set until it lasts this long, like timeit's autorange


# --- Engines -----------------------------------------------------------------


@dataclass
class Engine:
    id: str
    description: str
    setup: Callable[[str], Any]  # FEN -> whatever `run` needs, built outside the timer
    run: Callable[[Any, int], tuple[int | None, int, str | None]]  # -> (nodes, root score, best move)
    reference: bool = False  # only searched to --reference-depth


def tempo(search_mode: int) -> Callable[[np.ndarray, int], tuple[int, int, str | None]]:
    def run(state: np.ndarray, depth: int) -> tuple[int, int, str | None]:
        move, score, nodes = search_root(state, depth, EVAL_MATERIAL, search_mode)  # restores state
        return int(nodes), int(score), None if move == NO_MOVE else move_to_uci(int(move))
    return run


def python_chess(board: chess.Board, depth: int) -> tuple[None, int, None]:
    return None, reference_negamax(board, depth), None  # push/pops back to the root


ENGINES = [
    Engine("alphabeta", "search.search_root with alpha-beta pruning (fail-soft, full window at the root). "
           "Compiled, one state array changed in place, pin-aware legality.", parse_fen, tempo(SEARCH_ALPHABETA)),
    Engine("negamax", "search.search_root with pruning off: every move searched. The compiled reference "
           "alpha-beta must match.", parse_fen, tempo(SEARCH_NEGAMAX)),
    Engine("python-chess", "reference_negamax from tests/test_search.py: plain negamax on chess.Board from "
           "Python, same material eval and leaf rules. Returns the score only; it searches the same tree as "
           "tempo · negamax.", chess.Board, python_chess, reference=True),
]


def timed(engine: Engine, state: Any, depth: int) -> tuple[int | None, int, str | None, float]:
    start = time.perf_counter()
    nodes, score, move = engine.run(state, depth)
    return nodes, score, move, time.perf_counter() - start


# --- Evaluation speed --------------------------------------------------------


def eval_boards() -> list[chess.Board]:
    """Every node of EVAL_GAMES seeded random games of up to EVAL_PLIES plies from each position."""
    rng = random.Random(EVAL_SEED)
    boards = []
    for _, fen in POSITIONS:
        for _ in range(EVAL_GAMES):
            board = chess.Board(fen)
            for _ in range(EVAL_PLIES):
                boards.append(board.copy(stack=False))
                moves = list(board.legal_moves)
                if not moves:
                    break
                board.push(rng.choice(moves))
    return boards


@njit
def evaluate_all(states, out):
    for i in range(states.shape[0]):
        out[i] = evaluate(states[i], EVAL_MATERIAL)


def autorange(f: Callable[[], Any]) -> int:
    """How many passes over the set make one timed run last at least EVAL_MIN_RUN_S."""
    loops = 1
    while True:
        start = time.perf_counter()
        for _ in range(loops):
            f()
        if time.perf_counter() - start >= EVAL_MIN_RUN_S:
            return loops
        loops *= 2


def eval_speed() -> dict[str, Any]:
    boards = eval_boards()
    states = np.stack([parse_fen(b.fen()) for b in boards])
    out = np.empty(len(boards), dtype=np.int64)

    ways: list[tuple[str, str, Callable[[], list[int]]]] = [
        ("python-chess", "material() from tests/test_evaluate.py: a python-chess piece_map() count, per position "
         "from Python.", lambda: [material(b) for b in boards]),
        ("tempo-call", "Compiled evaluate(), called once per position from Python: includes the Python-to-Numba "
         "call, like Evaluator.evaluate.", lambda: [int(evaluate(s, EVAL_MATERIAL)) for s in states]),
        ("tempo-loop", "Compiled evaluate() in a compiled loop over all positions: the eval itself.",
         lambda: (evaluate_all(states, out), out.tolist())[1]),
    ]
    scores = {way: f() for way, _, f in ways}  # also the warm-up
    reference = scores["python-chess"]
    mismatches = [{"fen": b.fen(), "python_chess": reference[i],
                   **{way: s[i] for way, s in scores.items() if way != "python-chess"}}
                  for i, b in enumerate(boards) if any(s[i] != reference[i] for s in scores.values())]
    loops = {way: autorange(f) for way, _, f in ways}
    runs = {way: [] for way, _, _ in ways}
    for _ in range(EVAL_REPEAT):
        for way, _, f in ways:
            start = time.perf_counter()
            for _ in range(loops[way]):
                f()
            runs[way].append(time.perf_counter() - start)
    return {
        "positions": len(boards),
        "seed": EVAL_SEED,
        "games_per_position": EVAL_GAMES,
        "max_plies": EVAL_PLIES,
        "repeat": EVAL_REPEAT,
        "min_run_s": EVAL_MIN_RUN_S,
        "ways": [{"id": way, "description": d, "loops": loops[way], "seconds": runs[way]} for way, d, _ in ways],
        "mismatches": mismatches[:20],
        "mismatch_count": len(mismatches),
    }


# --- Main --------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search benchmark: compiled alpha-beta and negamax against a python-chess negamax.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--depth", "-d", type=int, default=4, help="Deepest depth to time (runs 1..depth).")
    parser.add_argument("--reference-depth", type=int, default=3, help="Deepest depth for the python-chess negamax.")
    parser.add_argument("--repeat", "-r", type=int, default=5, help="Timed runs per engine per cell.")
    parser.add_argument("--no-save", action="store_true", help="Print the summary only, save nothing.")
    args = parser.parse_args()
    if args.depth < 1 or args.repeat < 1 or args.reference_depth < 0:
        parser.error("--depth and --repeat must be at least 1, --reference-depth at least 0")

    started = datetime.now()
    sha, dirty = commit()
    data: dict[str, Any] = {
        "kind": "search",
        "schema": SCHEMA_VERSION,
        "started": started.isoformat(timespec="seconds"),
        "commit": sha,
        "dirty": dirty,
        "machine": machine(),
        "versions": versions(),
        "jit": JIT,
        "settings": {
            "max_depth": args.depth,
            "reference_max_depth": min(args.reference_depth, args.depth),
            "repeat": args.repeat,
            "warmup_depth": min(WARMUP_DEPTH, args.depth),
            "eval_mode": "material",
            **timer_settings(),
        },
        "engines": [{"id": e.id, "label": report.ENGINE_LABELS[e.id], "description": e.description,
                     "max_depth": args.reference_depth if e.reference else args.depth} for e in ENGINES],
        "positions": [{"name": name, "fen": fen} for name, fen in POSITIONS],
        "warmup": [],
        "results": [],
    }

    print("Warming up the JIT...", file=sys.stderr)
    for name, fen in POSITIONS:
        for engine in ENGINES:
            depth = min(data["settings"]["warmup_depth"], args.reference_depth if engine.reference else args.depth)
            if depth >= 1:
                *_, seconds = timed(engine, engine.setup(fen), depth)
                data["warmup"].append({"position": name, "engine": engine.id, "depth": depth, "seconds": seconds})

    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for name, fen in POSITIONS:
            for depth in range(1, args.depth + 1):
                print(f"  {name}, depth {depth}", file=sys.stderr)
                engines = [e for e in ENGINES if not e.reference or depth <= args.reference_depth]
                states = {e.id: e.setup(fen) for e in engines}
                cells = {e.id: {"position": name, "depth": depth, "engine": e.id, "nodes": [], "scores": [],
                                "moves": [], "seconds": []} for e in engines}
                for _ in range(args.repeat):
                    for engine in engines:  # take turns so drift affects every engine alike
                        nodes, score, move, seconds = timed(engine, states[engine.id], depth)
                        cell = cells[engine.id]
                        cell["nodes"].append(nodes)
                        cell["scores"].append(score)
                        cell["moves"].append(move)
                        cell["seconds"].append(seconds)
                data["results"] += cells.values()
        print("  evaluation speed", file=sys.stderr)
        data["eval"] = eval_speed()
    finally:
        if gc_was_enabled:
            gc.enable()

    data["finished"] = datetime.now().isoformat(timespec="seconds")
    data["machine"]["load_average_end"] = runinfo.load_average()

    print(report.summary(data))
    if not args.no_save:
        run_dir = RESULTS_DIR / f"{started:%Y-%m-%d_%H%M%S}_{sha}{'-dirty' if dirty else ''}_search"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / report.RESULTS_FILE).write_text(json.dumps(data, indent=2) + "\n")
        readme = report.write_report(run_dir)
        print(f"Saved {run_dir / report.RESULTS_FILE}\nReport {readme}", file=sys.stderr)
    if report.problems(data):
        sys.exit("Search checks failed:\n" + "\n".join(report.problems(data)))


if __name__ == "__main__":
    main()
