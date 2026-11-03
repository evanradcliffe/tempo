"""Bitboard representation: constants, bit tricks and state-array helpers.

This module, attacks and movegen are plain numpy on uint64 and compiled with
Numba. Set NUMBA_DISABLE_JIT=1 to run them as ordinary Python for debugging.
The conventions below hold for all of them.

Conventions
-----------
Squares: a1 = 0, b1 = 1, ..., h1 = 7, a2 = 8, ..., h8 = 63 (file + 8 * rank).

State: one uint64[16] array.
    [0..5]   white P N B R Q K bitboards
    [6..11]  black P N B R Q K bitboards
    [12]     all white pieces
    [13]     all black pieces
    [14]     all pieces
    [15]     meta, packed as:
        bit  0       side to move (0 white, 1 black)
        bits 1-4     castling rights (K=1, Q=2, k=4, q=8)
        bits 5-11    en passant target square (64 = none)
        bits 12-27   halfmove clock
        bits 28-43   fullmove number

Moves: one int64, packed as
    bits 0-5 from, bits 6-11 to, bits 12-14 promotion piece type (0 = none),
    bits 15-16 flag (normal, double push, en passant, castle).

Numba gotcha: mixing uint64 with signed ints silently gives float64, so every
bitboard operation uses the uint64 constants below (U0, U1, ...) and never a
bare Python int.
"""

import numpy as np
from numba import njit


# --- Conventions -------------------------------------------------------------

WHITE, BLACK = 0, 1
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(6)
PIECES_PER_COLOR = 6

# Board geometry: square = file + BOARD_WIDTH * rank
BOARD_WIDTH = 8
NUM_SQUARES = BOARD_WIDTH * BOARD_WIDTH
FILE_A, FILE_B, FILE_C, FILE_D, FILE_E, FILE_F, FILE_G, FILE_H = range(BOARD_WIDTH)
RANK_1, RANK_2, RANK_3, RANK_4, RANK_5, RANK_6, RANK_7, RANK_8 = range(BOARD_WIDTH)
NO_SQ = NUM_SQUARES  # "no square", e.g. no en passant target
# Moving one rank up or down the board changes the square index by a full row
ONE_RANK = BOARD_WIDTH

# State array layout
NUM_PIECE_BOARDS = 2 * PIECES_PER_COLOR  # [0..5] white, [6..11] black
OCC_WHITE, OCC_BLACK, OCC_ALL, META = range(NUM_PIECE_BOARDS, NUM_PIECE_BOARDS + 4)
STATE_SIZE = META + 1

CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ = 1, 2, 4, 8
ALL_CASTLING = CASTLE_WK | CASTLE_WQ | CASTLE_BK | CASTLE_BQ

FLAG_NORMAL, FLAG_DOUBLE, FLAG_EP, FLAG_CASTLE = 0, 1, 2, 3
NO_PIECE = -1  # piece_at() result for an empty square
NO_PROMO = 0  # PAWN is never a promotion target, so its value can mean "none"

MAX_MOVES = 256  # most legal moves in any position is 218

# Move layout (int64): from | to | promotion piece | flag, each in its own bit field.
# A field's shift is the sum of the widths before it; its mask is width-many 1 bits.
SQUARE_BITS = 6  # 2**6 = 64 squares
PROMO_BITS = 3  # piece types 0..5
FLAG_BITS = 2  # 4 flags
MOVE_TO_SHIFT = SQUARE_BITS
MOVE_PROMO_SHIFT = MOVE_TO_SHIFT + SQUARE_BITS
MOVE_FLAG_SHIFT = MOVE_PROMO_SHIFT + PROMO_BITS
SQUARE_MASK = (1 << SQUARE_BITS) - 1
PROMO_MASK = (1 << PROMO_BITS) - 1
FLAG_MASK = (1 << FLAG_BITS) - 1

# Meta layout (uint64): side | castling | en passant square | halfmove | fullmove.
# Kept as np.uint64 because they're combined with the uint64 meta word (see gotcha above).
SIDE_BITS = 1
CASTLE_BITS = 4  # one per right
EP_BITS = 7  # squares 0..63 plus NO_SQ = 64
CLOCK_BITS = 16
CASTLE_SHIFT = np.uint64(SIDE_BITS)
EP_SHIFT = np.uint64(SIDE_BITS + CASTLE_BITS)
HALF_SHIFT = np.uint64(SIDE_BITS + CASTLE_BITS + EP_BITS)
FULL_SHIFT = np.uint64(SIDE_BITS + CASTLE_BITS + EP_BITS + CLOCK_BITS)
SIDE_MASK = np.uint64((1 << SIDE_BITS) - 1)
CASTLE_MASK = np.uint64((1 << CASTLE_BITS) - 1)
EP_MASK = np.uint64((1 << EP_BITS) - 1)
CLOCK_MASK = np.uint64((1 << CLOCK_BITS) - 1)

U0 = np.uint64(0)
U1 = np.uint64(1)
# Masks and shifts for lsb/msb, which binary-search a 64-bit word by halving it:
# 32 bits, then 16, 8, 4, 2, 1.
M32 = np.uint64(0xFFFFFFFF)
M16 = np.uint64(0xFFFF)
M8 = np.uint64(0xFF)
M4 = np.uint64(0xF)
M2 = np.uint64(0x3)
S32, S16, S8, S4, S2, S1 = (np.uint64(s) for s in (32, 16, 8, 4, 2, 1))

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


# --- Geometry helpers --------------------------------------------------------


@njit(cache=True)
def square(file, rank):
    return file + BOARD_WIDTH * rank


@njit(cache=True)
def file_of(sq):
    return sq % BOARD_WIDTH


@njit(cache=True)
def rank_of(sq):
    return sq // BOARD_WIDTH


@njit(cache=True)
def piece_index(color, piece):
    """Index of the (color, piece) bitboard in the state array."""
    return color * PIECES_PER_COLOR + piece


# --- Bit helpers -------------------------------------------------------------


@njit(cache=True)
def bit(sq):
    return U1 << np.uint64(sq)


@njit(cache=True)
def lsb(bb):
    """Index of the lowest set bit. bb must be non-zero."""
    n = 0
    if (bb & M32) == U0:
        n += 32
        bb = bb >> S32
    if (bb & M16) == U0:
        n += 16
        bb = bb >> S16
    if (bb & M8) == U0:
        n += 8
        bb = bb >> S8
    if (bb & M4) == U0:
        n += 4
        bb = bb >> S4
    if (bb & M2) == U0:
        n += 2
        bb = bb >> S2
    if (bb & U1) == U0:
        n += 1
    return n


@njit(cache=True)
def msb(bb):
    """Index of the highest set bit. bb must be non-zero."""
    n = 0
    if (bb >> S32) != U0:
        n += 32
        bb = bb >> S32
    if (bb >> S16) != U0:
        n += 16
        bb = bb >> S16
    if (bb >> S8) != U0:
        n += 8
        bb = bb >> S8
    if (bb >> S4) != U0:
        n += 4
        bb = bb >> S4
    if (bb >> S2) != U0:
        n += 2
        bb = bb >> S2
    if (bb >> S1) != U0:
        n += 1
    return n


# --- Meta field --------------------------------------------------------------


@njit(cache=True)
def pack_meta(side, castling, ep, halfmove, fullmove):
    return (
        np.uint64(side)
        | (np.uint64(castling) << CASTLE_SHIFT)
        | (np.uint64(ep) << EP_SHIFT)
        | (np.uint64(halfmove) << HALF_SHIFT)
        | (np.uint64(fullmove) << FULL_SHIFT)
    )


@njit(cache=True)
def side_to_move(state):
    return np.int64(state[META] & SIDE_MASK)


@njit(cache=True)
def castling_rights(state):
    return np.int64((state[META] >> CASTLE_SHIFT) & CASTLE_MASK)


@njit(cache=True)
def ep_square(state):
    return np.int64((state[META] >> EP_SHIFT) & EP_MASK)


@njit(cache=True)
def halfmove_clock(state):
    return np.int64((state[META] >> HALF_SHIFT) & CLOCK_MASK)


@njit(cache=True)
def fullmove_number(state):
    return np.int64((state[META] >> FULL_SHIFT) & CLOCK_MASK)


@njit(cache=True)
def update_occupancy(state):
    white = U0
    black = U0
    for piece in range(PIECES_PER_COLOR):
        white |= state[piece_index(WHITE, piece)]
        black |= state[piece_index(BLACK, piece)]
    state[OCC_WHITE] = white
    state[OCC_BLACK] = black
    state[OCC_ALL] = white | black


@njit(cache=True)
def piece_at(state, sq):
    """Bitboard index (0..11) of the piece on sq, or -1 if empty."""
    b = bit(sq)
    for i in range(NUM_PIECE_BOARDS):
        if (state[i] & b) != U0:
            return i
    return NO_PIECE
