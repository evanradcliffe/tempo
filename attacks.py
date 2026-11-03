"""Precomputed attack tables and "is this square attacked?" detection."""

import numpy as np
from numba import njit

from .bitboard import (
    BISHOP,
    BOARD_WIDTH,
    KING,
    KNIGHT,
    NUM_SQUARES,
    OCC_ALL,
    PAWN,
    QUEEN,
    ROOK,
    U0,
    file_of,
    lsb,
    msb,
    piece_index,
    rank_of,
    side_to_move,
    square,
)


# --- Precomputed tables ------------------------------------------------------


def _on_board(f: int, r: int) -> bool:
    return 0 <= f < BOARD_WIDTH and 0 <= r < BOARD_WIDTH


def _leaper_table(offsets: list[tuple[int, int]]) -> np.ndarray:
    table = np.zeros(NUM_SQUARES, dtype=np.uint64)
    for sq in range(NUM_SQUARES):
        f, r = int(file_of(sq)), int(rank_of(sq))
        bb = 0
        for df, dr in offsets:
            if _on_board(f + df, r + dr):
                bb |= 1 << int(square(f + df, r + dr))
        table[sq] = bb
    return table


KNIGHT_ATTACKS = _leaper_table([(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)])
KING_ATTACKS = _leaper_table([(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)])
# PAWN_ATTACKS[color, sq]: squares a pawn of `color` on `sq` attacks
PAWN_ATTACKS = np.stack([_leaper_table([(-1, 1), (1, 1)]), _leaper_table([(-1, -1), (1, -1)])])

# Ray directions. "Positive" ones step to higher square indices, so the nearest
# blocker is the lowest set bit; for the others it's the highest.
N, NE, E, SE, S, SW, W, NW = range(8)
_DIRS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]


def _ray_table() -> np.ndarray:
    rays = np.zeros((len(_DIRS), NUM_SQUARES), dtype=np.uint64)
    for d, (df, dr) in enumerate(_DIRS):
        for sq in range(NUM_SQUARES):
            f, r = int(file_of(sq)) + df, int(rank_of(sq)) + dr
            bb = 0
            while _on_board(f, r):
                bb |= 1 << int(square(f, r))
                f, r = f + df, r + dr
            rays[d, sq] = bb
    return rays


RAYS = _ray_table()


# --- Attack generation -------------------------------------------------------


@njit(cache=True)
def ray_attacks(sq, occ, d):
    """Squares a slider on sq attacks in direction d, up to and including the first blocker."""
    ray = RAYS[d, sq]
    blockers = ray & occ
    if blockers != U0:
        positive = d == N or d == NE or d == E or d == NW
        first = lsb(blockers) if positive else msb(blockers)
        ray &= ~RAYS[d, first]
    return ray


@njit(cache=True)
def bishop_attacks(sq, occ):
    return ray_attacks(sq, occ, NE) | ray_attacks(sq, occ, SE) | ray_attacks(sq, occ, SW) | ray_attacks(sq, occ, NW)


@njit(cache=True)
def rook_attacks(sq, occ):
    return ray_attacks(sq, occ, N) | ray_attacks(sq, occ, E) | ray_attacks(sq, occ, S) | ray_attacks(sq, occ, W)


@njit(cache=True)
def is_square_attacked(state, sq, by):
    """Is sq attacked by any piece of color `by`?"""
    off = piece_index(by, PAWN)
    occ = state[OCC_ALL]
    # A pawn of `by` attacks sq iff it stands where a pawn of the other color on sq would attack
    if (PAWN_ATTACKS[1 - by, sq] & state[off + PAWN]) != U0:
        return True
    if (KNIGHT_ATTACKS[sq] & state[off + KNIGHT]) != U0:
        return True
    if (KING_ATTACKS[sq] & state[off + KING]) != U0:
        return True
    if (bishop_attacks(sq, occ) & (state[off + BISHOP] | state[off + QUEEN])) != U0:
        return True
    if (rook_attacks(sq, occ) & (state[off + ROOK] | state[off + QUEEN])) != U0:
        return True
    return False


@njit(cache=True)
def king_square(state, color):
    return lsb(state[piece_index(color, KING)])


@njit(cache=True)
def in_check(state):
    side = side_to_move(state)
    return is_square_attacked(state, king_square(state, side), 1 - side)
