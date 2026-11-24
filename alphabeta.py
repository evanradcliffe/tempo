"""The harness's AbstractSearch on top of the compiled search in search.py.

In its own module because it subclasses ccc26.search.AbstractSearch, and the harness's
ccc26.search package doesn't import yet; nothing else in this repo imports this file,
so that can't break the board, the eval or the compiled search.
"""

import time
from collections.abc import Callable
from typing import Any

from ...evaluator import AbstractEvaluator
from ...search import AbstractSearch, SearchLimits, SearchResult
from .b import Board, Move
from .evaluate import Evaluator
from .search import NO_MOVE, SEARCH_MODES, search_root

DEFAULT_DEPTH = 3


class AlphaBetaSearch(AbstractSearch):
    """Fixed-depth negamax, with alpha-beta pruning unless mode="negamax".

    Uses limits.depth (default 3); the other limits are ignored for now. The search
    runs entirely in compiled code, so stop() can't interrupt it: it takes effect
    from the next search.
    """

    def __init__(self, mode: str = "alphabeta") -> None:
        super().__init__()
        if mode not in SEARCH_MODES:
            raise ValueError(f"unknown search mode {mode!r}; expected one of {', '.join(SEARCH_MODES)}")
        self.name = mode
        self.mode = SEARCH_MODES[mode]

    def search(
        self,
        board: Board,
        evaluator: AbstractEvaluator,
        limits: SearchLimits,
        info_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> SearchResult:
        if not isinstance(evaluator, Evaluator):
            raise TypeError(f"AlphaBetaSearch needs an eradcliffe Evaluator to run compiled, got {evaluator!r}")
        if not isinstance(board, Board):
            raise TypeError(f"AlphaBetaSearch needs an eradcliffe b.Board, got {type(board).__name__}")
        self.is_stopped = False
        depth = max(1, DEFAULT_DEPTH if limits.depth is None else limits.depth)
        start = time.perf_counter()
        move, score, nodes = search_root(board.state, depth, evaluator.mode, self.mode)  # restores board.state
        elapsed = time.perf_counter() - start
        best = None if move == NO_MOVE else Move(int(move))
        result = SearchResult(best_move=best, score=int(score), depth=depth, nodes=int(nodes),
                              pv=[] if best is None else [best], time_elapsed=elapsed)
        if info_callback is not None:
            info_callback({"depth": depth, "score": result.score, "nodes": result.nodes, "pv": result.pv,
                           "time": elapsed})
        return result
