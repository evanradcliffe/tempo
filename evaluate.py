"""Static evaluation in centipawns from the side to move's view, compiled with Numba.

The eval is static: no move generation and no terminal detection. Checkmate and
stalemate are the search's job (see search.py).

Modes work like movegen.LEGAL_MODES: EVAL_MODES maps a name to an int that is passed
into the compiled functions as an argument, so a piece-square-table eval can become
mode 1 later without touching the search.
    material  100 / 320 / 330 / 500 / 900 for pawn / knight / bishop / rook / queen, king 0

Evaluator is the harness adapter: an AbstractEvaluator whose evaluate(board) runs the
compiled eval on a b.Board's state array.
"""

import numpy as np
from numba import njit

from ...evaluator import AbstractEvaluator
from .b import Board
from .bitboard import PIECES_PER_COLOR, U0, U1, WHITE, side_to_move

EVAL_MATERIAL = 0
EVAL_MODES = {"material": EVAL_MATERIAL}

# Centipawns by piece type (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING), the course's values
PIECE_VALUES = np.array([100, 320, 330, 500, 900, 0], dtype=np.int64)


@njit(cache=True)
def popcount(bb):
    """Number of set bits. Clears the lowest bit per step, so it costs one step per piece."""
    n = 0
    while bb != U0:
        bb &= bb - U1
        n += 1
    return n


@njit(cache=True)
def material(state):
    """White's material minus Black's, in centipawns."""
    score = 0
    for piece in range(PIECES_PER_COLOR):
        white = popcount(state[piece])
        black = popcount(state[PIECES_PER_COLOR + piece])
        score += PIECE_VALUES[piece] * (white - black)
    return score


@njit(cache=True)
def evaluate(state, mode=EVAL_MATERIAL):
    """Score of `state` for the side to move: positive is good for them. Doesn't change `state`."""
    # Only material so far; a new mode adds a branch on `mode` here.
    score = material(state)
    return score if side_to_move(state) == WHITE else -score


class Evaluator(AbstractEvaluator):
    """The harness's evaluator interface on top of the compiled eval.

    mode: a name from EVAL_MODES. `self.name` keeps the name, `self.mode` the int the
    compiled functions take; search.py reads it to evaluate inside the compiled search.
    """

    def __init__(self, mode: str = "material") -> None:
        if mode not in EVAL_MODES:
            raise ValueError(f"unknown eval mode {mode!r}; expected one of {', '.join(EVAL_MODES)}")
        self.name = mode
        self.mode = EVAL_MODES[mode]

    def evaluate(self, board: Board) -> int:
        return int(evaluate(board.state, self.mode))

    def __repr__(self) -> str:
        return f"Evaluator({self.name!r})"
