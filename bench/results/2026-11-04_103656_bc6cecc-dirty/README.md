# Perft benchmark: `bc6cecc-dirty`, 2026-11-04

At depth 4, measured against python-chess on the same positions: **tempo · from Python** 3.0–3.3× and **tempo · compiled + bulk count** 34–39× (best run against best run; above 1× is faster).

| Position | Nodes | python-chess | tempo · from Python | tempo · compiled + bulk count |
|---|---:|---:|---:|---:|
| Start | 197,281 | 529.7 ms · 372.43k/s | 175.0 ms · 1.13M/s (3.0×) | 14.7 ms · 13.43M/s (36×) |
| Kiwi-Pete | 4,085,603 | 11.40 s · 358.47k/s | 3.45 s · 1.18M/s (3.3×) | 292.6 ms · 13.96M/s (39×) |
| En Passant & Pins | 43,238 | 129.8 ms · 333.19k/s | 40.0 ms · 1.08M/s (3.2×) | 3.8 ms · 11.45M/s (34×) |

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
| 1 | 20 | python-chess | 55 µs | 56 µs | 69 µs | 26% | 364.81k/s | — | fast, noisy |
| 1 | 20 | tempo · from Python | 19 µs | 19 µs | 21 µs | 11% | 1.07M/s | 2.9× | fast, noisy |
| 1 | 20 | tempo · compiled + bulk count | 2 µs | 2 µs | 2 µs | 10% | 10.62M/s | 29× | fast, noisy |
| 2 | 400 | python-chess | 1.0 ms | 1.1 ms | 1.1 ms | 4% | 382.71k/s | — |  |
| 2 | 400 | tempo · from Python | 344 µs | 352 µs | 363 µs | 6% | 1.16M/s | 3.0× | fast |
| 2 | 400 | tempo · compiled + bulk count | 30 µs | 30 µs | 33 µs | 12% | 13.43M/s | 35× | fast, noisy |
| 3 | 8,902 | python-chess | 21.6 ms | 22.5 ms | 22.6 ms | 4% | 411.38k/s | — |  |
| 3 | 8,902 | tempo · from Python | 8.0 ms | 8.0 ms | 8.1 ms | 0% | 1.11M/s | 2.7× |  |
| 3 | 8,902 | tempo · compiled + bulk count | 676 µs | 699 µs | 717 µs | 6% | 13.17M/s | 32× | fast |
| 4 | 197,281 | python-chess | 529.7 ms | 530.1 ms | 548.0 ms | 3% | 372.43k/s | — |  |
| 4 | 197,281 | tempo · from Python | 175.0 ms | 176.2 ms | 177.4 ms | 1% | 1.13M/s | 3.0× |  |
| 4 | 197,281 | tempo · compiled + bulk count | 14.7 ms | 14.8 ms | 14.9 ms | 1% | 13.43M/s | 36× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.0689, 0.05812, 0.05588, 0.05617, 0.05482 |
| 1 | tempo · from Python | 0.02081, 0.0194, 0.01867, 0.01892, 0.0189 |
| 1 | tempo · compiled + bulk count | 0.00208, 0.001927, 0.001892, 0.001956, 0.001883 |
| 2 | python-chess | 1.086, 1.081, 1.048, 1.045, 1.086 |
| 2 | tempo · from Python | 0.3503, 0.357, 0.3634, 0.3443, 0.3516 |
| 2 | tempo · compiled + bulk count | 0.0303, 0.03188, 0.03336, 0.02983, 0.02978 |
| 3 | python-chess | 21.64, 22.24, 22.58, 22.54, 22.48 |
| 3 | tempo · from Python | 8.056, 8.032, 8.068, 8.046, 8.035 |
| 3 | tempo · compiled + bulk count | 0.7108, 0.6825, 0.6761, 0.7166, 0.6988 |
| 4 | python-chess | 548, 529.9, 531.5, 529.7, 530.1 |
| 4 | tempo · from Python | 175, 176.4, 176.2, 176, 177.4 |
| 4 | tempo · compiled + bulk count | 14.69, 14.84, 14.81, 14.8, 14.86 |

</details>

### Kiwi-Pete

`r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 48 | python-chess | 155 µs | 157 µs | 181 µs | 16% | 308.93k/s | — | fast, noisy |
| 1 | 48 | tempo · from Python | 43 µs | 45 µs | 48 µs | 10% | 1.10M/s | 3.6× | fast |
| 1 | 48 | tempo · compiled + bulk count | 4 µs | 4 µs | 4 µs | 10% | 12.73M/s | 41× | fast, noisy |
| 2 | 2,039 | python-chess | 6.0 ms | 6.1 ms | 6.1 ms | 2% | 338.57k/s | — |  |
| 2 | 2,039 | tempo · from Python | 1.7 ms | 1.8 ms | 1.8 ms | 3% | 1.17M/s | 3.4× |  |
| 2 | 2,039 | tempo · compiled + bulk count | 145 µs | 151 µs | 157 µs | 8% | 14.03M/s | 41× | fast |
| 3 | 97,862 | python-chess | 257.9 ms | 259.7 ms | 261.5 ms | 1% | 379.47k/s | — |  |
| 3 | 97,862 | tempo · from Python | 82.3 ms | 82.7 ms | 83.4 ms | 1% | 1.19M/s | 3.1× |  |
| 3 | 97,862 | tempo · compiled + bulk count | 6.9 ms | 7.0 ms | 7.2 ms | 3% | 14.14M/s | 37× |  |
| 4 | 4,085,603 | python-chess | 11.40 s | 11.44 s | 11.50 s | 1% | 358.47k/s | — |  |
| 4 | 4,085,603 | tempo · from Python | 3.45 s | 3.47 s | 3.48 s | 1% | 1.18M/s | 3.3× |  |
| 4 | 4,085,603 | tempo · compiled + bulk count | 292.6 ms | 293.6 ms | 296.7 ms | 1% | 13.96M/s | 39× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.181, 0.1554, 0.1602, 0.1566, 0.1573 |
| 1 | tempo · from Python | 0.04478, 0.04346, 0.04431, 0.04486, 0.0477 |
| 1 | tempo · compiled + bulk count | 0.004012, 0.003771, 0.004001, 0.004153, 0.004015 |
| 2 | python-chess | 6.098, 6.124, 6.052, 6.022, 6.065 |
| 2 | tempo · from Python | 1.794, 1.759, 1.797, 1.748, 1.791 |
| 2 | tempo · compiled + bulk count | 0.1512, 0.1453, 0.1506, 0.1496, 0.1572 |
| 3 | python-chess | 261.5, 260.4, 258.9, 257.9, 259.7 |
| 3 | tempo · from Python | 83.36, 82.73, 82.26, 82.99, 82.51 |
| 3 | tempo · compiled + bulk count | 7.156, 7.003, 6.922, 7.058, 6.971 |
| 4 | python-chess | 1.144e+04, 1.15e+04, 1.147e+04, 1.144e+04, 1.14e+04 |
| 4 | tempo · from Python | 3469, 3476, 3463, 3469, 3453 |
| 4 | tempo · compiled + bulk count | 296.7, 295.3, 293.3, 293.6, 292.6 |

</details>

### En Passant & Pins

`8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 14 | python-chess | 48 µs | 48 µs | 95 µs | 100% | 294.61k/s | — | fast, noisy |
| 1 | 14 | tempo · from Python | 14 µs | 15 µs | 20 µs | 42% | 973.03k/s | 3.3× | fast, noisy |
| 1 | 14 | tempo · compiled + bulk count | 1 µs | 2 µs | 2 µs | 18% | 9.49M/s | 32× | fast, noisy |
| 2 | 191 | python-chess | 597 µs | 602 µs | 668 µs | 12% | 320.02k/s | — | fast, noisy |
| 2 | 191 | tempo · from Python | 180 µs | 181 µs | 189 µs | 5% | 1.06M/s | 3.3× | fast |
| 2 | 191 | tempo · compiled + bulk count | 18 µs | 18 µs | 19 µs | 4% | 10.73M/s | 34× | fast |
| 3 | 2,812 | python-chess | 8.2 ms | 8.4 ms | 8.6 ms | 4% | 341.39k/s | — |  |
| 3 | 2,812 | tempo · from Python | 2.6 ms | 2.6 ms | 2.7 ms | 3% | 1.07M/s | 3.1× |  |
| 3 | 2,812 | tempo · compiled + bulk count | 245 µs | 255 µs | 260 µs | 6% | 11.46M/s | 34× | fast |
| 4 | 43,238 | python-chess | 129.8 ms | 131.1 ms | 132.1 ms | 2% | 333.19k/s | — |  |
| 4 | 43,238 | tempo · from Python | 40.0 ms | 40.7 ms | 41.1 ms | 3% | 1.08M/s | 3.2× |  |
| 4 | 43,238 | tempo · compiled + bulk count | 3.8 ms | 3.8 ms | 3.8 ms | 2% | 11.45M/s | 34× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.09484, 0.05052, 0.04752, 0.04772, 0.04767 |
| 1 | tempo · from Python | 0.02047, 0.01533, 0.01439, 0.01462, 0.01447 |
| 1 | tempo · compiled + bulk count | 0.001743, 0.001547, 0.001509, 0.001476, 0.0015 |
| 2 | python-chess | 0.6676, 0.6016, 0.6035, 0.5989, 0.5968 |
| 2 | tempo · from Python | 0.1803, 0.1812, 0.1811, 0.1811, 0.1888 |
| 2 | tempo · compiled + bulk count | 0.01787, 0.01802, 0.01797, 0.0178, 0.01856 |
| 3 | python-chess | 8.237, 8.263, 8.442, 8.595, 8.568 |
| 3 | tempo · from Python | 2.62, 2.688, 2.64, 2.647, 2.706 |
| 3 | tempo · compiled + bulk count | 0.2454, 0.2548, 0.2476, 0.2581, 0.2597 |
| 4 | python-chess | 132.1, 131.1, 131.3, 130.3, 129.8 |
| 4 | tempo · from Python | 41.1, 40.82, 40.66, 39.96, 40.47 |
| 4 | tempo · compiled + bulk count | 3.819, 3.846, 3.818, 3.777, 3.789 |

</details>

## Warm-up (not counted)

One run per engine and position at depth 2 before any measurement, recorded here and left out of every other number. For tempo the first one includes Numba compiling or loading its cache, which is why it is much slower than the rest.

| Position | python-chess | tempo · from Python | tempo · compiled + bulk count |
|---|---:|---:|---:|
| Start | 2.5 ms | 5.4 ms | 4.3 ms |
| Kiwi-Pete | 10.5 ms | 1.8 ms | 151 µs |
| En Passant & Pins | 652 µs | 186 µs | 18 µs |

## Run
- **Commit:** `bc6cecc` (uncommitted changes present: numbers may not match this commit exactly)
- **When:** 2026-11-04T10:36:56 to 2026-11-04T10:38:19
- **Machine:** Intel(R) Core(TM) i7-14650HX, 24 threads, Linux-7.0.0-42-generic-x86_64-with-glibc2.43
- **Load average:** [1.37, 0.76, 0.54] at start, [1.44, 0.91, 0.61] at end (1, 5, 15 min)
- **Versions:** Python 3.15.0rc3, python-chess 1.11.2, numba 0.68.1, JIT on
- **Settings:** depths 1–4, 5 timed runs per engine per cell, warm-up at depth 2, GC off while timing, time.perf_counter (resolution 1e-09 s)

## Method
- Each engine's position object is built once per cell, outside the timer. Perft pushes and pops back to the root, so later runs start from the same position.
- Within a cell, engines take turns run by run (A, B, C, A, B, C, ...), so slow drift such as thermal throttling or background load hits every engine alike instead of one engine's whole batch.
- The garbage collector is off while timing, as in `timeit`.
- Best run is the headline number because noise only ever adds time; median and slowest are shown so you can see how much noise there was.
- Everything on this page is generated from `results.json` by `bench/report.py`; no number is typed by hand.

_Regenerate with `python -m ccc26.user.eradcliffe.bench.report 2026-11-04_103656_bc6cecc-dirty`._
