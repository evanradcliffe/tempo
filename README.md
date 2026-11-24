# tempo

Work-in-progress bitboard chess engine(s) in Python with Numba, built with CUDA in mind.

## Context
This codebase is being developed for the seminar *Cogsci Chess Club: A Project Seminar in Computer Chess* by Dr. Ulf Krumnack, Institute of Cognitive Science, Osnabrück University (WiSe 2026/27). Over the semester, students builds two engines, moving from move generation and alpha-beta search toward NNUE and MCTS.

> [!NOTE]
> This repository is meant to be a submodule for a harness that is not publicly available. It's not a standalone program, the entrypoints live in the harness.

## Status
- Move generation passes perft against python-chess on the standard test positions (start position, Kiwi-Pete, en passant/pins), with pin-aware legality and in-place XOR make/unmake as opt-in modes.
- Assignment 6: a material evaluator and a fixed-depth negamax search with alpha-beta pruning, both compiled (see Evaluation and Search below).
- The search adapter (`alphabeta.AlphaBetaSearch`) can't be used through the harness yet: `ccc26.search` doesn't import (its `__init__` does `from search import ...`). Its tests are skipped until it does.
- Next: move ordering, quiescence search, iterative deepening and time limits.

## Design
- **Studying representation:** symbolic vs. neural net vs. transformer evaluation
- **Bitboards in one flat array:** a position is 16 `uint64` words: 12 piece boards, 3 occupancy boards, and 1 packed word for side to move, castling rights, en passant square and clocks.
- **Speed:** move generation is compiled with `Numba` and works on plain arrays, fewer Python objects.
- **CUDA in mind:** the same layout and functions are meant to compile for the GPU via `numba-cuda` later, not implemented yet.

## Roadmap
See [milestones](https://github.com/evanradcliffe/tempo/milestones) and [issues](https://github.com/evanradcliffe/tempo/issues).

## Getting Started
Run from the root of the seminar's `winter26` repo, with this repo mounted at `src/ccc26/user/eradcliffe` (as the synced submodule, or as a symlink to a local clone).

### Testing
```
CHESS_BOARD_CLASS=ccc26.user.eradcliffe.b.Board python3 -m unittest tests/test_perft.py
python3 -m unittest ccc26.user.eradcliffe.tests.test_legal_modes                         # ~3 s
TEMPO_DIFF_GAMES=3000 python3 -m unittest ccc26.user.eradcliffe.tests.test_legal_modes   # full differential, ~1 min
python3 -m unittest ccc26.user.eradcliffe.tests.test_make_modes                          # ~3 s; TEMPO_DIFF_GAMES=3000 for the full check (~40 s)
python3 -m unittest ccc26.user.eradcliffe.tests.test_evaluate                            # ~3 s; TEMPO_DIFF_GAMES=3000 ~75 s
python3 -m unittest ccc26.user.eradcliffe.tests.test_search                              # ~6 s; TEMPO_DIFF_GAMES=3000 ~80 s
```
`test_legal_modes` checks that copy-make and pin-aware legality agree: `pinned_pieces` on hand-made pins, perft against the published counts in both modes, and random games where both modes and python-chess must give the same legal moves at every position.

> [!WARNING]
> Numba's `cache=True` only recompiles a function when **its own file** changes. If you edit `bitboard.py` or `attacks.py`, cached functions in `movegen.py` keep the old compiled code and tests can pass against stale code. The same goes for `search.py` after editing `movegen.py` or `evaluate.py`, and for anything using the harness's `CHECKMATE_SCORE` if that changes. After such an edit, clear the cache first: `find . -name '*.nb[ic]' -delete` (or run with `NUMBA_CACHE_DIR` set to an empty folder).

### Benchmarking
Perft against python-chess on Start, Kiwi-Pete and En Passant & Pins, with the JIT warmed up first. Each run gets a folder in `bench/results/`:
- `results.json`: every timed run, the warm-up times, node counts, commit hash and machine. This is the source of truth.
- `README.md`, `speed.png`, `speed_by_depth.png`, `staircase.png`: the writeup and charts, generated from `results.json` alone.

```
python3 -m ccc26.user.eradcliffe.bench                  # depths 1-4, 5 runs per cell
NUMBA_DISABLE_JIT=1 python3 -m ccc26.user.eradcliffe.bench -d 3 -r 3
python3 -m ccc26.user.eradcliffe.bench.report           # rebuild the latest report from its JSON
python3 -m ccc26.user.eradcliffe.bench.report <run> --nojit <no-JIT run>   # add a no-JIT bar to the staircase
```
Eleven engines, all checked against the published perft counts:
- **python-chess**: the course's `reference_perft`, one push/pop per node.
- **tempo · from Python**: the course's `custom_perft` on `b.Board`, also one push/pop per node from Python. This mostly measures interface cost.
- **tempo · compiled**: `movegen.perft_every_leaf`, the whole recursion in Numba with every leaf move made. This is the fair comparison with python-chess.
- **tempo · compiled + bulk count**: `movegen.perft`, which counts the last ply from the legal-move list instead of making each move. It visits the same nodes with less work, the usual engine trick.
- **· pin-aware**: both compiled engines run a second time with pin-aware legality (see below), next to the copy-make baseline.
- **· XOR**: every tempo engine above also runs with in-place XOR make/unmake (see Make modes), right after its copy twin. In the charts a twin keeps its twin's color, with hatched bars and a dashed line. "from Python" uses `TEMPO_LEGAL` for legality but always sets the make mode itself, so `TEMPO_MAKE` doesn't change the bench.

Each engine's legality and make mode are saved in `results.json`.

`staircase.png` puts all engines for one position and depth (Kiwi-Pete, depth 4 by default) in order from slowest to fastest. With `--nojit` it adds the every-leaf engine from a `NUMBA_DISABLE_JIT=1` run as plain Python. Charts need `matplotlib` (`uv pip install matplotlib`). Without it, the report is written without charts.

#### Search benchmark
The same conventions for the search: JIT warm-up, engines taking turns run by run, and one folder per run in `bench/results/` (ending in `_search`), with `results.json` as the source of truth.
```
python3 -m ccc26.user.eradcliffe.bench.search              # depths 1-4, python-chess to depth 3, 5 runs per cell
python3 -m ccc26.user.eradcliffe.bench.search.report       # rebuild the latest search report from its JSON
```
- **What it times:** on Start, Kiwi-Pete and En Passant & Pins, it times `search_root` with alpha-beta and with plain negamax, recording nodes, root score and best move. It also times the python-chess negamax from `tests/test_search.py` (same material eval and leaf rules) up to depth 3.
- **Evaluation speed:** on every node of seeded random games, it compares python-chess's material count with the compiled `evaluate()`, both called from Python and in a compiled loop.
- **Checks:** the run exits with 1, after saving, if alpha-beta and negamax root scores differ anywhere, if python-chess's score differs from ours, if alpha-beta visits more nodes than negamax, if any engine repeats a cell differently, or if the two evals disagree on a position.
- **Report:** `README.md` with `nodes.png` (nodes by depth), `time.png` (time by depth, against python-chess) and `pruning.png` (negamax nodes ÷ alpha-beta nodes).

### Legality modes
Move generation produces pseudo-legal moves, then filters out the ones that leave the own king in check. There are two ways to do that filter, chosen at runtime:
- `copymake` (default): play every move on a copy and test whether the king is attacked.
- `pinaware`: when not in check, moves by a piece that is neither the king nor pinned skip that test (except en passant), because they can't expose the king. Everything else still gets the full test.

`b.Board` reads `TEMPO_LEGAL=copymake|pinaware` (or `Board(fen, legal="pinaware")`) and passes the mode into the compiled functions as an argument, so both modes coexist in one process.

### Make modes
How a move is applied, independent of the legality mode (the `copymake` legality mode just means "try every move", whichever make mode does the trying):
- `copy` (default): `make_move` returns a new 16-word state array. Undo means keeping the old array.
- `xor`: `make_inplace` changes the one state array in place. It XORs the moved piece's from/to bits into its board and the occupancy boards, clears a captured piece's bit, and returns an undo record of two numbers: the captured piece type and the old meta word. `unmake_inplace` repeats the XORs and restores the meta word.

`b.Board` reads `TEMPO_MAKE=copy|xor` (or `Board(fen, make="xor")`). The compiled functions take it as one more argument: `generate_legal(state, moves, mode, make)`, `perft(state, depth, mode, make)` and so on. In `xor` mode, `board.state` stays the same array object for the board's whole life, so copy it if you want to keep a position. `test_make_modes` checks that `make_inplace` produces exactly what `make_move` does for every legal move along random games, and that `unmake_inplace` restores the array bit for bit.

### Evaluation
`evaluate.evaluate(state, mode)` scores a position in centipawns from the side to move's view: positive is good for the player to move. It is static. It generates no moves and doesn't detect checkmate or stalemate, which is the search's job. Modes work like the legality modes: `EVAL_MODES` maps a name to an int that is passed through the compiled search, so a piece-square-table eval can be added as mode 1 later.
- `material` (mode 0): pawn 100, knight 320, bishop 330, rook 500, queen 900, king 0.

`Evaluator(mode="material")` is the harness's `AbstractEvaluator`: `Evaluator().evaluate(board)` runs the compiled eval on a `b.Board`'s state. `test_evaluate` checks the start position, hand-made imbalances with each side to move, mirrored positions, and a material count written on python-chess at every node of random games.

### Search
`search.py` is a fixed-depth negamax, compiled with Numba. It walks the tree on one state array with `make_inplace`/`unmake_inplace` and pin-aware legality, with no Python per node, and the array is back bit for bit when it returns.
- `search_root(state, depth, eval_mode, search_mode)` returns `(best move, score, nodes)`. Ties go to the first move in generation order. With no legal move at the root it returns `NO_MOVE` and `-CHECKMATE_SCORE` or `DRAW_SCORE`.
- `negamax(state, depth, eval_mode, search_mode)` returns just the score.
- `SEARCH_MODES`: `alphabeta` (default) prunes. `negamax` searches every move and is the reference: both give the same root score, and alpha-beta never visits more nodes.
- Scores come from the harness (`CHECKMATE_SCORE = 30000`, `DRAW_SCORE = 0`). Being checkmated at ply p scores `-(CHECKMATE_SCORE - p)`, so a quicker mate scores higher. With no legal move, an interior node is mate or stalemate. A leaf (depth 0) is mate if in check with no legal move, otherwise the static eval; stalemate at leaves is ignored for now. There's no 50-move rule or repetition yet.

`alphabeta.AlphaBetaSearch(mode="alphabeta")` is the harness's `AbstractSearch`. It needs a `b.Board` and an `Evaluator`, uses `limits.depth` (default 3), and ignores the other limits. `stop()` can't interrupt a search already running in compiled code. It is in its own module because `ccc26.search` doesn't import yet.

Nodes visited (root included), material eval:

| Position | Depth | alpha-beta | negamax |
|---|---:|---:|---:|
| Start | 1 | 21 | 21 |
| Start | 2 | 60 | 421 |
| Start | 3 | 586 | 9,323 |
| Start | 4 | 2,012 | 206,604 |
| Kiwi-Pete | 1 | 49 | 49 |
| Kiwi-Pete | 2 | 456 | 2,088 |
| Kiwi-Pete | 3 | 6,903 | 99,950 |
| Kiwi-Pete | 4 | 26,518 | 4,185,553 |

Plain negamax visits exactly one more than the sum of the perft counts up to that depth.

`test_search` checks mate in 1 and 2, a hanging queen, a defended pawn, checkmate and stalemate at the root, alpha-beta against negamax on positions from random games, a negamax written on python-chess with the same eval and leaf rules, and that the state is unchanged after every search.

### Profiling

#### cProfile
```
python3 -m cProfile -s cumulative -m ccc26.eval.perft \
  --board ccc26.user.eradcliffe.b.Board -d 4 --mode custom \
  --fen "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
```

With pin aware enhancement and Numba disabled
```
TEMPO_LEGAL=pinaware NUMBA_DISABLE_JIT=1 python3 -m cProfile -s cumulative -m ccc26.eval.perft \
  --board ccc26.user.eradcliffe.b.Board -d 3 --mode custom \
  --fen "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1" > perf-numbaless.txt
```

#### profiling.sampling
>[!NOTE]
> Requires Python 3.15!

```
python3 -m profiling.sampling run -r 20khz --native --binary -o mine.bin \
  -m ccc26.eval.perft --board ccc26.user.eradcliffe.b.Board -d 4 --mode custom \
  --fen "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
```

##### Flame graph
`python3 -m profiling.sampling replay --flamegraph -o mine-flame.html mine.bin`

##### Heatmap
`python3 -m profiling.sampling replay --heatmap -o mine-heatmap mine.bin`

## Credits & License
Template and entrypoint code provided by the seminar. Ideation and code generation done in part with Claude.

My own code is released under the [MIT License](LICENSE). The template code belongs to the seminar.
