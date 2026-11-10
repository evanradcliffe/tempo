# Perft benchmark: `bc6cecc-dirty`, 2026-11-10

At depth 4, measured against python-chess on the same positions: **tempo · from Python** 3.0–3.2× and **tempo · compiled + bulk count** 34–38× (best run against best run; above 1× is faster).

| Position | Nodes | python-chess | tempo · from Python | tempo · compiled + bulk count |
|---|---:|---:|---:|---:|
| Start | 197,281 | 516.1 ms · 382.27k/s | 172.9 ms · 1.14M/s (3.0×) | 14.4 ms · 13.67M/s (36×) |
| Kiwi-Pete | 4,085,603 | 10.94 s · 373.45k/s | 3.39 s · 1.20M/s (3.2×) | 286.8 ms · 14.25M/s (38×) |
| En Passant & Pins | 43,238 | 126.7 ms · 341.34k/s | 40.1 ms · 1.08M/s (3.2×) | 3.7 ms · 11.57M/s (34×) |

![Nodes per second at depth 4 for each engine and position](speed.png)

![Nodes per second by depth, every run shown as a dot](speed_by_depth.png)

![Each engine on Kiwi-Pete at depth 3, slowest to fastest](staircase.png)

## Correctness

Node counts from every run, checked against the published perft results on the [Chess Programming Wiki](https://www.chessprogramming.org/Perft_Results), which are independent of python-chess. A ✓ needs all runs of that engine to agree with it.

| Position | Depth | Published | python-chess | tempo · from Python | tempo · compiled + bulk count |
|---|---:|---:|---:|---:|---:|
| Start | 1 | 20 | 20 ✓ | 20 ✓ | 20 ✓ |
| Start | 2 | 400 | 400 ✓ | 400 ✓ | 400 ✓ |
| Start | 3 | 8,902 | 8,902 ✓ | 8,902 ✓ | 8,902 ✓ |
| Start | 4 | 197,281 | 197,281 ✓ | 197,281 ✓ | 197,281 ✓ |
| Kiwi-Pete | 1 | 48 | 48 ✓ | 48 ✓ | 48 ✓ |
| Kiwi-Pete | 2 | 2,039 | 2,039 ✓ | 2,039 ✓ | 2,039 ✓ |
| Kiwi-Pete | 3 | 97,862 | 97,862 ✓ | 97,862 ✓ | 97,862 ✓ |
| Kiwi-Pete | 4 | 4,085,603 | 4,085,603 ✓ | 4,085,603 ✓ | 4,085,603 ✓ |
| En Passant & Pins | 1 | 14 | 14 ✓ | 14 ✓ | 14 ✓ |
| En Passant & Pins | 2 | 191 | 191 ✓ | 191 ✓ | 191 ✓ |
| En Passant & Pins | 3 | 2,812 | 2,812 ✓ | 2,812 ✓ | 2,812 ✓ |
| En Passant & Pins | 4 | 43,238 | 43,238 ✓ | 43,238 ✓ | 43,238 ✓ |

Every run of every engine matches the published count.

## Engines
- **python-chess**: The course harness's reference_perft: chess.Board driven from Python, one push/pop per node.
- **tempo · from Python**: The course harness's custom_perft on b.Board, also driven from Python once per node. Mostly measures per-node interface cost, not move generation.
- **tempo · compiled + bulk count**: movegen.perft: the whole recursion in Numba, no Python per node. What the board itself can do. Leaves are counted from the legal-move list instead of pushed one by one.

## All timings

Best, median and slowest of 5 runs per cell. Spread is (slowest − best) / best. Nodes/s and speedup use the best run. Flags: **fast** = best run under 1.0 ms, so call overhead and timer noise dominate; **noisy** = spread above 10%. Raw run times are under each table and in [results.json](results.json).

### Start

`rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 20 | python-chess | 57 µs | 58 µs | 69 µs | 20% | 348.72k/s | — | fast, noisy |
| 1 | 20 | tempo · from Python | 20 µs | 21 µs | 23 µs | 11% | 987.70k/s | 2.8× | fast, noisy |
| 1 | 20 | tempo · compiled + bulk count | 2 µs | 2 µs | 2 µs | 13% | 11.04M/s | 32× | fast, noisy |
| 2 | 400 | python-chess | 1.1 ms | 1.1 ms | 1.1 ms | 5% | 380.56k/s | — |  |
| 2 | 400 | tempo · from Python | 371 µs | 380 µs | 387 µs | 4% | 1.08M/s | 2.8× | fast |
| 2 | 400 | tempo · compiled + bulk count | 30 µs | 31 µs | 31 µs | 3% | 13.43M/s | 35× | fast |
| 3 | 8,902 | python-chess | 21.5 ms | 21.8 ms | 21.8 ms | 2% | 414.13k/s | — |  |
| 3 | 8,902 | tempo · from Python | 7.8 ms | 7.9 ms | 7.9 ms | 1% | 1.14M/s | 2.7× |  |
| 3 | 8,902 | tempo · compiled + bulk count | 645 µs | 648 µs | 653 µs | 1% | 13.80M/s | 33× | fast |
| 4 | 197,281 | python-chess | 516.1 ms | 517.6 ms | 522.4 ms | 1% | 382.27k/s | — |  |
| 4 | 197,281 | tempo · from Python | 172.9 ms | 173.3 ms | 173.3 ms | 0% | 1.14M/s | 3.0× |  |
| 4 | 197,281 | tempo · compiled + bulk count | 14.4 ms | 14.6 ms | 14.7 ms | 2% | 13.67M/s | 36× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.0687, 0.05848, 0.05787, 0.05828, 0.05735 |
| 1 | tempo · from Python | 0.02215, 0.02252, 0.02085, 0.02025, 0.02065 |
| 1 | tempo · compiled + bulk count | 0.002039, 0.001842, 0.001812, 0.001823, 0.001902 |
| 2 | python-chess | 1.106, 1.105, 1.051, 1.073, 1.106 |
| 2 | tempo · from Python | 0.3709, 0.387, 0.3709, 0.3799, 0.3817 |
| 2 | tempo · compiled + bulk count | 0.03013, 0.03054, 0.02978, 0.03058, 0.03062 |
| 3 | python-chess | 21.5, 21.84, 21.83, 21.81, 21.83 |
| 3 | tempo · from Python | 7.834, 7.91, 7.856, 7.878, 7.874 |
| 3 | tempo · compiled + bulk count | 0.6477, 0.6526, 0.6478, 0.6453, 0.6476 |
| 4 | python-chess | 522.4, 517.4, 518.8, 516.1, 517.6 |
| 4 | tempo · from Python | 173.3, 173.3, 173.3, 173.2, 172.9 |
| 4 | tempo · compiled + bulk count | 14.55, 14.62, 14.68, 14.44, 14.55 |

</details>

### Kiwi-Pete

`r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 48 | python-chess | 148 µs | 154 µs | 191 µs | 29% | 323.36k/s | — | fast, noisy |
| 1 | 48 | tempo · from Python | 44 µs | 45 µs | 50 µs | 14% | 1.10M/s | 3.4× | fast, noisy |
| 1 | 48 | tempo · compiled + bulk count | 4 µs | 4 µs | 4 µs | 14% | 12.88M/s | 40× | fast, noisy |
| 2 | 2,039 | python-chess | 5.9 ms | 5.9 ms | 5.9 ms | 2% | 348.17k/s | — |  |
| 2 | 2,039 | tempo · from Python | 1.8 ms | 1.8 ms | 1.8 ms | 3% | 1.13M/s | 3.2× |  |
| 2 | 2,039 | tempo · compiled + bulk count | 145 µs | 145 µs | 146 µs | 1% | 14.09M/s | 40× | fast |
| 3 | 97,862 | python-chess | 251.8 ms | 252.1 ms | 252.8 ms | 0% | 388.59k/s | — |  |
| 3 | 97,862 | tempo · from Python | 81.3 ms | 81.7 ms | 82.2 ms | 1% | 1.20M/s | 3.1× |  |
| 3 | 97,862 | tempo · compiled + bulk count | 6.6 ms | 6.7 ms | 6.7 ms | 1% | 14.77M/s | 38× |  |
| 4 | 4,085,603 | python-chess | 10.94 s | 11.01 s | 11.18 s | 2% | 373.45k/s | — |  |
| 4 | 4,085,603 | tempo · from Python | 3.39 s | 3.41 s | 3.43 s | 1% | 1.20M/s | 3.2× |  |
| 4 | 4,085,603 | tempo · compiled + bulk count | 286.8 ms | 287.3 ms | 294.4 ms | 3% | 14.25M/s | 38× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.1913, 0.1602, 0.1545, 0.1524, 0.1484 |
| 1 | tempo · from Python | 0.04964, 0.04478, 0.04464, 0.0436, 0.04421 |
| 1 | tempo · compiled + bulk count | 0.004259, 0.003775, 0.003789, 0.004077, 0.003728 |
| 2 | python-chess | 5.946, 5.906, 5.874, 5.856, 5.917 |
| 2 | tempo · from Python | 1.849, 1.812, 1.803, 1.816, 1.813 |
| 2 | tempo · compiled + bulk count | 0.1455, 0.1449, 0.1448, 0.1458, 0.1448 |
| 3 | python-chess | 251.8, 252.6, 252.8, 252.1, 252 |
| 3 | tempo · from Python | 81.83, 82.15, 81.34, 81.55, 81.66 |
| 3 | tempo · compiled + bulk count | 6.681, 6.687, 6.692, 6.627, 6.65 |
| 4 | python-chess | 1.115e+04, 1.094e+04, 1.101e+04, 1.118e+04, 1.101e+04 |
| 4 | tempo · from Python | 3391, 3406, 3415, 3426, 3403 |
| 4 | tempo · compiled + bulk count | 286.9, 290.5, 294.4, 286.8, 287.3 |

</details>

### En Passant & Pins

`8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 14 | python-chess | 44 µs | 46 µs | 92 µs | 112% | 320.64k/s | — | fast, noisy |
| 1 | 14 | tempo · from Python | 15 µs | 15 µs | 20 µs | 35% | 923.06k/s | 2.9× | fast, noisy |
| 1 | 14 | tempo · compiled + bulk count | 1 µs | 2 µs | 2 µs | 40% | 9.56M/s | 30× | fast, noisy |
| 2 | 191 | python-chess | 572 µs | 604 µs | 715 µs | 25% | 334.05k/s | — | fast, noisy |
| 2 | 191 | tempo · from Python | 195 µs | 196 µs | 350 µs | 80% | 979.87k/s | 2.9× | fast, noisy |
| 2 | 191 | tempo · compiled + bulk count | 18 µs | 18 µs | 20 µs | 11% | 10.74M/s | 32× | fast, noisy |
| 3 | 2,812 | python-chess | 8.0 ms | 8.1 ms | 8.2 ms | 3% | 353.29k/s | — |  |
| 3 | 2,812 | tempo · from Python | 2.7 ms | 2.7 ms | 2.7 ms | 2% | 1.06M/s | 3.0× |  |
| 3 | 2,812 | tempo · compiled + bulk count | 236 µs | 243 µs | 256 µs | 9% | 11.92M/s | 34× | fast |
| 4 | 43,238 | python-chess | 126.7 ms | 127.9 ms | 129.9 ms | 3% | 341.34k/s | — |  |
| 4 | 43,238 | tempo · from Python | 40.1 ms | 40.7 ms | 41.1 ms | 2% | 1.08M/s | 3.2× |  |
| 4 | 43,238 | tempo · compiled + bulk count | 3.7 ms | 3.8 ms | 3.8 ms | 2% | 11.57M/s | 34× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.09236, 0.04827, 0.04596, 0.0454, 0.04366 |
| 1 | tempo · from Python | 0.02048, 0.01583, 0.01517, 0.01526, 0.01531 |
| 1 | tempo · compiled + bulk count | 0.002047, 0.001497, 0.001464, 0.001529, 0.001516 |
| 2 | python-chess | 0.62, 0.5718, 0.715, 0.6035, 0.5919 |
| 2 | tempo · from Python | 0.196, 0.2091, 0.3501, 0.1954, 0.1949 |
| 2 | tempo · compiled + bulk count | 0.01779, 0.01966, 0.0187, 0.01786, 0.01785 |
| 3 | python-chess | 8.057, 7.96, 8.052, 8.179, 8.084 |
| 3 | tempo · from Python | 2.662, 2.673, 2.673, 2.694, 2.727 |
| 3 | tempo · compiled + bulk count | 0.2377, 0.2565, 0.2433, 0.2551, 0.236 |
| 4 | python-chess | 126.7, 127, 127.9, 129.9, 129.4 |
| 4 | tempo · from Python | 40.58, 40.15, 41.09, 40.84, 40.69 |
| 4 | tempo · compiled + bulk count | 3.797, 3.779, 3.795, 3.738, 3.784 |

</details>

## Warm-up (not counted)

One run per engine and position at depth 2 before any measurement, recorded here and left out of every other number. For tempo the first one includes Numba compiling or loading its cache, which is why it is much slower than the rest.

| Position | python-chess | tempo · from Python | tempo · compiled + bulk count |
|---|---:|---:|---:|
| Start | 2.5 ms | 7.7 ms | 2.8 ms |
| Kiwi-Pete | 5.9 ms | 1.8 ms | 143 µs |
| En Passant & Pins | 653 µs | 194 µs | 18 µs |

## Run
- **Commit:** `bc6cecc` (uncommitted changes present: numbers may not match this commit exactly)
- **When:** 2026-11-10T12:18:20 to 2026-11-10T12:19:41
- **Machine:** Intel(R) Core(TM) i7-14650HX, 24 threads, Linux-7.0.0-43-generic-x86_64-with-glibc2.43
- **Load average:** [0.8, 0.66, 0.56] at start, [1.25, 0.83, 0.63] at end (1, 5, 15 min)
- **Versions:** Python 3.15.0rc3, python-chess 1.11.2, numba 0.68.1, JIT on
- **Settings:** depths 1–4, 5 timed runs per engine per cell, warm-up at depth 2, GC off while timing, time.perf_counter (resolution 1e-09 s)

## Method
- Each engine's position object is built once per cell, outside the timer. Perft pushes and pops back to the root, so later runs start from the same position.
- Within a cell, engines take turns run by run (A, B, C, A, B, C, ...), so slow drift such as thermal throttling or background load hits every engine alike instead of one engine's whole batch.
- The garbage collector is off while timing, as in `timeit`.
- Best run is the headline number because noise only ever adds time; median and slowest are shown so you can see how much noise there was.
- Everything on this page is generated from `results.json` by `bench/report.py`; no number is typed by hand.

_Regenerate with `python -m ccc26.user.eradcliffe.bench.report 2026-11-10_121820_bc6cecc-dirty`._
