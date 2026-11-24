# tempo

Work-in-progress bitboard chess engine(s) in Python with Numba, built with CUDA in mind.

## Context
This codebase is being developed for the seminar *Cogsci Chess Club: A Project Seminar in Computer Chess* by Dr. Ulf Krumnack, Institute of Cognitive Science, Osnabrück University (WiSe 2026/27). Over the semester, students builds two engines, moving from move generation and alpha-beta search toward NNUE and MCTS.

> [!NOTE]
> This repository is meant to be a submodule for a harness that is not publicly available. It's not a standalone program, the entrypoints live in the harness.

## Status
- Move generation passes perft against python-chess on the standard test positions (start position, Kiwi-Pete, en passant/pins).
- Now: profiling and speeding up move generation. Next: alpha-beta search.

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
```
`test_legal_modes` checks that copy-make and pin-aware legality agree: `pinned_pieces` on hand-made pins, perft against the published counts in both modes, and random games where both modes and python-chess must give the same legal moves at every position.

> [!WARNING]
> Numba's `cache=True` only recompiles a function when **its own file** changes. If you edit `bitboard.py` or `attacks.py`, cached functions in `movegen.py` keep the old compiled code and tests can pass against stale code. After such an edit, clear the cache first: `find . -name '*.nb[ic]' -delete` (or run with `NUMBA_CACHE_DIR` set to an empty folder).

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
