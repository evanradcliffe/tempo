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
```

### Profiling

#### cProfile
```
python3 -m cProfile -s cumulative -m ccc26.eval.perft \
  --board ccc26.user.eradcliffe.b.Board -d 6 --mode custom \
  --fen "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
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
