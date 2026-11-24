"""Negamax search with alpha-beta pruning, compiled with Numba.

The whole tree is walked on one state array with make_inplace / unmake_inplace, and
legal moves come from generate_legal with pin-aware legality, so there is no Python
and no array copy per node. The state is bit-for-bit as it was when a search returns.

Scores are int64 centipawns from the side to move's view (negamax). Terminal positions
are scored here, not by the eval:
    interior node with no legal move  checkmate if in check, else stalemate (DRAW_SCORE)
    leaf (depth 0)                     checkmate if in check with no legal move, else
                                       the static eval; stalemate at leaves is ignored
The side to move checkmated at ply p scores -(CHECKMATE_SCORE - p), so a nearer mate
scores higher for the winner. No 50-move rule or repetition yet.

Modes are runtime int arguments, like movegen.LEGAL_MODES:
    SEARCH_MODES   negamax (every move searched; the reference) or alphabeta (pruning)
    eval mode      evaluate.EVAL_MODES, passed through to the eval at the leaves
Alpha-beta is fail-soft and starts from the full window (-INF, INF), so its root score
equals plain negamax's, and it visits a subset of negamax's nodes.
"""

import numpy as np
from numba import njit

from ...evaluator.evaluator import CHECKMATE_SCORE, DRAW_SCORE
from .attacks import in_check
from .bitboard import MAX_MOVES
from .evaluate import EVAL_MATERIAL, evaluate
from .movegen import LEGAL_PINAWARE, MAKE_XOR, generate_legal, has_legal_move, make_inplace, unmake_inplace

SEARCH_NEGAMAX = 0
SEARCH_ALPHABETA = 1
SEARCH_MODES = {"negamax": SEARCH_NEGAMAX, "alphabeta": SEARCH_ALPHABETA}

INF = CHECKMATE_SCORE + 1_000  # finite, above every mate score, far from int64 overflow
NO_MOVE = -1  # search_root's move when the root has no legal move (encoded moves are >= 0)

# As with movegen.perft: the public functions keep their defaults for callers and hand
# every argument to the private recursion as a plain int64. A recursive function
# compiled with an omitted default argument segfaults when loaded from the cache.


@njit(cache=True)
def negamax(state, depth, eval_mode=EVAL_MATERIAL, search_mode=SEARCH_ALPHABETA):
    """Score of `state` for the side to move, searched `depth` plies deep."""
    nodes = np.zeros(1, dtype=np.int64)
    return _negamax(state, np.int64(depth), np.int64(-INF), np.int64(INF), np.int64(0), np.int64(eval_mode),
                    np.int64(search_mode), nodes)


@njit(cache=True)
def search_root(state, depth, eval_mode=EVAL_MATERIAL, search_mode=SEARCH_ALPHABETA):
    """(best move, score, nodes visited) for the side to move, searched `depth` plies deep.

    Ties go to the first move in generation order. With no legal move at the root the
    move is NO_MOVE and the score is -CHECKMATE_SCORE or DRAW_SCORE. Depth below 1 is
    searched as 1. Nodes count every position visited, the root included.
    """
    depth = np.int64(max(depth, 1))
    eval_mode, search_mode = np.int64(eval_mode), np.int64(search_mode)
    nodes = np.ones(1, dtype=np.int64)  # the root
    moves = np.empty(MAX_MOVES, dtype=np.int64)
    n = generate_legal(state, moves, LEGAL_PINAWARE, MAKE_XOR)
    if n == 0:
        return np.int64(NO_MOVE), np.int64(-CHECKMATE_SCORE if in_check(state) else DRAW_SCORE), nodes[0]
    best_move, best, alpha = np.int64(NO_MOVE), np.int64(-INF), np.int64(-INF)
    for i in range(n):
        captured, old_meta = make_inplace(state, moves[i])
        score = -_negamax(state, depth - 1, np.int64(-INF), -alpha, np.int64(1), eval_mode, search_mode, nodes)
        unmake_inplace(state, moves[i], captured, old_meta)
        if score > best:  # strictly better, so the first of equal moves stays
            best, best_move = score, moves[i]
            if search_mode == SEARCH_ALPHABETA and best > alpha:
                alpha = best
    return best_move, best, nodes[0]


@njit(cache=True)
def _negamax(state, depth, alpha, beta, ply, eval_mode, search_mode, nodes):
    nodes[0] += 1
    if depth == 0:
        if in_check(state) and not has_legal_move(state, LEGAL_PINAWARE, MAKE_XOR):
            return -(CHECKMATE_SCORE - ply)
        return evaluate(state, eval_mode)
    moves = np.empty(MAX_MOVES, dtype=np.int64)
    n = generate_legal(state, moves, LEGAL_PINAWARE, MAKE_XOR)
    if n == 0:
        return -(CHECKMATE_SCORE - ply) if in_check(state) else np.int64(DRAW_SCORE)
    best = np.int64(-INF)
    for i in range(n):
        captured, old_meta = make_inplace(state, moves[i])
        score = -_negamax(state, depth - 1, -beta, -alpha, ply + 1, eval_mode, search_mode, nodes)
        unmake_inplace(state, moves[i], captured, old_meta)
        if score > best:
            best = score
        if search_mode == SEARCH_ALPHABETA:
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break  # the opponent already has a better option earlier in the tree
    return best
