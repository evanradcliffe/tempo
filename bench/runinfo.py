"""Run metadata shared by the perft and search benchmarks: commit, machine, versions."""

import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import chess
import numba

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"
JIT = not numba.config.DISABLE_JIT


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout.strip()


def commit() -> tuple[str, bool | None]:
    """Short hash, and whether anything but the results folder has uncommitted changes."""
    try:
        sha = git("rev-parse", "--short", "HEAD")
        dirty = git("status", "--porcelain", "--", ".", f":(exclude){RESULTS_DIR.relative_to(REPO)}")
    except (OSError, subprocess.CalledProcessError):
        return "unknown", None
    return sha, bool(dirty)


def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def load_average() -> list[float] | None:
    try:
        return [round(x, 2) for x in os.getloadavg()]
    except OSError:
        return None


def machine() -> dict[str, Any]:
    return {"cpu": cpu_name(), "threads": os.cpu_count(), "platform": platform.platform(),
            "load_average_start": load_average()}


def versions() -> dict[str, str]:
    return {"python": platform.python_version(), "python_chess": chess.__version__, "numba": numba.__version__}


def timer_settings() -> dict[str, Any]:
    clock = time.get_clock_info("perf_counter")
    return {"gc_disabled_while_timing": True, "timer": "time.perf_counter", "timer_resolution_s": clock.resolution}
