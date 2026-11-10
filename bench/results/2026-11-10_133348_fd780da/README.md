# Perft benchmark: `fd780da`, 2026-11-10

At depth 4, measured against python-chess on the same positions: **tempo · from Python** 3.0–3.3×, **tempo · compiled** 21–23× and **tempo · compiled + bulk count** 35–38× (best run against best run; above 1× is faster).

| Position | Nodes | python-chess | tempo · from Python | tempo · compiled | tempo · compiled + bulk count |
|---|---:|---:|---:|---:|---:|
| Start | 197,281 | 519.5 ms · 379.73k/s | 173.7 ms · 1.14M/s (3.0×) | 25.0 ms · 7.89M/s (21×) | 14.7 ms · 13.43M/s (35×) |
| Kiwi-Pete | 4,085,603 | 11.32 s · 361.07k/s | 3.44 s · 1.19M/s (3.3×) | 500.9 ms · 8.16M/s (23×) | 294.2 ms · 13.89M/s (38×) |
| En Passant & Pins | 43,238 | 132.8 ms · 325.65k/s | 40.6 ms · 1.06M/s (3.3×) | 6.0 ms · 7.26M/s (22×) | 3.7 ms · 11.59M/s (36×) |

![Nodes per second at depth 4 for each engine and position](speed.png)

![Nodes per second by depth, every run shown as a dot](speed_by_depth.png)

![Each engine on Kiwi-Pete at depth 3, slowest to fastest](staircase.png)

The “tempo · no JIT” bar comes from run `2026-11-10_133520_fd780da`, made with `NUMBA_DISABLE_JIT=1`: the every-leaf engine run as plain Python.

## Correctness

Node counts from every run, checked against the published perft results on the [Chess Programming Wiki](https://www.chessprogramming.org/Perft_Results), which are independent of python-chess. A ✓ needs all runs of that engine to agree with it.

| Position | Depth | Published | python-chess | tempo · from Python | tempo · compiled | tempo · compiled + bulk count |
|---|---:|---:|---:|---:|---:|---:|
| Start | 1 | 20 | 20 ✓ | 20 ✓ | 20 ✓ | 20 ✓ |
| Start | 2 | 400 | 400 ✓ | 400 ✓ | 400 ✓ | 400 ✓ |
| Start | 3 | 8,902 | 8,902 ✓ | 8,902 ✓ | 8,902 ✓ | 8,902 ✓ |
| Start | 4 | 197,281 | 197,281 ✓ | 197,281 ✓ | 197,281 ✓ | 197,281 ✓ |
| Kiwi-Pete | 1 | 48 | 48 ✓ | 48 ✓ | 48 ✓ | 48 ✓ |
| Kiwi-Pete | 2 | 2,039 | 2,039 ✓ | 2,039 ✓ | 2,039 ✓ | 2,039 ✓ |
| Kiwi-Pete | 3 | 97,862 | 97,862 ✓ | 97,862 ✓ | 97,862 ✓ | 97,862 ✓ |
| Kiwi-Pete | 4 | 4,085,603 | 4,085,603 ✓ | 4,085,603 ✓ | 4,085,603 ✓ | 4,085,603 ✓ |
| En Passant & Pins | 1 | 14 | 14 ✓ | 14 ✓ | 14 ✓ | 14 ✓ |
| En Passant & Pins | 2 | 191 | 191 ✓ | 191 ✓ | 191 ✓ | 191 ✓ |
| En Passant & Pins | 3 | 2,812 | 2,812 ✓ | 2,812 ✓ | 2,812 ✓ | 2,812 ✓ |
| En Passant & Pins | 4 | 43,238 | 43,238 ✓ | 43,238 ✓ | 43,238 ✓ | 43,238 ✓ |

Every run of every engine matches the published count.

## Engines
- **python-chess**: The course harness's reference_perft: chess.Board driven from Python, one push/pop per node, every leaf played.
- **tempo · from Python**: The course harness's custom_perft on b.Board, also driven from Python once per node with every leaf played. Mostly measures per-node interface cost, not move generation.
- **tempo · compiled**: movegen.perft_every_leaf: the whole recursion in Numba, no Python per node, every leaf move made. What the board itself can do, on the same terms as the two above.
- **tempo · compiled + bulk count**: movegen.perft: like tempo · compiled, but the last ply is counted from the legal-move list instead of making each leaf move (bulk counting). Same nodes, less work per node.

## All timings

Best, median and slowest of 5 runs per cell. Spread is (slowest − best) / best. Nodes/s and speedup use the best run. Flags: **fast** = best run under 1.0 ms, so call overhead and timer noise dominate; **noisy** = spread above 10%. Raw run times are under each table and in [results.json](results.json).

### Start

`rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 20 | python-chess | 63 µs | 65 µs | 75 µs | 20% | 318.99k/s | — | fast, noisy |
| 1 | 20 | tempo · from Python | 21 µs | 21 µs | 55 µs | 165% | 973.52k/s | 3.1× | fast, noisy |
| 1 | 20 | tempo · compiled | 3 µs | 3 µs | 4 µs | 45% | 6.58M/s | 21× | fast, noisy |
| 1 | 20 | tempo · compiled + bulk count | 2 µs | 2 µs | 2 µs | 18% | 11.55M/s | 36× | fast, noisy |
| 2 | 400 | python-chess | 1.1 ms | 1.1 ms | 1.1 ms | 3% | 364.96k/s | — |  |
| 2 | 400 | tempo · from Python | 360 µs | 364 µs | 377 µs | 5% | 1.11M/s | 3.0× | fast |
| 2 | 400 | tempo · compiled | 52 µs | 52 µs | 54 µs | 4% | 7.70M/s | 21× | fast |
| 2 | 400 | tempo · compiled + bulk count | 31 µs | 31 µs | 32 µs | 5% | 12.94M/s | 35× | fast |
| 3 | 8,902 | python-chess | 21.7 ms | 21.9 ms | 22.4 ms | 3% | 409.79k/s | — |  |
| 3 | 8,902 | tempo · from Python | 7.8 ms | 7.8 ms | 7.9 ms | 2% | 1.14M/s | 2.8× |  |
| 3 | 8,902 | tempo · compiled | 1.1 ms | 1.2 ms | 1.2 ms | 7% | 8.06M/s | 20× |  |
| 3 | 8,902 | tempo · compiled + bulk count | 647 µs | 677 µs | 688 µs | 6% | 13.76M/s | 34× | fast |
| 4 | 197,281 | python-chess | 519.5 ms | 533.4 ms | 537.5 ms | 3% | 379.73k/s | — |  |
| 4 | 197,281 | tempo · from Python | 173.7 ms | 174.1 ms | 174.9 ms | 1% | 1.14M/s | 3.0× |  |
| 4 | 197,281 | tempo · compiled | 25.0 ms | 25.1 ms | 25.3 ms | 1% | 7.89M/s | 21× |  |
| 4 | 197,281 | tempo · compiled + bulk count | 14.7 ms | 14.8 ms | 14.9 ms | 1% | 13.43M/s | 35× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.0753, 0.06511, 0.0627, 0.06502, 0.06352 |
| 1 | tempo · from Python | 0.02428, 0.02111, 0.02054, 0.02088, 0.05453 |
| 1 | tempo · compiled | 0.00308, 0.003039, 0.003077, 0.003169, 0.004393 |
| 1 | tempo · compiled + bulk count | 0.001781, 0.001731, 0.001732, 0.001744, 0.002048 |
| 2 | python-chess | 1.124, 1.098, 1.107, 1.096, 1.104 |
| 2 | tempo · from Python | 0.3643, 0.3765, 0.3601, 0.3659, 0.3625 |
| 2 | tempo · compiled | 0.0524, 0.05424, 0.05193, 0.05216, 0.05207 |
| 2 | tempo · compiled + bulk count | 0.03134, 0.03232, 0.03092, 0.03106, 0.031 |
| 3 | python-chess | 21.9, 21.72, 21.78, 22.42, 22.14 |
| 3 | tempo · from Python | 7.846, 7.793, 7.925, 7.936, 7.83 |
| 3 | tempo · compiled | 1.163, 1.172, 1.105, 1.13, 1.182 |
| 3 | tempo · compiled + bulk count | 0.647, 0.6878, 0.6627, 0.6772, 0.6835 |
| 4 | python-chess | 519.5, 536, 537.5, 533.4, 527.8 |
| 4 | tempo · from Python | 174.1, 173.7, 174.9, 174.3, 173.8 |
| 4 | tempo · compiled | 25.08, 25.01, 25.26, 25.08, 25.11 |
| 4 | tempo · compiled + bulk count | 14.81, 14.75, 14.89, 14.69, 14.78 |

</details>

### Kiwi-Pete

`r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 48 | python-chess | 150 µs | 157 µs | 203 µs | 36% | 320.36k/s | — | fast, noisy |
| 1 | 48 | tempo · from Python | 41 µs | 44 µs | 49 µs | 18% | 1.16M/s | 3.6× | fast, noisy |
| 1 | 48 | tempo · compiled | 6 µs | 6 µs | 7 µs | 18% | 7.94M/s | 25× | fast, noisy |
| 1 | 48 | tempo · compiled + bulk count | 3 µs | 4 µs | 4 µs | 11% | 13.86M/s | 43× | fast, noisy |
| 2 | 2,039 | python-chess | 5.9 ms | 6.0 ms | 6.1 ms | 3% | 343.09k/s | — |  |
| 2 | 2,039 | tempo · from Python | 1.7 ms | 1.7 ms | 1.8 ms | 6% | 1.20M/s | 3.5× |  |
| 2 | 2,039 | tempo · compiled | 249 µs | 254 µs | 272 µs | 9% | 8.17M/s | 24× | fast |
| 2 | 2,039 | tempo · compiled + bulk count | 145 µs | 154 µs | 157 µs | 8% | 14.08M/s | 41× | fast |
| 3 | 97,862 | python-chess | 256.8 ms | 259.3 ms | 262.8 ms | 2% | 381.04k/s | — |  |
| 3 | 97,862 | tempo · from Python | 81.9 ms | 82.5 ms | 86.7 ms | 6% | 1.20M/s | 3.1× |  |
| 3 | 97,862 | tempo · compiled | 11.9 ms | 12.0 ms | 12.4 ms | 5% | 8.23M/s | 22× |  |
| 3 | 97,862 | tempo · compiled + bulk count | 6.8 ms | 6.8 ms | 6.9 ms | 2% | 14.44M/s | 38× |  |
| 4 | 4,085,603 | python-chess | 11.32 s | 11.36 s | 11.37 s | 1% | 361.07k/s | — |  |
| 4 | 4,085,603 | tempo · from Python | 3.44 s | 3.45 s | 3.47 s | 1% | 1.19M/s | 3.3× |  |
| 4 | 4,085,603 | tempo · compiled | 500.9 ms | 506.3 ms | 510.2 ms | 2% | 8.16M/s | 23× |  |
| 4 | 4,085,603 | tempo · compiled + bulk count | 294.2 ms | 296.0 ms | 297.9 ms | 1% | 13.89M/s | 38× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.2033, 0.1668, 0.1545, 0.1498, 0.1566 |
| 1 | tempo · from Python | 0.0488, 0.04158, 0.04147, 0.04386, 0.04469 |
| 1 | tempo · compiled | 0.007167, 0.006165, 0.006085, 0.006049, 0.006549 |
| 1 | tempo · compiled + bulk count | 0.003845, 0.003583, 0.003469, 0.003464, 0.003816 |
| 2 | python-chess | 6.146, 6.027, 5.974, 5.943, 5.946 |
| 2 | tempo · from Python | 1.74, 1.804, 1.704, 1.785, 1.705 |
| 2 | tempo · compiled | 0.2723, 0.2544, 0.2495, 0.2507, 0.264 |
| 2 | tempo · compiled + bulk count | 0.1537, 0.1527, 0.1448, 0.157, 0.156 |
| 3 | python-chess | 256.8, 259.3, 259.3, 261.2, 262.8 |
| 3 | tempo · from Python | 81.88, 82.04, 83.03, 82.54, 86.71 |
| 3 | tempo · compiled | 11.97, 11.89, 12.08, 11.97, 12.44 |
| 3 | tempo · compiled + bulk count | 6.856, 6.788, 6.94, 6.778, 6.846 |
| 4 | python-chess | 1.137e+04, 1.132e+04, 1.133e+04, 1.136e+04, 1.137e+04 |
| 4 | tempo · from Python | 3442, 3469, 3444, 3453, 3446 |
| 4 | tempo · compiled | 506.3, 510.2, 500.9, 506.3, 508.6 |
| 4 | tempo · compiled + bulk count | 294.2, 297.9, 294.3, 296, 296.2 |

</details>

### En Passant & Pins

`8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 14 | python-chess | 50 µs | 53 µs | 90 µs | 82% | 282.27k/s | — | fast, noisy |
| 1 | 14 | tempo · from Python | 15 µs | 16 µs | 31 µs | 106% | 930.60k/s | 3.3× | fast, noisy |
| 1 | 14 | tempo · compiled | 2 µs | 2 µs | 4 µs | 64% | 6.09M/s | 22× | fast, noisy |
| 1 | 14 | tempo · compiled + bulk count | 1 µs | 1 µs | 2 µs | 30% | 10.00M/s | 35× | fast, noisy |
| 2 | 191 | python-chess | 600 µs | 611 µs | 669 µs | 12% | 318.59k/s | — | fast, noisy |
| 2 | 191 | tempo · from Python | 176 µs | 181 µs | 199 µs | 13% | 1.09M/s | 3.4× | fast, noisy |
| 2 | 191 | tempo · compiled | 27 µs | 27 µs | 30 µs | 11% | 7.08M/s | 22× | fast, noisy |
| 2 | 191 | tempo · compiled + bulk count | 17 µs | 17 µs | 19 µs | 12% | 11.08M/s | 35× | fast, noisy |
| 3 | 2,812 | python-chess | 8.3 ms | 8.5 ms | 8.5 ms | 2% | 337.66k/s | — |  |
| 3 | 2,812 | tempo · from Python | 2.7 ms | 2.7 ms | 2.7 ms | 2% | 1.05M/s | 3.1× |  |
| 3 | 2,812 | tempo · compiled | 378 µs | 385 µs | 414 µs | 9% | 7.43M/s | 22× | fast |
| 3 | 2,812 | tempo · compiled + bulk count | 233 µs | 234 µs | 241 µs | 3% | 12.04M/s | 36× | fast |
| 4 | 43,238 | python-chess | 132.8 ms | 133.0 ms | 133.2 ms | 0% | 325.65k/s | — |  |
| 4 | 43,238 | tempo · from Python | 40.6 ms | 41.0 ms | 41.2 ms | 1% | 1.06M/s | 3.3× |  |
| 4 | 43,238 | tempo · compiled | 6.0 ms | 6.1 ms | 6.2 ms | 4% | 7.26M/s | 22× |  |
| 4 | 43,238 | tempo · compiled + bulk count | 3.7 ms | 3.8 ms | 3.8 ms | 2% | 11.59M/s | 36× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.09023, 0.05875, 0.05261, 0.0496, 0.05008 |
| 1 | tempo · from Python | 0.03106, 0.0172, 0.01623, 0.01504, 0.01568 |
| 1 | tempo · compiled | 0.003773, 0.002491, 0.002318, 0.002485, 0.002298 |
| 1 | tempo · compiled + bulk count | 0.001816, 0.001554, 0.001441, 0.0014, 0.001408 |
| 2 | python-chess | 0.6693, 0.5995, 0.6107, 0.608, 0.6373 |
| 2 | tempo · from Python | 0.19, 0.179, 0.1813, 0.176, 0.199 |
| 2 | tempo · compiled | 0.02995, 0.02717, 0.02721, 0.02698, 0.02997 |
| 2 | tempo · compiled + bulk count | 0.01897, 0.01743, 0.01735, 0.01724, 0.01923 |
| 3 | python-chess | 8.464, 8.328, 8.456, 8.516, 8.49 |
| 3 | tempo · from Python | 2.699, 2.698, 2.738, 2.749, 2.688 |
| 3 | tempo · compiled | 0.4136, 0.3783, 0.3879, 0.3852, 0.3825 |
| 3 | tempo · compiled + bulk count | 0.2399, 0.2407, 0.2337, 0.2336, 0.2335 |
| 4 | python-chess | 133, 133.1, 132.8, 132.9, 133.2 |
| 4 | tempo · from Python | 40.99, 41.15, 41.09, 40.83, 40.65 |
| 4 | tempo · compiled | 6.175, 6.075, 6.08, 6.137, 5.959 |
| 4 | tempo · compiled + bulk count | 3.801, 3.789, 3.771, 3.79, 3.731 |

</details>

## Warm-up (not counted)

One run per engine and position at depth 2 before any measurement, recorded here and left out of every other number. For tempo the first one includes Numba compiling or loading its cache, which is why it is much slower than the rest.

| Position | python-chess | tempo · from Python | tempo · compiled | tempo · compiled + bulk count |
|---|---:|---:|---:|---:|
| Start | 1.4 ms | 4.9 ms | 3.0 ms | 2.9 ms |
| Kiwi-Pete | 6.2 ms | 1.8 ms | 257 µs | 154 µs |
| En Passant & Pins | 679 µs | 191 µs | 29 µs | 18 µs |

## Run
- **Commit:** `fd780da`
- **When:** 2026-11-10T13:33:48 to 2026-11-10T13:35:13
- **Machine:** Intel(R) Core(TM) i7-14650HX, 24 threads, Linux-7.0.0-43-generic-x86_64-with-glibc2.43
- **Load average:** [1.63, 1.32, 1.09] at start, [1.91, 1.5, 1.17] at end (1, 5, 15 min)
- **Versions:** Python 3.15.0rc3, python-chess 1.11.2, numba 0.68.1, JIT on
- **Settings:** depths 1–4, 5 timed runs per engine per cell, warm-up at depth 2, GC off while timing, time.perf_counter (resolution 1e-09 s)

## Method
- Each engine's position object is built once per cell, outside the timer. Perft pushes and pops back to the root, so later runs start from the same position.
- Within a cell, engines take turns run by run (A, B, C, A, B, C, ...), so slow drift such as thermal throttling or background load hits every engine alike instead of one engine's whole batch.
- The garbage collector is off while timing, as in `timeit`.
- Best run is the headline number because noise only ever adds time; median and slowest are shown so you can see how much noise there was.
- Everything on this page is generated from `results.json` by `bench/report.py`; no number is typed by hand.

_Regenerate with `python -m ccc26.user.eradcliffe.bench.report 2026-11-10_133348_fd780da --nojit 2026-11-10_133520_fd780da`._
