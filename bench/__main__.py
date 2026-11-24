"""Measure perft speed for python-chess and this board, and save every raw timing.

Run from the root of the winter26 repo:
    python -m ccc26.user.eradcliffe.bench                 # depths 1-4, 5 runs per cell
    python -m ccc26.user.eradcliffe.bench -d 5 -r 3
    NUMBA_DISABLE_JIT=1 python -m ccc26.user.eradcliffe.bench -d 3

Every position and depth is timed by these engines, plus the variants below:
    python-chess          the course's reference_perft: chess.Board driven from
                          Python, one push/pop per node, every leaf played.
    tempo · from Python   the course's custom_perft on b.Board, also driven from
                          Python once per node with every leaf played. Comparable
                          to the row above, but it mostly measures per-node
                          interface cost (Python <-> Numba calls, Move objects, the
                          undo stack) rather than move generation.
    tempo · compiled      movegen.perft_every_leaf: the whole recursion runs in
                          Numba and every leaf move is made, like the two rows
                          above. This is what the board itself can do on equal terms.
    tempo · compiled      movegen.perft: same, but the last ply is counted from the
      + bulk count        legal-move list instead of making each leaf move (bulk
                          counting). Same node counts, less work; the usual engine
                          trick, shown separately so it isn't mixed into the
                          compiled-vs-Python comparison.

Both compiled engines also run a second time with pin-aware legality (" · pin-aware",
movegen.LEGAL_PINAWARE) next to the copy-make baseline, so one run compares old and
new move generation. "from Python" uses b.Board's default ($TEMPO_LEGAL, else
copymake).

Every tempo engine also runs with in-place XOR make/unmake (" · XOR",
movegen.MAKE_XOR) right after its copy-make twin, so one run compares both state
models. Each engine's legality and make mode are saved in results.json.

Before timing, each engine runs every position once at a shallow depth so the JIT
has compiled (or loaded from cache) everything; those warm-up times are saved too,
but kept out of the results. Within a cell the engines take turns run by run, so
slow drift (thermals, background load) hits all of them alike. The garbage
collector is off while timing, like timeit.

Output goes to bench/results/<date>_<time>_<commit>/: results.json with every
run, then README.md and charts generated from it by report.py. Exits with 1 if
any node count disagrees between engines or with the published perft value.
"""

import argparse
import gc
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import chess
import numba

from ....eval.perft import custom_perft, reference_perft
from ..b import Board, legal_mode
from ..bitboard import STARTING_FEN
from ..movegen import perft as bulk_perft
from ..movegen import LEGAL_MODES, MAKE_MODES, perft_every_leaf
from ..notation import parse_fen
from . import report

SCHEMA_VERSION = 1

# Published counts from https://www.chessprogramming.org/Perft_Results (Initial
# Position, Position 2 "Kiwipete", Position 3), an independent check on all engines.
POSITIONS = [
    ("Start", STARTING_FEN, [20, 400, 8_902, 197_281, 4_865_609, 119_060_324]),
    (
        "Kiwi-Pete",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        [48, 2_039, 97_862, 4_085_603, 193_690_690],
    ),
    (
        "En Passant & Pins",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        [14, 191, 2_812, 43_238, 674_624, 11_030_083, 178_633_661],
    ),
]

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"
WARMUP_DEPTH = 2  # deep enough to call every compiled function at least once
JIT = not numba.config.DISABLE_JIT


# --- Engines -----------------------------------------------------------------


@dataclass
class Engine:
    id: str
    label: str
    description: str
    setup: Callable[[str], Any]  # FEN -> whatever `run` needs, built outside the timer
    run: Callable[[Any, int], int]  # (setup result, depth) -> leaf nodes
    mode: str | None = None  # tempo's legality mode (movegen.LEGAL_MODES); None for python-chess
    make: str | None = None  # tempo's make mode (movegen.MAKE_MODES); None for python-chess


NO_JIT = "" if JIT else report.NO_JIT_SUFFIX
LABELS = report.ENGINE_LABELS


def compiled(perft: Callable[..., int], mode: str, make: str) -> Callable[[Any, int], int]:
    legal, how = LEGAL_MODES[mode], MAKE_MODES[make]
    return lambda state, depth: int(perft(state, depth, legal, how))


def board(make: str) -> Callable[[str], Board]:
    return lambda fen: Board(fen, make=make)


XOR = " With in-place XOR make/unmake on one state array instead of copying it per move."


def tempo(id: str, description: str, setup: Callable[[str], Any], run: Callable[[Any, int], int], mode: str,
          make: str) -> Engine:
    if make == "xor":
        id, description = id + report.XOR_ID_SUFFIX, description + XOR
    return Engine(id, LABELS[id] + NO_JIT, description, setup, run, mode, make)


HARNESS = ("The course harness's custom_perft on b.Board, also driven from Python once per node with every "
           "leaf played. Mostly measures per-node interface cost, not move generation.")
FULL = ("movegen.perft_every_leaf: the whole recursion in Numba, no Python per node, every leaf move made. "
        "What the board itself can do, on the same terms as the two above.")
FULL_PIN = ("Same as tempo · compiled, with pin-aware legality: moves by unpinned non-king pieces skip the "
            "make-and-test check when not in check.")
BULK = ("movegen.perft: like tempo · compiled, but the last ply is counted from the legal-move list "
        "instead of making each leaf move (bulk counting). Same nodes, less work per node.")
BULK_PIN = "Same as tempo · compiled + bulk count, with pin-aware legality."

ENGINES = [
    Engine(
        "python-chess",
        LABELS["python-chess"],
        "The course harness's reference_perft: chess.Board driven from Python, one push/pop per node, "
        "every leaf played.",
        chess.Board,
        reference_perft,
    ),
    # Each copy-make engine is followed by its XOR twin, so they sit side by side in tables and charts.
    *(tempo("tempo-harness", HARNESS, board(make), custom_perft, legal_mode(), make) for make in MAKE_MODES),
    *(tempo("tempo-compiled-full", FULL, parse_fen, compiled(perft_every_leaf, "copymake", make), "copymake", make)
      for make in MAKE_MODES),
    *(tempo("tempo-compiled-full-pinaware", FULL_PIN, parse_fen, compiled(perft_every_leaf, "pinaware", make),
            "pinaware", make) for make in MAKE_MODES),
    *(tempo("tempo-compiled", BULK, parse_fen, compiled(bulk_perft, "copymake", make), "copymake", make)
      for make in MAKE_MODES),
    *(tempo("tempo-compiled-pinaware", BULK_PIN, parse_fen, compiled(bulk_perft, "pinaware", make), "pinaware", make)
      for make in MAKE_MODES),
]


def timed(engine: Engine, state: Any, depth: int) -> tuple[int, float]:
    """(nodes, wall seconds) for one run. perft push/pops back to the root, so `state` can be reused."""
    start = time.perf_counter()
    nodes = engine.run(state, depth)
    return nodes, time.perf_counter() - start


# --- Run metadata ------------------------------------------------------------


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout.strip()


def commit() -> tuple[str, bool | None]:
    """Short hash, and whether anything but the results folder has uncommitted changes."""
    try:
        sha = git("rev-parse", "--short", "HEAD")
        dirty = git("status", "--porcelain", "--", ".", f":(exclude){RESULTS_DIR.relative_to(REPO)}")
    except (OSError, subprocess.CalledProcessError):
        return "unknown", None
    return sha, bool(dirty)


def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def load_average() -> list[float] | None:
    try:
        return [round(x, 2) for x in os.getloadavg()]
    except OSError:
        return None


# --- Main --------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Perft benchmark of this board against python-chess.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--depth", "-d", type=int, default=4, help="Deepest depth to time (runs 1..depth).")
    parser.add_argument("--repeat", "-r", type=int, default=5, help="Timed runs per engine per cell.")
    parser.add_argument("--no-save", action="store_true", help="Print the summary only, save nothing.")
    args = parser.parse_args()
    if args.depth < 1 or args.repeat < 1:
        parser.error("--depth and --repeat must be at least 1")

    started = datetime.now()
    sha, dirty = commit()
    clock = time.get_clock_info("perf_counter")
    data: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "started": started.isoformat(timespec="seconds"),
        "commit": sha,
        "dirty": dirty,
        "machine": {
            "cpu": cpu_name(),
            "threads": os.cpu_count(),
            "platform": platform.platform(),
            "load_average_start": load_average(),
        },
        "versions": {
            "python": platform.python_version(),
            "python_chess": chess.__version__,
            "numba": numba.__version__,
        },
        "jit": JIT,
        "settings": {
            "max_depth": args.depth,
            "repeat": args.repeat,
            "warmup_depth": min(WARMUP_DEPTH, args.depth),
            "gc_disabled_while_timing": True,
            "timer": "time.perf_counter",
            "timer_resolution_s": clock.resolution,
        },
        "engines": [{"id": e.id, "label": e.label, "description": e.description, "mode": e.mode,
                     "make": e.make} for e in ENGINES],
        "positions": [{"name": name, "fen": fen, "published": published} for name, fen, published in POSITIONS],
        "warmup": [],
        "results": [],
    }

    print("Warming up the JIT...", file=sys.stderr)
    for name, fen, _ in POSITIONS:
        for engine in ENGINES:
            depth = data["settings"]["warmup_depth"]
            _, seconds = timed(engine, engine.setup(fen), depth)
            data["warmup"].append({"position": name, "engine": engine.id, "depth": depth, "seconds": seconds})

    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for name, fen, _ in POSITIONS:
            for depth in range(1, args.depth + 1):
                print(f"  {name}, depth {depth}", file=sys.stderr)
                states = {e.id: e.setup(fen) for e in ENGINES}
                cells = {e.id: {"position": name, "depth": depth, "engine": e.id, "nodes": [], "seconds": []} for e in ENGINES}
                for _ in range(args.repeat):
                    for engine in ENGINES:  # take turns so drift affects every engine alike
                        nodes, seconds = timed(engine, states[engine.id], depth)
                        cells[engine.id]["nodes"].append(nodes)
                        cells[engine.id]["seconds"].append(seconds)
                data["results"] += cells.values()
    finally:
        if gc_was_enabled:
            gc.enable()

    data["finished"] = datetime.now().isoformat(timespec="seconds")
    data["machine"]["load_average_end"] = load_average()

    print(report.summary(data))
    if not args.no_save:
        run_dir = RESULTS_DIR / f"{started:%Y-%m-%d_%H%M%S}_{sha}{'-dirty' if dirty else ''}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / report.RESULTS_FILE).write_text(json.dumps(data, indent=2) + "\n")
        readme = report.write_report(run_dir)
        print(f"Saved {run_dir / report.RESULTS_FILE}\nReport {readme}", file=sys.stderr)
    if report.problems(data):
        sys.exit("Node counts are wrong:\n" + "\n".join(report.problems(data)))


if __name__ == "__main__":
    main()
