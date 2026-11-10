"""Build a benchmark report (README.md + charts) from a saved results.json.

The report is a pure function of the JSON: nothing is re-measured, so anyone can
rebuild it and check every number against the raw runs.

Run from the root of the winter26 repo:
    python -m ccc26.user.eradcliffe.bench.report                  # latest run
    python -m ccc26.user.eradcliffe.bench.report <run folder or results.json>
    python -m ccc26.user.eradcliffe.bench.report <run> --nojit <no-JIT run> [--position Kiwi-Pete --depth 3]

--nojit adds a "tempo · no JIT" bar to staircase.png, taken from the every-leaf
engine of a run made with NUMBA_DISABLE_JIT=1.

Charts need matplotlib; without it the report is written without them.
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

RESULTS_FILE = "results.json"
REPORT_FILE = "README.md"
SPEED_CHART = "speed.png"
DEPTH_CHART = "speed_by_depth.png"
STAIRCASE_CHART = "staircase.png"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

FAST_CELL_S = 1e-3  # below this, call overhead and timer noise dominate a run
NOISY_SPREAD = 0.10  # (max - min) / min above this is flagged

STAIRCASE_POSITION = "Kiwi-Pete"
STAIRCASE_DEPTH = 4
NOJIT_ENGINE = "tempo-compiled-full"  # the engine a --nojit run contributes to the staircase
NOJIT_ID = "tempo-nojit"

# Chart colors follow the engine id, not its place in the list, so an engine keeps
# its color across runs (older runs have three engines). Slots 1-5 of the dataviz
# reference palette, slots 1-7 in the order the engines were added; every adjacent
# pair in engine order and in the staircase's likely speed orders passes the
# colorblind and normal-vision checks.
ENGINE_COLORS = {
    "python-chess": "#2a78d6",
    "tempo-harness": "#eb6834",
    "tempo-compiled-full": "#1baf7a",
    "tempo-compiled": "#eda100",
    NOJIT_ID: "#e87ba4",
    "tempo-compiled-full-pinaware": "#008300",
    "tempo-compiled-pinaware": "#6250d6",
}
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"
FALLBACK_COLOR = "#8c8a83"

# Display names by engine id. Applied when a report is built, so older runs (which
# called these "tempo · harness" and "tempo · compiled") read the same as new ones.
ENGINE_LABELS = {
    "python-chess": "python-chess",
    "tempo-harness": "tempo · from Python",
    "tempo-compiled-full": "tempo · compiled",
    "tempo-compiled": "tempo · compiled + bulk count",
}
PIN_AWARE_SUFFIX = " · pin-aware"
ENGINE_LABELS["tempo-compiled-full-pinaware"] = ENGINE_LABELS["tempo-compiled-full"] + PIN_AWARE_SUFFIX
ENGINE_LABELS["tempo-compiled-pinaware"] = ENGINE_LABELS["tempo-compiled"] + PIN_AWARE_SUFFIX
NO_JIT_SUFFIX = " (no JIT)"
MODE_NAMES = {"copymake": "copy-make", "pinaware": "pin-aware"}

Data = dict[str, Any]


# --- Statistics --------------------------------------------------------------


def cell(data: Data, position: str, depth: int, engine: str) -> Data:
    for row in data["results"]:
        if row["position"] == position and row["depth"] == depth and row["engine"] == engine:
            return row
    raise KeyError((position, depth, engine))


def best(row: Data) -> float:
    return min(row["seconds"])


def nodes(row: Data) -> int:
    return row["nodes"][0]


def spread(row: Data) -> float:
    return (max(row["seconds"]) - best(row)) / best(row)


def depths(data: Data) -> list[int]:
    return list(range(1, data["settings"]["max_depth"] + 1))


def reference(data: Data) -> str:
    """The engine every speedup is relative to: the first one, python-chess."""
    return data["engines"][0]["id"]


def is_fast(row: Data) -> bool:
    return best(row) < FAST_CELL_S


def speedup(data: Data, row: Data) -> float:
    """How many times faster than python-chess, best run against best run."""
    return best(cell(data, row["position"], row["depth"], reference(data))) / best(row)


def published(data: Data, position: str, depth: int) -> int | None:
    counts = next(p["published"] for p in data["positions"] if p["name"] == position)
    return counts[depth - 1] if depth <= len(counts) else None


def problems(data: Data) -> list[str]:
    """Every node count that disagrees with the published value, the other engines, or its own other runs."""
    out = []
    for p in data["positions"]:
        for depth in depths(data):
            rows = [cell(data, p["name"], depth, e["id"]) for e in data["engines"]]
            expected = published(data, p["name"], depth)
            seen = {n for row in rows for n in row["nodes"]}
            if len(seen) > 1 or (expected is not None and seen != {expected}):
                counts = ", ".join(f"{row['engine']}: {sorted(set(row['nodes']))}" for row in rows)
                out.append(f"{p['name']} depth {depth}: published {expected}, got {counts}")
    return out


# --- Formatting --------------------------------------------------------------


def fmt_time(secs: float) -> str:
    if secs < 1e-3:
        return f"{secs * 1e6:.0f} µs"
    if secs < 1:
        return f"{secs * 1e3:.1f} ms"
    return f"{secs:.2f} s"


def fmt_x(x: float) -> str:
    """Speedup: 38×, 3.1×, 0.042×."""
    if x >= 10:
        return f"{x:.0f}×"
    if x >= 1:
        return f"{x:.1f}×"
    return f"{x:.2g}×"


def fmt_rate(nps: float) -> str:
    for unit, scale in (("M", 1e6), ("k", 1e3)):
        if nps >= scale:
            return f"{nps / scale:.2f}{unit}/s"
    return f"{nps:.0f}/s"


def load(run_dir: Path) -> Data:
    """A run's results.json, with engine labels brought up to date (see ENGINE_LABELS)."""
    data = json.loads((run_dir / RESULTS_FILE).read_text())
    for e in data["engines"]:
        if e["id"] in ENGINE_LABELS:
            e["label"] = ENGINE_LABELS[e["id"]] + ("" if data["jit"] or e["id"] == "python-chess" else NO_JIT_SUFFIX)
    return data


def label(data: Data, engine_id: str) -> str:
    return next(e["label"] for e in data["engines"] if e["id"] == engine_id)


def md_table(header: list[str], rows: list[list[str]], align: str) -> str:
    """align: one 'l' or 'r' per column."""
    marks = ["---" if a == "l" else "---:" for a in align]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(marks) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def headline_table(data: Data) -> str:
    """Deepest depth only: one row per position, one column per engine."""
    deepest = data["settings"]["max_depth"]
    rows = []
    for p in data["positions"]:
        cells = []
        for e in data["engines"]:
            row = cell(data, p["name"], deepest, e["id"])
            text = f"{fmt_time(best(row))} · {fmt_rate(nodes(row) / best(row))}"
            if e["id"] != reference(data):
                text += f" ({fmt_x(speedup(data, row))})"
            cells.append(text)
        rows.append([p["name"], f"{nodes(cell(data, p['name'], deepest, reference(data))):,}", *cells])
    return md_table(
        ["Position", "Nodes", *(e["label"] for e in data["engines"])], rows, "lr" + "r" * len(data["engines"])
    )


def headline_sentence(data: Data) -> str:
    deepest = data["settings"]["max_depth"]
    parts = []
    for e in data["engines"][1:]:
        ups = [speedup(data, cell(data, p["name"], deepest, e["id"])) for p in data["positions"]]
        lo, hi = fmt_x(min(ups)), fmt_x(max(ups))
        parts.append(f"**{e['label']}** {hi if lo == hi else lo[:-1] + '–' + hi}")
    joined = ", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]
    return (
        f"At depth {deepest}, measured against python-chess on the same positions: "
        + joined
        + " (best run against best run; above 1× is faster)."
    )


def summary(data: Data) -> str:
    """Short text for the terminal."""
    status = "all node counts correct" if not problems(data) else f"{len(problems(data))} node count problem(s)"
    return f"{headline_table(data)}\n\n{headline_sentence(data)}\nCorrectness: {status}."


# --- Charts ------------------------------------------------------------------


def short_rate(nps: float) -> str:
    """Three significant figures, for chart labels: 402k, 1.16M, 13.7M."""
    for unit, scale in (("M", 1e6), ("k", 1e3), ("", 1)):
        if nps >= scale:
            return f"{nps / scale:.3g}{unit}"
    return f"{nps:.3g}"


def _rate_axis(axis: Any) -> None:
    """Log axis ticked at 1, 2, 5 × 10^n and labelled 300k, 1M, 2M, ..."""
    from matplotlib.ticker import FuncFormatter, LogLocator, NullLocator

    axis.set_major_locator(LogLocator(subs=(1, 2, 5)))
    axis.set_major_formatter(FuncFormatter(lambda v, _: short_rate(v)))
    axis.set_minor_locator(NullLocator())


def _style(plt: Any) -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.size": 9,
        "text.color": TEXT_PRIMARY,
        "axes.labelcolor": TEXT_SECONDARY,
        "axes.edgecolor": GRID,
        "xtick.color": TEXT_SECONDARY,
        "ytick.color": TEXT_SECONDARY,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "legend.frameon": False,
    })


def color(engine_id: str) -> str:
    return ENGINE_COLORS.get(engine_id, FALLBACK_COLOR)


def footnote(data: Data, rows: list[Data]) -> str:
    """Machine, versions, commit, and the worst spread among the cells a chart shows."""
    m, v = data["machine"], data["versions"]
    worst = math.ceil(max(spread(r) for r in rows) * 100)
    jit = "" if data["jit"] else " (JIT off)"
    return (
        f"{m['cpu']} · Python {v['python']}, Numba {v['numba']}{jit}, python-chess {v['python_chess']}\n"
        f"commit {data['commit']}{'-dirty' if data['dirty'] else ''} · "
        f"{data['settings']['repeat']} runs per bar, spread ≤ {worst}% · best run shown"
    )


def _bottom(fig: Any, note: str | None, legend: bool = True) -> None:
    """Legend, then small print, in a strip under the plot; the layout is shrunk to keep them clear."""
    height = fig.get_figheight()
    size, spacing, pad = 7, 1.5, 0.08  # note font points, line spacing, inches
    note_h = ((note.count("\n") + 1) * size * spacing / 72 + 2 * pad) if note else pad
    legend_h = 0.0
    if legend:
        labels = [t for ax in fig.axes for t in ax.get_legend_handles_labels()[1]]
        ncol = len(labels) if sum(len(t) + 6 for t in labels) <= 110 else 2
        legend_h = math.ceil(len(labels) / ncol) * 8 * 1.8 / 72 + 0.1
        fig.legend(loc="lower center", bbox_to_anchor=(0.5, note_h / height), ncol=ncol, fontsize=8,
                   borderaxespad=0)
    strip = (note_h + legend_h) / height
    fig.get_layout_engine().set(rect=(0, strip, 1, 1 - strip))
    if note:
        fig.text(0.01, pad / height, note, ha="left", va="bottom", fontsize=size, color=TEXT_SECONDARY,
                 linespacing=spacing)


def speed_chart(data: Data, path: Path) -> None:
    """Grouped bars: nodes per second at the deepest depth, one group per position, linear from 0."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    _style(plt)
    deepest = data["settings"]["max_depth"]
    positions = [p["name"] for p in data["positions"]]
    engines = data["engines"]
    height = 0.8 / len(engines)
    fig, ax = plt.subplots(figsize=(8, 0.4 * len(engines) * len(positions) + 1.8), dpi=200, layout="constrained")
    fastest, shown = 0.0, []
    for i, e in enumerate(engines):
        ys = [y - 0.4 + height * (i + 0.5) for y in range(len(positions))]
        rows = [cell(data, name, deepest, e["id"]) for name in positions]
        shown += rows
        rates = [nodes(r) / best(r) for r in rows]
        fastest = max(fastest, *rates)
        ax.barh(ys, rates, height=height, color=color(e["id"]), edgecolor=SURFACE, linewidth=1.5, zorder=2,
                label=e["label"])
        for y, rate, row in zip(ys, rates, rows):
            text = f"{short_rate(rate)}/s"
            if e["id"] != reference(data):
                text += f" · {fmt_x(speedup(data, row))}"
            ax.annotate(text, (rate, y), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=7.5, color=TEXT_PRIMARY)
    ax.set_xlim(0, fastest * 1.2)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: short_rate(v)))
    ax.set_yticks(range(len(positions)), positions)
    ax.invert_yaxis()  # first position and first engine on top
    ax.tick_params(axis="y", length=0, labelcolor=TEXT_PRIMARY)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("nodes per second (higher is faster) · × = times faster than python-chess")
    fig.suptitle(f"Perft speed at depth {deepest}", x=0.01, ha="left", fontsize=11, fontweight="bold")
    _bottom(fig, footnote(data, shown))
    fig.savefig(path)
    plt.close(fig)


def depth_chart(data: Data, path: Path) -> None:
    """Small multiples: nodes per second by depth, every run as a dot and the best run as a line.

    Cells the report flags as fast (best run under FAST_CELL_S) get hollow markers: there the
    timing is mostly call overhead, so the dip at shallow depths is not something the engine does.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _style(plt)
    positions = [p["name"] for p in data["positions"]]
    fig, axes = plt.subplots(1, len(positions), figsize=(8, 3.6), dpi=200, sharey=True, layout="constrained")
    any_fast = False
    for ax, name in zip(axes, positions):
        for e in data["engines"]:
            c = color(e["id"])
            rows = [cell(data, name, d, e["id"]) for d in depths(data)]
            for row in rows:
                runs = [nodes(row) / s for s in row["seconds"]]
                ax.plot([row["depth"]] * len(runs), runs, "o", markersize=3, zorder=2, alpha=0.45,
                        color=c, markerfacecolor="none" if is_fast(row) else c, markeredgewidth=0.8)
            ax.plot(depths(data), [nodes(r) / best(r) for r in rows], "-o", linewidth=1.5, markersize=4.5,
                    color=c, zorder=3, label=e["label"] if ax is axes[0] else None)
            fast = [r for r in rows if is_fast(r)]
            any_fast |= bool(fast)
            ax.plot([r["depth"] for r in fast], [nodes(r) / best(r) for r in fast], "o", markersize=4.5,
                    markerfacecolor=SURFACE, markeredgecolor=c, markeredgewidth=1.3, zorder=4)
        ax.set_yscale("log")
        _rate_axis(ax.yaxis)
        ax.set_xticks(depths(data))
        ax.set_title(name, fontsize=9.5, loc="left", color=TEXT_PRIMARY)
        ax.set_xlabel("depth")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("nodes per second (log)")
    fig.suptitle("Speed by depth: lines are the best run, dots are every run",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    _bottom(fig, None if not any_fast else (
        f"Hollow markers: best run under {fmt_time(FAST_CELL_S)}. A run that short is mostly "
                       "call overhead and timer noise, so the dip at shallow depths\nis the measurement, "
                       "not the engine. See the fast flag in the timings tables."))
    fig.savefig(path)
    plt.close(fig)


def load_nojit(nojit_dir: Path, position: str, depth: int) -> tuple[Data | None, str | None]:
    """The no-JIT run's every-leaf cell for the staircase, or None and a note saying why it is missing."""
    nojit = load(nojit_dir)
    if nojit["jit"]:
        sys.exit(f"--nojit run {nojit_dir.name} was made with the JIT on; run the bench with NUMBA_DISABLE_JIT=1")
    try:
        row = cell(nojit, position, depth, NOJIT_ENGINE)
    except KeyError:
        return None, (f"No “tempo · no JIT” bar: run `{nojit_dir.name}` has no `{NOJIT_ENGINE}` timing for "
                      f"{position} at depth {depth} (it ran depths 1–{nojit['settings']['max_depth']}).")
    expected = published(nojit, position, depth)
    if expected is not None and set(row["nodes"]) != {expected}:
        sys.exit(f"--nojit run {nojit_dir.name}: {position} depth {depth} counted {row['nodes']}, published {expected}")
    return {"data": nojit, "row": row, "run": nojit_dir.name}, None


def staircase_chart(data: Data, path: Path, position: str, depth: int, nojit: Data | None) -> None:
    """One bar per engine on one position and depth, slowest on top, linear from 0."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    _style(plt)
    ref = best(cell(data, position, depth, reference(data)))
    bars = []  # (label, rate, speedup, color)
    for e in data["engines"]:
        row = cell(data, position, depth, e["id"])
        bars.append((e["label"], nodes(row) / best(row), ref / best(row), color(e["id"])))
    if nojit is not None:
        row = nojit["row"]
        bars.append(("tempo · no JIT", nodes(row) / best(row), ref / best(row), color(NOJIT_ID)))
    bars.sort(key=lambda b: b[1])
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(bars) + 1.5), dpi=200, layout="constrained")
    ys = range(len(bars))
    ax.barh(ys, [b[1] for b in bars], height=0.7, color=[b[3] for b in bars], edgecolor=SURFACE, linewidth=1.5,
            zorder=2)
    for y, (_, rate, up, _) in zip(ys, bars):
        ax.annotate(f"{short_rate(rate)}/s · {'1×' if up == 1 else fmt_x(up)}", (rate, y), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=TEXT_PRIMARY)
    ax.set_xlim(0, bars[-1][1] * 1.2)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: short_rate(v)))
    ax.set_yticks(ys, [b[0] for b in bars])
    ax.invert_yaxis()  # slowest on top
    ax.tick_params(axis="y", length=0, labelcolor=TEXT_PRIMARY)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("nodes per second (higher is faster) · × = times faster than python-chess")
    fig.suptitle(f"Perft speed on {position} at depth {depth}, slowest to fastest",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    note = footnote(data, [cell(data, position, depth, e["id"]) for e in data["engines"]])
    if nojit is not None:
        n = nojit["data"]
        note += (f"\nno-JIT bar: every-leaf engine from run {nojit['run']} (NUMBA_DISABLE_JIT=1), "
                 f"{n['settings']['repeat']} runs, spread ≤ {math.ceil(spread(nojit['row']) * 100)}%")
    _bottom(fig, note, legend=False)
    fig.savefig(path)
    plt.close(fig)


def write_charts(data: Data, run_dir: Path, position: str, depth: int, nojit: Data | None) -> bool:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("matplotlib not installed; writing the report without charts", file=sys.stderr)
        return False
    speed_chart(data, run_dir / SPEED_CHART)
    depth_chart(data, run_dir / DEPTH_CHART)
    staircase_chart(data, run_dir / STAIRCASE_CHART, position, depth, nojit)
    return True


# --- Report ------------------------------------------------------------------


def correctness_section(data: Data) -> str:
    rows = []
    for p in data["positions"]:
        for depth in depths(data):
            expected = published(data, p["name"], depth)
            cells = []
            for e in data["engines"]:
                counts = set(cell(data, p["name"], depth, e["id"])["nodes"])
                ok = len(counts) == 1 and (expected is None or counts == {expected})
                cells.append(", ".join(f"{n:,}" for n in sorted(counts)) + (" ✓" if ok else " ❌"))
            rows.append([p["name"], str(depth), f"{expected:,}" if expected is not None else "—", *cells])
    found = problems(data)
    verdict = (
        "Every run of every engine matches the published count."
        if not found
        else "**Mismatches:**\n" + "\n".join(f"- {line}" for line in found)
    )
    return "\n\n".join([
        "## Correctness",
        "Node counts from every run, checked against the published perft results on the "
        "[Chess Programming Wiki](https://www.chessprogramming.org/Perft_Results), which are "
        "independent of python-chess. A ✓ needs all runs of that engine to agree with it.",
        md_table(["Position", "Depth", "Published", *(e["label"] for e in data["engines"])], rows,
                 "lrr" + "r" * len(data["engines"])),
        verdict,
    ])


def timings_section(data: Data) -> str:
    out = [
        "## All timings",
        f"Best, median and slowest of {data['settings']['repeat']} runs per cell. Spread is "
        "(slowest − best) / best. Nodes/s and speedup use the best run. Flags: "
        f"**fast** = best run under {fmt_time(FAST_CELL_S)}, so call overhead and timer noise dominate; "
        f"**noisy** = spread above {NOISY_SPREAD:.0%}. Raw run times are under each table and in "
        f"[{RESULTS_FILE}]({RESULTS_FILE}).",
    ]
    for p in data["positions"]:
        rows, raw = [], []
        for depth in depths(data):
            for e in data["engines"]:
                row = cell(data, p["name"], depth, e["id"])
                flags = [f for f, hit in (("fast", is_fast(row)), ("noisy", spread(row) > NOISY_SPREAD)) if hit]
                rows.append([
                    str(depth), f"{nodes(row):,}", e["label"],
                    fmt_time(best(row)), fmt_time(statistics.median(row["seconds"])), fmt_time(max(row["seconds"])),
                    f"{spread(row):.0%}", fmt_rate(nodes(row) / best(row)),
                    "—" if e["id"] == reference(data) else fmt_x(speedup(data, row)),
                    ", ".join(flags),
                ])
                raw.append([str(depth), e["label"], ", ".join(f"{s * 1e3:.4g}" for s in row["seconds"])])
        out += [
            f"### {p['name']}",
            f"`{p['fen']}`",
            md_table(["Depth", "Nodes", "Engine", "Best", "Median", "Slowest", "Spread", "Nodes/s", "vs python-chess",
                      "Flags"], rows, "rrlrrrrrrl"),
            "<details><summary>Raw run times, in run order</summary>\n\n"
            + md_table(["Depth", "Engine", "Runs (ms)"], raw, "rll")
            + "\n\n</details>",
        ]
    return "\n\n".join(out)


def warmup_section(data: Data) -> str:
    rows = []
    for p in data["positions"]:
        times = {w["engine"]: w["seconds"] for w in data["warmup"] if w["position"] == p["name"]}
        rows.append([p["name"], *(fmt_time(times[e["id"]]) for e in data["engines"])])
    return "\n\n".join([
        "## Warm-up (not counted)",
        f"One run per engine and position at depth {data['settings']['warmup_depth']} before any measurement, "
        "recorded here and left out of every other number. For tempo the first one includes Numba compiling "
        "or loading its cache, which is why it is much slower than the rest.",
        md_table(["Position", *(e["label"] for e in data["engines"])], rows, "l" + "r" * len(data["engines"])),
    ])


def run_section(data: Data) -> str:
    s, m, v = data["settings"], data["machine"], data["versions"]
    dirty = {True: " (uncommitted changes present: numbers may not match this commit exactly)",
             False: "", None: " (git status unknown)"}[data["dirty"]]
    load = f"{m['load_average_start']} at start, {m['load_average_end']} at end (1, 5, 15 min)"
    return "\n".join([
        "## Run",
        f"- **Commit:** `{data['commit']}`{dirty}",
        f"- **When:** {data['started']} to {data['finished']}",
        f"- **Machine:** {m['cpu']}, {m['threads']} threads, {m['platform']}",
        f"- **Load average:** {load}",
        f"- **Versions:** Python {v['python']}, python-chess {v['python_chess']}, numba {v['numba']}, "
        f"JIT {'on' if data['jit'] else 'off (NUMBA_DISABLE_JIT=1)'}",
        f"- **Settings:** depths 1–{s['max_depth']}, {s['repeat']} timed runs per engine per cell, "
        f"warm-up at depth {s['warmup_depth']}, GC off while timing, {s['timer']} "
        f"(resolution {s['timer_resolution_s']:.0e} s)",
    ])


def engines_section(data: Data) -> str:
    def mode(e: Data) -> str:
        return f" Legality: {MODE_NAMES.get(e['mode'], e['mode'])}." if e.get("mode") else ""

    return "\n".join(["## Engines", *(f"- **{e['label']}**: {e['description']}{mode(e)}" for e in data["engines"])])


def method_section() -> str:
    return "\n".join([
        "## Method",
        "- Each engine's position object is built once per cell, outside the timer. Perft pushes and pops "
        "back to the root, so later runs start from the same position.",
        "- Within a cell, engines take turns run by run (A, B, C, A, B, C, ...), so slow drift such as "
        "thermal throttling or background load hits every engine alike instead of one engine's whole batch.",
        "- The garbage collector is off while timing, as in `timeit`.",
        "- Best run is the headline number because noise only ever adds time; median and slowest are shown "
        "so you can see how much noise there was.",
        "- Everything on this page is generated from `results.json` by `bench/report.py`; no number is typed by hand.",
    ])


def staircase_target(data: Data, position: str | None, depth: int | None) -> tuple[str, int]:
    names = [p["name"] for p in data["positions"]]
    if position is None:
        position = STAIRCASE_POSITION if STAIRCASE_POSITION in names else names[0]
    if depth is None:
        depth = min(STAIRCASE_DEPTH, data["settings"]["max_depth"])
    if position not in names or depth not in depths(data):
        sys.exit(f"No {position} at depth {depth} in this run (positions: {', '.join(names)}; "
                 f"depths 1–{data['settings']['max_depth']})")
    return position, depth


def write_report(run_dir: Path, nojit_dir: Path | None = None, position: str | None = None,
                 depth: int | None = None) -> Path:
    data = load(run_dir)
    position, depth = staircase_target(data, position, depth)
    nojit, nojit_note = load_nojit(nojit_dir, position, depth) if nojit_dir is not None else (None, None)
    charts = write_charts(data, run_dir, position, depth, nojit)
    title = f"# Perft benchmark: `{data['commit']}{'-dirty' if data['dirty'] else ''}`, {data['started'][:10]}"
    sections = [
        title,
        headline_sentence(data),
        headline_table(data),
    ]
    if charts:
        sections += [
            f"![Nodes per second at depth {data['settings']['max_depth']} for each engine and position]({SPEED_CHART})",
            f"![Nodes per second by depth, every run shown as a dot]({DEPTH_CHART})",
            f"![Each engine on {position} at depth {depth}, slowest to fastest]({STAIRCASE_CHART})",
        ]
        if nojit is not None:
            sections.append(f"The “tempo · no JIT” bar comes from run `{nojit['run']}`, made with "
                            "`NUMBA_DISABLE_JIT=1`: the every-leaf engine run as plain Python.")
        if nojit_note:
            sections.append(nojit_note)
    sections += [
        correctness_section(data),
        engines_section(data),
        timings_section(data),
        warmup_section(data),
        run_section(data),
        method_section(),
        f"_Regenerate with `python -m ccc26.user.eradcliffe.bench.report {run_dir.name}"
        + (f" --nojit {nojit_dir.name}" if nojit_dir is not None else "")
        + (f" --position {position} --depth {depth}" if (position, depth) != (STAIRCASE_POSITION, STAIRCASE_DEPTH)
           else "")
        + "`._",
    ]
    path = run_dir / REPORT_FILE
    path.write_text("\n\n".join(sections) + "\n")
    return path


def resolve(arg: str | None) -> Path:
    """A run folder from a folder, a results.json, a run name, or the latest run if None."""
    if arg is None:
        runs = sorted(d for d in RESULTS_DIR.glob("*") if (d / RESULTS_FILE).exists())
        if not runs:
            sys.exit(f"No runs in {RESULTS_DIR}")
        return runs[-1]
    path = Path(arg)
    if not path.exists():
        path = RESULTS_DIR / arg
    return path.parent if path.is_file() else path


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a benchmark report from its results.json.")
    parser.add_argument("run", nargs="?", help="Run folder, its results.json, or its name. Default: latest run.")
    parser.add_argument("--nojit", metavar="RUN",
                        help="A run made with NUMBA_DISABLE_JIT=1; adds its every-leaf engine to staircase.png.")
    parser.add_argument("--position", help=f"Staircase position. Default: {STAIRCASE_POSITION}.")
    parser.add_argument("--depth", "-d", type=int, help=f"Staircase depth. Default: {STAIRCASE_DEPTH}.")
    args = parser.parse_args()
    run_dir = resolve(args.run)
    nojit_dir = resolve(args.nojit) if args.nojit else None
    for d in (run_dir, nojit_dir):
        if d is not None and not (d / RESULTS_FILE).exists():
            sys.exit(f"No {RESULTS_FILE} in {d}")
    print(write_report(run_dir, nojit_dir, args.position, args.depth))


if __name__ == "__main__":
    main()
