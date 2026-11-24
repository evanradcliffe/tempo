"""Build a search benchmark report (README.md + charts) from a saved results.json.

The report is a pure function of the JSON: nothing is re-measured. Formatting, the
fast/noisy flags and the run section are shared with the perft report (bench/report.py).

Run from the root of the winter26 repo:
    python -m ccc26.user.eradcliffe.bench.search.report            # latest search run
    python -m ccc26.user.eradcliffe.bench.search.report <run folder or results.json>

Charts need matplotlib; without it the report is written without them.
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from .. import report as perft
from ..report import (
    FAST_CELL_S, NOISY_SPREAD, REPORT_FILE, RESULTS_FILE, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, best, fmt_rate,
    fmt_time, fmt_x, is_fast, md_table, resolve, short_rate, spread,
)

NODES_CHART = "nodes.png"
TIME_CHART = "time.png"
PRUNING_CHART = "pruning.png"

ENGINE_LABELS = {
    "alphabeta": "tempo · alpha-beta",
    "negamax": "tempo · negamax",
    "python-chess": "python-chess negamax",
}
# Color follows the position (slots 1-3 of the dataviz reference palette, the same
# validated adjacent pairs as the perft charts); line style follows the engine.
POSITION_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
ENGINE_STYLES = {"alphabeta": ("-", "o"), "negamax": ("--", "o"), "python-chess": (":", "s")}
NEUTRAL = "#52514e"

Data = dict[str, Any]


# --- Lookups and checks ------------------------------------------------------


def find(data: Data, position: str, depth: int, engine: str) -> Data | None:
    for row in data["results"]:
        if row["position"] == position and row["depth"] == depth and row["engine"] == engine:
            return row
    return None


def depths(data: Data) -> list[int]:
    return list(range(1, data["settings"]["max_depth"] + 1))


def value(row: Data, key: str) -> Any:
    """A deterministic per-run value (nodes, score, move): the first run's; problems() checks the rest agree."""
    return row[key][0]


def problems(data: Data) -> list[str]:
    """Every failed check; the bench exits with 1 if there is any."""
    out = []
    for row in data["results"]:
        for key in ("nodes", "scores", "moves"):
            if len(set(row[key])) > 1:
                out.append(f"{row['position']} depth {row['depth']}, {row['engine']}: {key} differ between runs: "
                           f"{row[key]}")
    for p in data["positions"]:
        for depth in depths(data):
            ab, nm, pc = (find(data, p["name"], depth, e) for e in ("alphabeta", "negamax", "python-chess"))
            where = f"{p['name']} depth {depth}"
            if ab is None or nm is None:
                out.append(f"{where}: missing alphabeta or negamax results")
                continue
            if value(ab, "scores") != value(nm, "scores"):
                out.append(f"{where}: alpha-beta scores {value(ab, 'scores')}, negamax {value(nm, 'scores')}")
            if value(ab, "nodes") > value(nm, "nodes"):
                out.append(f"{where}: alpha-beta visited {value(ab, 'nodes')} nodes, negamax {value(nm, 'nodes')}")
            if pc is not None and value(pc, "scores") != value(nm, "scores"):
                out.append(f"{where}: python-chess negamax scores {value(pc, 'scores')}, ours {value(nm, 'scores')}")
    ev = data.get("eval")
    if ev is None:
        out.append("no evaluation speed results")
    elif ev["mismatch_count"]:
        out.append(f"evaluate() and the python-chess material count disagree on {ev['mismatch_count']} positions, "
                   f"e.g. {ev['mismatches'][0]}")
    return out


def ratio(data: Data, position: str, depth: int) -> float:
    """Pruning ratio: negamax nodes / alpha-beta nodes."""
    return value(find(data, position, depth, "negamax"), "nodes") / value(find(data, position, depth, "alphabeta"),
                                                                          "nodes")


def rate(data: Data, row: Data) -> float:
    """Nodes per second. python-chess doesn't count nodes; it searches negamax's tree, so that count is used."""
    nodes = value(find(data, row["position"], row["depth"], "negamax"), "nodes")
    return nodes / best(row)


def label(data: Data, engine: str) -> str:
    return next(e["label"] for e in data["engines"] if e["id"] == engine)


def eval_rates(data: Data) -> dict[str, float]:
    ev = data["eval"]
    return {w["id"]: ev["positions"] * w.get("loops", 1) / min(w["seconds"]) for w in ev["ways"]}


def span(xs: list[float]) -> str:
    lo, hi = fmt_x(min(xs)), fmt_x(max(xs))
    return hi if lo == hi else lo[:-1] + "–" + hi


# --- Text --------------------------------------------------------------------


def headline(data: Data) -> str:
    deepest, ref = data["settings"]["max_depth"], data["settings"]["reference_max_depth"]
    names = [p["name"] for p in data["positions"]]
    parts = [f"At depth {deepest}, alpha-beta visits {span([ratio(data, n, deepest) for n in names])} fewer nodes "
             f"than plain negamax and is "
             f"{span([best(find(data, n, deepest, 'negamax')) / best(find(data, n, deepest, 'alphabeta')) for n in names])}"
             " faster, with the same root score."]
    if ref >= 1:
        ups = {e: [best(find(data, n, ref, "python-chess")) / best(find(data, n, ref, e)) for n in names]
               for e in ("alphabeta", "negamax")}
        parts.append(f"At depth {ref}, against the python-chess negamax: alpha-beta {span(ups['alphabeta'])} faster, "
                     f"negamax {span(ups['negamax'])} (the same tree, so this is the compiled-vs-Python gap).")
    if "eval" in data:
        r = eval_rates(data)
        parts.append(f"Evaluation: {fmt_rate(r['tempo-loop'])} compiled, {fmt_rate(r['tempo-call'])} called from "
                     f"Python once per position, {fmt_rate(r['python-chess'])} for the python-chess material count.")
    return " ".join(parts)


def summary(data: Data) -> str:
    found = problems(data)
    status = "all checks pass" if not found else f"{len(found)} check(s) failed"
    return f"{nodes_table(data)}\n\n{headline(data)}\nChecks: {status}."


def nodes_table(data: Data) -> str:
    rows = []
    for p in data["positions"]:
        for depth in depths(data):
            ab, nm, pc = (find(data, p["name"], depth, e) for e in ("alphabeta", "negamax", "python-chess"))
            scores = {value(r, "scores") for r in (ab, nm, pc) if r is not None}
            agree = len(scores) == 1
            rows.append([
                p["name"], str(depth), f"{value(ab, 'nodes'):,}", f"{value(nm, 'nodes'):,}",
                f"{ratio(data, p['name'], depth):.1f}×",
                f"{value(ab, 'scores')}" + (" ✓" if agree else " ❌"),
                "—" if pc is None else str(value(pc, "scores")),
                value(ab, "moves") or "—", value(nm, "moves") or "—",
            ])
    return md_table(["Position", "Depth", "alpha-beta nodes", "negamax nodes", "negamax ÷ alpha-beta",
                     "Root score", "python-chess score", "alpha-beta move", "negamax move"], rows, "lrrrrrrll")


def checks_section(data: Data) -> str:
    found = problems(data)
    verdict = ("Every check passes: alpha-beta and negamax give the same root score in every cell, the python-chess "
               "negamax agrees wherever it ran, alpha-beta never visits more nodes, every engine repeats its own "
               "nodes, score and move on every run, and evaluate() matches the python-chess material count on "
               "every position."
               if not found else "**Failed checks:**\n" + "\n".join(f"- {line}" for line in found))
    return "\n\n".join([
        "## Nodes and scores",
        "Node counts, scores and moves are deterministic, so they are printed exactly (from the first run; every "
        "other run must match). Nodes include the root. The root score is in centipawns for the side to move; "
        "✓ means every engine that searched that cell gave the same score.",
        nodes_table(data),
        verdict,
    ])


def eval_section(data: Data) -> str:
    ev = data["eval"]
    rates = eval_rates(data)
    ref = rates["python-chess"]
    rows = [[w["id"], str(w.get("loops", 1)), fmt_time(min(w["seconds"])), fmt_time(statistics.median(w["seconds"])),
             f"{spread(w):.0%}" + (" (noisy)" if spread(w) > NOISY_SPREAD else ""), fmt_rate(rates[w["id"]]),
             "—" if w["id"] == "python-chess" else fmt_x(rates[w["id"]] / ref), w["description"]] for w in ev["ways"]]
    return "\n\n".join([
        "## Evaluation speed",
        f"{ev['positions']:,} positions: every node of {ev['games_per_position']} seeded random games (seed "
        f"{ev['seed']}, up to {ev['max_plies']} plies) from each position. Each timed run passes over the whole set "
        f"`Passes` times, enough to last at least {fmt_time(ev.get('min_run_s', 0))}, so even the compiled loop is "
        f"well above timer noise; best and median of {ev['repeat']} runs. All three give the same score on every "
        "position"
        + ("." if not ev["mismatch_count"] else f", except **{ev['mismatch_count']} mismatches**."),
        md_table(["Way", "Passes", "Best", "Median", "Spread", "Evals/s", "vs python-chess", "What"], rows,
                 "lrrrrrrl"),
    ])


def timings_section(data: Data) -> str:
    out = [
        "## All timings",
        f"Best, median and slowest of {data['settings']['repeat']} runs per cell. Spread is (slowest − best) / best. "
        "Nodes/s uses the best run; python-chess doesn't count nodes, so its nodes/s uses negamax's count (it "
        f"searches the same tree). Flags: **fast** = best run under {fmt_time(FAST_CELL_S)}, so call overhead and "
        f"timer noise dominate; **noisy** = spread above {NOISY_SPREAD:.0%}. Raw run times are under each table and "
        f"in [{RESULTS_FILE}]({RESULTS_FILE}).",
    ]
    for p in data["positions"]:
        rows, raw = [], []
        for depth in depths(data):
            for e in data["engines"]:
                row = find(data, p["name"], depth, e["id"])
                if row is None:
                    continue
                flags = [f for f, hit in (("fast", is_fast(row)), ("noisy", spread(row) > NOISY_SPREAD)) if hit]
                nodes = value(row, "nodes")
                rows.append([
                    str(depth), e["label"], "—" if nodes is None else f"{nodes:,}",
                    fmt_time(best(row)), fmt_time(statistics.median(row["seconds"])), fmt_time(max(row["seconds"])),
                    f"{spread(row):.0%}", fmt_rate(rate(data, row)), str(value(row, "scores")),
                    value(row, "moves") or "—", ", ".join(flags),
                ])
                raw.append([str(depth), e["label"], ", ".join(f"{s * 1e3:.4g}" for s in row["seconds"])])
        out += [
            f"### {p['name']}",
            f"`{p['fen']}`",
            md_table(["Depth", "Engine", "Nodes", "Best", "Median", "Slowest", "Spread", "Nodes/s", "Score", "Move",
                      "Flags"], rows, "rlrrrrrrrll"),
            "<details><summary>Raw run times, in run order</summary>\n\n"
            + md_table(["Depth", "Engine", "Runs (ms)"], raw, "rll") + "\n\n</details>",
        ]
    return "\n\n".join(out)


def engines_section(data: Data) -> str:
    lines = [f"- **{e['label']}** (depths 1–{min(e['max_depth'], data['settings']['max_depth'])}): {e['description']}"
             for e in data["engines"]]
    return "\n".join(["## Engines", f"All use the {data['settings']['eval_mode']} eval and the leaf rules in "
                      "`search.py`: no legal move is mate or stalemate, a leaf in check with no legal move is mate, "
                      "otherwise the static eval.", *lines])


def warmup_section(data: Data) -> str:
    rows = [[w["position"], ENGINE_LABELS.get(w["engine"], w["engine"]), str(w["depth"]), fmt_time(w["seconds"])]
            for w in data["warmup"]]
    return "\n\n".join([
        "## Warm-up (not counted)",
        "One run per engine and position before any measurement, left out of every other number. For tempo the "
        "first one includes Numba compiling or loading its cache.",
        md_table(["Position", "Engine", "Depth", "Time"], rows, "llrr"),
    ])


def method_section() -> str:
    return "\n".join([
        "## Method",
        "- Each engine's position object is built once per cell, outside the timer. The searches restore it, so "
        "later runs start from the same position.",
        "- Within a cell, engines take turns run by run, so slow drift hits every engine alike.",
        "- The garbage collector is off while timing, as in `timeit`.",
        "- Best run is the headline number because noise only ever adds time.",
        "- Everything on this page is generated from `results.json` by `bench/search/report.py`.",
    ])


# --- Charts ------------------------------------------------------------------


def _engine_handles(plt: Any, engines: list[str], data: Data) -> list[Any]:
    from matplotlib.lines import Line2D

    return [Line2D([], [], color=NEUTRAL, linestyle=ENGINE_STYLES[e][0], marker=ENGINE_STYLES[e][1], markersize=4.5,
                   linewidth=1.5, label=label(data, e)) for e in engines]


def _position_handles(data: Data) -> list[Any]:
    from matplotlib.patches import Patch

    return [Patch(color=POSITION_COLORS[i], label=p["name"]) for i, p in enumerate(data["positions"])]


def _legend_strip(fig: Any, handles: list[Any], note: str | None) -> None:
    """Like the perft report's _bottom, with explicit legend handles."""
    height = fig.get_figheight()
    size, spacing, pad = 7, 1.5, 0.08
    note_h = ((note.count("\n") + 1) * size * spacing / 72 + 2 * pad) if note else pad
    ncol = len(handles) if sum(len(h.get_label()) + 8 for h in handles) <= 110 else 3
    legend_h = math.ceil(len(handles) / ncol) * 8 * 1.8 / 72 + 0.1
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, note_h / height), ncol=ncol, fontsize=8,
               borderaxespad=0, handlelength=3.2)
    strip = (note_h + legend_h) / height
    fig.get_layout_engine().set(rect=(0, strip, 1, 1 - strip))
    if note:
        fig.text(0.01, pad / height, note, ha="left", va="bottom", fontsize=size, color=TEXT_SECONDARY,
                 linespacing=spacing)


def _count_axis(axis: Any) -> None:
    from matplotlib.ticker import FuncFormatter, LogLocator, NullLocator

    axis.set_major_locator(LogLocator(subs=(1,)))
    axis.set_major_formatter(FuncFormatter(lambda v, _: short_rate(v)))
    axis.set_minor_locator(NullLocator())


def _time_axis(axis: Any) -> None:
    from matplotlib.ticker import FuncFormatter, LogLocator, NullLocator

    axis.set_major_locator(LogLocator(subs=(1,)))
    axis.set_major_formatter(FuncFormatter(lambda v, _: fmt_time(v).replace(".0 ", " ")))
    axis.set_minor_locator(NullLocator())


def nodes_chart(data: Data, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    perft._style(plt)
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200, layout="constrained")
    for i, p in enumerate(data["positions"]):
        for engine in ("negamax", "alphabeta"):
            style, marker = ENGINE_STYLES[engine]
            counts = [value(find(data, p["name"], d, engine), "nodes") for d in depths(data)]
            ax.plot(depths(data), counts, linestyle=style, marker=marker, color=POSITION_COLORS[i], linewidth=1.5,
                    markersize=4.5, zorder=3)
    ax.set_yscale("log")
    _count_axis(ax.yaxis)
    ax.set_xticks(depths(data))
    ax.set_xlabel("depth (plies)")
    ax.set_ylabel("nodes visited (log)")
    ax.grid(axis="x", visible=False)
    fig.suptitle("Nodes visited by depth: alpha-beta against plain negamax", x=0.01, ha="left", fontsize=11,
                 fontweight="bold")
    _legend_strip(fig, _position_handles(data) + _engine_handles(plt, ["alphabeta", "negamax"], data),
                  "Node counts are exact and the same on every run. Both searches give the same root score in every "
                  "cell.")
    fig.savefig(path)
    plt.close(fig)


def time_chart(data: Data, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    perft._style(plt)
    positions = data["positions"]
    fig, axes = plt.subplots(1, len(positions), figsize=(8, 3.9), dpi=200, sharey=True, layout="constrained")
    any_fast, shown = False, []
    for i, (ax, p) in enumerate(zip(axes, positions)):
        c = POSITION_COLORS[i]
        for e in data["engines"]:
            rows = [r for d in depths(data) if (r := find(data, p["name"], d, e["id"])) is not None]
            shown += rows
            style, marker = ENGINE_STYLES[e["id"]]
            for row in rows:  # every run as a faint dot
                ax.plot([row["depth"]] * len(row["seconds"]), row["seconds"], marker, markersize=2.5, alpha=0.4,
                        color=c, markerfacecolor="none" if is_fast(row) else c, markeredgewidth=0.7, zorder=2)
            ax.plot([r["depth"] for r in rows], [best(r) for r in rows], linestyle=style, marker=marker, color=c,
                    linewidth=1.5, markersize=4.5, zorder=3)
            fast = [r for r in rows if is_fast(r)]
            any_fast |= bool(fast)
            ax.plot([r["depth"] for r in fast], [best(r) for r in fast], marker, markersize=4.5,
                    markerfacecolor=SURFACE, markeredgecolor=c, markeredgewidth=1.3, zorder=4)
        ax.set_yscale("log")
        _time_axis(ax.yaxis)
        ax.set_xticks(depths(data))
        ax.set_title(p["name"], fontsize=9.5, loc="left", color=TEXT_PRIMARY)
        ax.set_xlabel("depth")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("time per search (log)")
    fig.suptitle("Search time by depth: lines are the best run, dots are every run", x=0.01, ha="left",
                 fontsize=11, fontweight="bold")
    m, v = data["machine"], data["versions"]
    timed = [r for r in shown if not is_fast(r)]
    worst = math.ceil(max(spread(r) for r in timed) * 100) if timed else 0
    note = (f"{m['cpu']} · Python {v['python']}, Numba {v['numba']}, python-chess {v['python_chess']}\n"
            f"commit {data['commit']}{'-dirty' if data['dirty'] else ''} · {data['settings']['repeat']} runs per "
            f"point, spread ≤ {worst}% where the best run is {fmt_time(FAST_CELL_S)} or more")
    if any_fast:
        note += (f"\nHollow markers: best run under {fmt_time(FAST_CELL_S)}, mostly call overhead and timer noise; "
                 "their spread is in the timings tables.")
    _legend_strip(fig, _engine_handles(plt, [e["id"] for e in data["engines"]], data), note)
    fig.savefig(path)
    plt.close(fig)


def pruning_chart(data: Data, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    perft._style(plt)
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200, layout="constrained")
    deepest = depths(data)[-1]
    for i, p in enumerate(data["positions"]):
        ratios = [ratio(data, p["name"], d) for d in depths(data)]
        ax.plot(depths(data), ratios, "-o", color=POSITION_COLORS[i], linewidth=1.5, markersize=4.5, zorder=3)
        ax.annotate(f"{ratios[-1]:.0f}×" if ratios[-1] >= 10 else f"{ratios[-1]:.1f}×", (deepest, ratios[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=TEXT_PRIMARY)
    ax.set_yscale("log")
    from matplotlib.ticker import FuncFormatter, LogLocator, NullLocator

    ax.yaxis.set_major_locator(LogLocator(subs=(1, 2, 5)))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}×"))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_xticks(depths(data))
    ax.set_xlim(depths(data)[0] - 0.2, deepest + 0.45)
    ax.set_xlabel("depth (plies)")
    ax.set_ylabel("negamax nodes ÷ alpha-beta nodes (log)")
    ax.grid(axis="x", visible=False)
    fig.suptitle("Pruning ratio: how many times fewer nodes alpha-beta visits", x=0.01, ha="left", fontsize=11,
                 fontweight="bold")
    _legend_strip(fig, _position_handles(data), "1× means no pruning: at depth 1 every root move is a leaf.")
    fig.savefig(path)
    plt.close(fig)


def write_charts(data: Data, run_dir: Path) -> bool:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("matplotlib not installed; writing the report without charts", file=sys.stderr)
        return False
    nodes_chart(data, run_dir / NODES_CHART)
    time_chart(data, run_dir / TIME_CHART)
    pruning_chart(data, run_dir / PRUNING_CHART)
    return True


# --- Report ------------------------------------------------------------------


def load(run_dir: Path) -> Data:
    return json.loads((run_dir / RESULTS_FILE).read_text())


def write_report(run_dir: Path) -> Path:
    data = load(run_dir)
    charts = write_charts(data, run_dir)
    sections = [f"# Search benchmark: `{data['commit']}{'-dirty' if data['dirty'] else ''}`, {data['started'][:10]}",
                headline(data)]
    if charts:
        sections += [
            f"![Nodes visited by depth, alpha-beta and negamax, per position]({NODES_CHART})",
            f"![Search time by depth for alpha-beta, negamax and the python-chess negamax]({TIME_CHART})",
            f"![Pruning ratio, negamax nodes over alpha-beta nodes, by depth]({PRUNING_CHART})",
        ]
    sections += [
        checks_section(data),
        eval_section(data),
        engines_section(data),
        timings_section(data),
        warmup_section(data),
        perft.run_section(data).replace("timed runs per engine per cell",
                                        f"timed runs per engine per cell, python-chess to depth "
                                        f"{data['settings']['reference_max_depth']}"),
        method_section(),
        f"_Regenerate with `python -m ccc26.user.eradcliffe.bench.search.report {run_dir.name}`._",
    ]
    path = run_dir / REPORT_FILE
    path.write_text("\n\n".join(sections) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a search benchmark report from its results.json.")
    parser.add_argument("run", nargs="?", help="Run folder, its results.json, or its name. Default: latest search run.")
    args = parser.parse_args()
    run_dir = resolve(args.run, kind="search")
    if not (run_dir / RESULTS_FILE).exists():
        sys.exit(f"No {RESULTS_FILE} in {run_dir}")
    print(write_report(run_dir))


if __name__ == "__main__":
    main()
