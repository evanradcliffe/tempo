# Perft benchmark: `bc6cecc-dirty`, 2026-11-10

At depth 4, measured against python-chess on the same positions: **tempo · harness** 3.0–3.3× and **tempo · compiled** 34.4–38.0× (best run against best run; above 1× is faster).

| Position | Nodes | python-chess | tempo · harness | tempo · compiled |
|---|---:|---:|---:|---:|
| Start | 197,281 | 509.6 ms · 387.11k/s | 169.4 ms · 1.16M/s (3.0×) | 14.4 ms · 13.74M/s (35.5×) |
| Kiwi-Pete | 4,085,603 | 10.91 s · 374.49k/s | 3.33 s · 1.23M/s (3.3×) | 287.2 ms · 14.22M/s (38.0×) |
| En Passant & Pins | 43,238 | 126.6 ms · 341.65k/s | 39.0 ms · 1.11M/s (3.2×) | 3.7 ms · 11.77M/s (34.4×) |

![Nodes per second at depth 4 for each engine and position](speed.png)

![Nodes per second by depth, every run shown as a dot](speed_by_depth.png)

## Correctness

Node counts from every run, checked against the published perft results on the [Chess Programming Wiki](https://www.chessprogramming.org/Perft_Results), which are independent of python-chess. A ✓ needs all runs of that engine to agree with it.

| Position | Depth | Published | python-chess | tempo · harness | tempo · compiled |
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
- **tempo · harness**: The course harness's custom_perft on b.Board, also driven from Python once per node. Mostly measures per-node interface cost, not move generation.
- **tempo · compiled**: movegen.perft: the whole recursion in Numba, no Python per node. What the board itself can do. Leaves are counted from the legal-move list instead of pushed one by one.

## All timings

Best, median and slowest of 5 runs per cell. Spread is (slowest − best) / best. Nodes/s and speedup use the best run. Flags: **fast** = best run under 1.0 ms, so call overhead and timer noise dominate; **noisy** = spread above 10%. Raw run times are under each table and in [results.json](results.json).

### Start

`rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 20 | python-chess | 55 µs | 57 µs | 68 µs | 24% | 365.46k/s | — | fast, noisy |
| 1 | 20 | tempo · harness | 19 µs | 19 µs | 21 µs | 11% | 1.04M/s | 2.8× | fast, noisy |
| 1 | 20 | tempo · compiled | 2 µs | 2 µs | 2 µs | 13% | 11.10M/s | 30.4× | fast, noisy |
| 2 | 400 | python-chess | 1.0 ms | 1.1 ms | 1.1 ms | 5% | 381.72k/s | — |  |
| 2 | 400 | tempo · harness | 342 µs | 351 µs | 353 µs | 3% | 1.17M/s | 3.1× | fast |
| 2 | 400 | tempo · compiled | 30 µs | 30 µs | 31 µs | 6% | 13.49M/s | 35.3× | fast |
| 3 | 8,902 | python-chess | 21.7 ms | 21.8 ms | 21.9 ms | 1% | 410.07k/s | — |  |
| 3 | 8,902 | tempo · harness | 7.6 ms | 7.7 ms | 7.7 ms | 1% | 1.16M/s | 2.8× |  |
| 3 | 8,902 | tempo · compiled | 653 µs | 657 µs | 711 µs | 9% | 13.64M/s | 33.3× | fast |
| 4 | 197,281 | python-chess | 509.6 ms | 509.8 ms | 513.0 ms | 1% | 387.11k/s | — |  |
| 4 | 197,281 | tempo · harness | 169.4 ms | 169.7 ms | 170.3 ms | 1% | 1.16M/s | 3.0× |  |
| 4 | 197,281 | tempo · compiled | 14.4 ms | 14.4 ms | 14.4 ms | 0% | 13.74M/s | 35.5× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.06787, 0.06176, 0.05631, 0.05654, 0.05472 |
| 1 | tempo · harness | 0.02128, 0.01988, 0.0192, 0.01926, 0.01939 |
| 1 | tempo · compiled | 0.002029, 0.001859, 0.001801, 0.001826, 0.001808 |
| 2 | python-chess | 1.104, 1.052, 1.057, 1.048, 1.059 |
| 2 | tempo · harness | 0.3505, 0.3526, 0.3422, 0.3476, 0.3515 |
| 2 | tempo · compiled | 0.03006, 0.02972, 0.02965, 0.03134, 0.0297 |
| 3 | python-chess | 21.87, 21.81, 21.71, 21.8, 21.75 |
| 3 | tempo · harness | 7.708, 7.683, 7.644, 7.666, 7.713 |
| 3 | tempo · compiled | 0.7106, 0.6526, 0.653, 0.6615, 0.6571 |
| 4 | python-chess | 513, 509.6, 509.7, 509.8, 510.1 |
| 4 | tempo · harness | 169.7, 169.4, 170.3, 169.8, 169.5 |
| 4 | tempo · compiled | 14.36, 14.37, 14.4, 14.39, 14.4 |

</details>

### Kiwi-Pete

`r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 48 | python-chess | 152 µs | 156 µs | 182 µs | 19% | 314.95k/s | — | fast, noisy |
| 1 | 48 | tempo · harness | 41 µs | 42 µs | 44 µs | 7% | 1.17M/s | 3.7× | fast |
| 1 | 48 | tempo · compiled | 4 µs | 4 µs | 4 µs | 12% | 12.90M/s | 41.0× | fast, noisy |
| 2 | 2,039 | python-chess | 5.7 ms | 5.8 ms | 5.8 ms | 1% | 354.74k/s | — |  |
| 2 | 2,039 | tempo · harness | 1.7 ms | 1.7 ms | 1.7 ms | 2% | 1.21M/s | 3.4× |  |
| 2 | 2,039 | tempo · compiled | 144 µs | 145 µs | 149 µs | 3% | 14.20M/s | 40.0× | fast |
| 3 | 97,862 | python-chess | 250.2 ms | 250.9 ms | 251.7 ms | 1% | 391.21k/s | — |  |
| 3 | 97,862 | tempo · harness | 79.4 ms | 79.5 ms | 80.1 ms | 1% | 1.23M/s | 3.2× |  |
| 3 | 97,862 | tempo · compiled | 6.7 ms | 6.7 ms | 6.8 ms | 2% | 14.66M/s | 37.5× |  |
| 4 | 4,085,603 | python-chess | 10.91 s | 11.03 s | 11.06 s | 1% | 374.49k/s | — |  |
| 4 | 4,085,603 | tempo · harness | 3.33 s | 3.34 s | 3.36 s | 1% | 1.23M/s | 3.3× |  |
| 4 | 4,085,603 | tempo · compiled | 287.2 ms | 288.0 ms | 293.6 ms | 2% | 14.22M/s | 38.0× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.1816, 0.1597, 0.1555, 0.1559, 0.1524 |
| 1 | tempo · harness | 0.0437, 0.04185, 0.04155, 0.04145, 0.04095 |
| 1 | tempo · compiled | 0.004169, 0.003736, 0.00372, 0.003855, 0.003754 |
| 2 | python-chess | 5.8, 5.823, 5.811, 5.748, 5.761 |
| 2 | tempo · harness | 1.708, 1.697, 1.682, 1.68, 1.701 |
| 2 | tempo · compiled | 0.1459, 0.1447, 0.1436, 0.1447, 0.1485 |
| 3 | python-chess | 250.6, 250.2, 251.7, 250.9, 250.9 |
| 3 | tempo · harness | 79.48, 80.06, 79.41, 79.41, 79.74 |
| 3 | tempo · compiled | 6.698, 6.715, 6.676, 6.7, 6.789 |
| 4 | python-chess | 1.106e+04, 1.091e+04, 1.103e+04, 1.104e+04, 1.095e+04 |
| 4 | tempo · harness | 3327, 3338, 3359, 3345, 3334 |
| 4 | tempo · compiled | 288.2, 287.5, 293.6, 287.2, 288 |

</details>

### En Passant & Pins

`8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1`

| Depth | Nodes | Engine | Best | Median | Slowest | Spread | Nodes/s | vs python-chess | Flags |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 14 | python-chess | 50 µs | 52 µs | 77 µs | 53% | 279.74k/s | — | fast, noisy |
| 1 | 14 | tempo · harness | 15 µs | 16 µs | 25 µs | 65% | 912.05k/s | 3.3× | fast, noisy |
| 1 | 14 | tempo · compiled | 2 µs | 2 µs | 2 µs | 49% | 8.88M/s | 31.7× | fast, noisy |
| 2 | 191 | python-chess | 592 µs | 602 µs | 639 µs | 8% | 322.66k/s | — | fast |
| 2 | 191 | tempo · harness | 176 µs | 178 µs | 181 µs | 3% | 1.09M/s | 3.4× | fast |
| 2 | 191 | tempo · compiled | 17 µs | 18 µs | 18 µs | 3% | 10.95M/s | 33.9× | fast |
| 3 | 2,812 | python-chess | 8.0 ms | 8.1 ms | 8.3 ms | 4% | 352.56k/s | — |  |
| 3 | 2,812 | tempo · harness | 2.6 ms | 2.6 ms | 2.6 ms | 1% | 1.10M/s | 3.1× |  |
| 3 | 2,812 | tempo · compiled | 238 µs | 238 µs | 251 µs | 5% | 11.80M/s | 33.5× | fast |
| 4 | 43,238 | python-chess | 126.6 ms | 127.0 ms | 127.9 ms | 1% | 341.65k/s | — |  |
| 4 | 43,238 | tempo · harness | 39.0 ms | 39.0 ms | 39.4 ms | 1% | 1.11M/s | 3.2× |  |
| 4 | 43,238 | tempo · compiled | 3.7 ms | 3.7 ms | 3.7 ms | 1% | 11.77M/s | 34.4× |  |

<details><summary>Raw run times, in run order</summary>

| Depth | Engine | Runs (ms) |
|---:|---|---|
| 1 | python-chess | 0.0767, 0.05005, 0.05164, 0.0509, 0.05248 |
| 1 | tempo · harness | 0.0253, 0.01535, 0.01588, 0.01592, 0.016 |
| 1 | tempo · compiled | 0.002346, 0.001593, 0.001583, 0.001577, 0.001594 |
| 2 | python-chess | 0.6392, 0.6011, 0.6074, 0.5919, 0.6022 |
| 2 | tempo · harness | 0.1811, 0.1805, 0.176, 0.1764, 0.1779 |
| 2 | tempo · compiled | 0.01797, 0.01762, 0.01746, 0.0175, 0.01744 |
| 3 | python-chess | 7.976, 8.048, 8.085, 8.084, 8.318 |
| 3 | tempo · harness | 2.574, 2.583, 2.562, 2.585, 2.585 |
| 3 | tempo · compiled | 0.2384, 0.2382, 0.2389, 0.251, 0.2384 |
| 4 | python-chess | 127.3, 126.6, 127, 126.9, 127.9 |
| 4 | tempo · harness | 39.03, 39.02, 39.02, 39.45, 39.27 |
| 4 | tempo · compiled | 3.693, 3.69, 3.716, 3.675, 3.713 |

</details>

## Warm-up (not counted)

One run per engine and position at depth 2 before any measurement, recorded here and left out of every other number. For tempo the first one includes Numba compiling or loading its cache, which is why it is much slower than the rest.

| Position | python-chess | tempo · harness | tempo · compiled |
|---|---:|---:|---:|
| Start | 2.5 ms | 7.5 ms | 2.9 ms |
| Kiwi-Pete | 5.7 ms | 1.7 ms | 142 µs |
| En Passant & Pins | 649 µs | 182 µs | 18 µs |

## Run
- **Commit:** `bc6cecc` (uncommitted changes present: numbers may not match this commit exactly)
- **When:** 2026-11-10T12:21:59 to 2026-11-10T12:23:18
- **Machine:** Intel(R) Core(TM) i7-14650HX, 24 threads, Linux-7.0.0-43-generic-x86_64-with-glibc2.43
- **Load average:** [0.82, 0.8, 0.65] at start, [1.22, 0.94, 0.71] at end (1, 5, 15 min)
- **Versions:** Python 3.15.0rc3, python-chess 1.11.2, numba 0.68.1, JIT on
- **Settings:** depths 1–4, 5 timed runs per engine per cell, warm-up at depth 2, GC off while timing, time.perf_counter (resolution 1e-09 s)

## Method
- Each engine's position object is built once per cell, outside the timer. Perft pushes and pops back to the root, so later runs start from the same position.
- Within a cell, engines take turns run by run (A, B, C, A, B, C, ...), so slow drift such as thermal throttling or background load hits every engine alike instead of one engine's whole batch.
- The garbage collector is off while timing, as in `timeit`.
- Best run is the headline number because noise only ever adds time; median and slowest are shown so you can see how much noise there was.
- Everything on this page is generated from `results.json` by `bench/report.py`; no number is typed by hand.

_Regenerate with `python -m ccc26.user.eradcliffe.bench.report 2026-11-10_122159_bc6cecc-dirty`._
