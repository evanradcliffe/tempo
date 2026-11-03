# Developer Module

This is your personal development workspace for the CCC Winter26 project.

## Important Rules & Guidelines

* **Your Workspace:** You have exclusive write access to this directory (and its associated repository). 
* **Other Directories:** Please do not make any changes in your colleagues' directories. These will either be blocked during push or cause conflicts.
* **Global Changes:** If you need changes to central files (outside of this directory), please create a Merge Request in the main project or contact the Maintainer.

## Getting Started

1. Make sure you have cloned the main project using the `--recursive` flag.
2. Write your code exclusively inside this directory.
3. Use central project classes via relative imports (e.g., `import ../../core/config`).


## Publishing Code

When you are done, commit and push your changes as usual **from within this directory**:

```bash
git add my_file.py
git commit -m "feat: Added new feature"
git push origin main
```
_Note: Your changes will only become visible in the main system once the Maintainer updates the submodule pointer in the main repository._

## Testing
`CHESS_BOARD_CLASS=ccc26.user.eradcliffe.b.Board python3 -m unittest tests/test_perft.py`

## Profiling

### cProfile
```
python3 -m cProfile -s cumulative -m ccc26.eval.perft \
  --board ccc26.user.eradcliffe.b.Board -d 6 --mode custom \
  --fen "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
```

### profiling.sampling
```
python3 -m profiling.sampling run -r 20khz --native --binary -o mine.bin \
  -m ccc26.eval.perft --board ccc26.user.eradcliffe.b.Board -d 4 --mode custom \
  --fen "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
```

#### Flame graph
`python3 -m profiling.sampling replay --flamegraph -o mine-flame.html mine.bin`

#### Heatmap
`python3 -m profiling.sampling replay --heatmap -o mine-heatmap mine.bin`
