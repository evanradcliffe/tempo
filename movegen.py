"""Move encoding, generation, copy-make, game-end detection and perft."""

import numpy as np
from numba import njit

from .bitboard import (
    ALL_CASTLING,
    BISHOP,
    BLACK,
    CASTLE_BK,
    CASTLE_BQ,
    CASTLE_WK,
    CASTLE_WQ,
    FILE_A,
    FILE_B,
    FILE_C,
    FILE_D,
    FILE_E,
    FILE_F,
    FILE_G,
    FILE_H,
    FLAG_CASTLE,
    FLAG_DOUBLE,
    FLAG_EP,
    FLAG_MASK,
    FLAG_NORMAL,
    KING,
    KNIGHT,
    MAX_MOVES,
    META,
    MOVE_FLAG_SHIFT,
    MOVE_PROMO_SHIFT,
    MOVE_TO_SHIFT,
    NO_PROMO,
    NO_SQ,
    NUM_SQUARES,
    OCC_ALL,
    OCC_WHITE,
    ONE_RANK,
    PAWN,
    PIECES_PER_COLOR,
    PROMO_MASK,
    QUEEN,
    RANK_1,
    RANK_2,
    RANK_7,
    RANK_8,
    ROOK,
    SQUARE_MASK,
    U0,
    U1,
    WHITE,
    bit,
    castling_rights,
    ep_square,
    file_of,
    fullmove_number,
    halfmove_clock,
    lsb,
    pack_meta,
    piece_at,
    piece_index,
    rank_of,
    side_to_move,
    square,
    update_occupancy,
)
from .attacks import (
    KING_ATTACKS,
    KNIGHT_ATTACKS,
    PAWN_ATTACKS,
    bishop_attacks,
    in_check,
    is_square_attacked,
    king_square,
    rook_attacks,
)


# --- Castling rights table ------------------------------------------------

# Castling rights that survive a move touching each square. Applied to both
# the from- and to-square, so a rook captured on its home square also clears
# that side's right.
CASTLE_KEEP = np.full(NUM_SQUARES, ALL_CASTLING, dtype=np.int64)
CASTLE_KEEP[square(FILE_A, RANK_1)] &= ~CASTLE_WQ
CASTLE_KEEP[square(FILE_E, RANK_1)] &= ~(CASTLE_WK | CASTLE_WQ)
CASTLE_KEEP[square(FILE_H, RANK_1)] &= ~CASTLE_WK
CASTLE_KEEP[square(FILE_A, RANK_8)] &= ~CASTLE_BQ
CASTLE_KEEP[square(FILE_E, RANK_8)] &= ~(CASTLE_BK | CASTLE_BQ)
CASTLE_KEEP[square(FILE_H, RANK_8)] &= ~CASTLE_BK


# --- Moves -------------------------------------------------------------------


@njit(cache=True)
def encode_move(frm, to, promo, flag):
    return np.int64(frm | (to << MOVE_TO_SHIFT) | (promo << MOVE_PROMO_SHIFT) | (flag << MOVE_FLAG_SHIFT))


@njit(cache=True)
def move_from(move):
    return move & SQUARE_MASK


@njit(cache=True)
def move_to(move):
    return (move >> MOVE_TO_SHIFT) & SQUARE_MASK


@njit(cache=True)
def move_promo(move):
    return (move >> MOVE_PROMO_SHIFT) & PROMO_MASK


@njit(cache=True)
def move_flag(move):
    return (move >> MOVE_FLAG_SHIFT) & FLAG_MASK


@njit(cache=True)
def _add_targets(moves, n, frm, targets):
    while targets != U0:
        to = lsb(targets)
        targets &= targets - U1
        moves[n] = encode_move(frm, to, NO_PROMO, FLAG_NORMAL)
        n += 1
    return n


@njit(cache=True)
def _add_pawn_move(moves, n, frm, to):
    if rank_of(to) == RANK_8 or rank_of(to) == RANK_1:
        for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
            moves[n] = encode_move(frm, to, promo, FLAG_NORMAL)
            n += 1
    else:
        moves[n] = encode_move(frm, to, NO_PROMO, FLAG_NORMAL)
        n += 1
    return n


@njit(cache=True)
def generate_pseudo_legal(state, moves):
    """Fill `moves` with pseudo-legal moves (may leave own king in check); return the count."""
    n = 0
    side = side_to_move(state)
    them = 1 - side
    off = piece_index(side, PAWN)
    own = state[OCC_WHITE + side]
    enemy = state[OCC_WHITE + them]
    occ = state[OCC_ALL]
    ep = ep_square(state)

    # Pawns
    forward = ONE_RANK if side == WHITE else -ONE_RANK
    start_rank = RANK_2 if side == WHITE else RANK_7
    bb = state[off + PAWN]
    while bb != U0:
        frm = lsb(bb)
        bb &= bb - U1
        to = frm + forward
        if 0 <= to < NUM_SQUARES and (occ & bit(to)) == U0:
            n = _add_pawn_move(moves, n, frm, to)
            if rank_of(frm) == start_rank and (occ & bit(to + forward)) == U0:
                moves[n] = encode_move(frm, to + forward, NO_PROMO, FLAG_DOUBLE)
                n += 1
        caps = PAWN_ATTACKS[side, frm] & enemy
        while caps != U0:
            to = lsb(caps)
            caps &= caps - U1
            n = _add_pawn_move(moves, n, frm, to)
        if ep != NO_SQ and (PAWN_ATTACKS[side, frm] & bit(ep)) != U0:
            moves[n] = encode_move(frm, ep, NO_PROMO, FLAG_EP)
            n += 1

    # Knights
    bb = state[off + KNIGHT]
    while bb != U0:
        frm = lsb(bb)
        bb &= bb - U1
        n = _add_targets(moves, n, frm, KNIGHT_ATTACKS[frm] & ~own)

    # Sliders
    bb = state[off + BISHOP]
    while bb != U0:
        frm = lsb(bb)
        bb &= bb - U1
        n = _add_targets(moves, n, frm, bishop_attacks(frm, occ) & ~own)
    bb = state[off + ROOK]
    while bb != U0:
        frm = lsb(bb)
        bb &= bb - U1
        n = _add_targets(moves, n, frm, rook_attacks(frm, occ) & ~own)
    bb = state[off + QUEEN]
    while bb != U0:
        frm = lsb(bb)
        bb &= bb - U1
        n = _add_targets(moves, n, frm, (bishop_attacks(frm, occ) | rook_attacks(frm, occ)) & ~own)

    # King
    bb = state[off + KING]
    while bb != U0:
        frm = lsb(bb)
        bb &= bb - U1
        n = _add_targets(moves, n, frm, KING_ATTACKS[frm] & ~own)

    # Castling: right present, rook home, squares between empty, and the king
    # not in, through or into check. "Into" is also caught by the legal filter,
    # but checking it here keeps the rule in one place.
    rights = castling_rights(state)
    home = RANK_1 if side == WHITE else RANK_8
    king_side = CASTLE_WK if side == WHITE else CASTLE_BK
    queen_side = CASTLE_WQ if side == WHITE else CASTLE_BQ
    e, f, g = square(FILE_E, home), square(FILE_F, home), square(FILE_G, home)
    d, c, b = square(FILE_D, home), square(FILE_C, home), square(FILE_B, home)
    king_home = (state[off + KING] & bit(e)) != U0
    if king_home and (rights & king_side) != 0 and (state[off + ROOK] & bit(square(FILE_H, home))) != U0:
        if (occ & (bit(f) | bit(g))) == U0:
            if not (
                is_square_attacked(state, e, them)
                or is_square_attacked(state, f, them)
                or is_square_attacked(state, g, them)
            ):
                moves[n] = encode_move(e, g, NO_PROMO, FLAG_CASTLE)
                n += 1
    if king_home and (rights & queen_side) != 0 and (state[off + ROOK] & bit(square(FILE_A, home))) != U0:
        if (occ & (bit(b) | bit(c) | bit(d))) == U0:
            if not (
                is_square_attacked(state, e, them)
                or is_square_attacked(state, d, them)
                or is_square_attacked(state, c, them)
            ):
                moves[n] = encode_move(e, c, NO_PROMO, FLAG_CASTLE)
                n += 1

    return n


@njit(cache=True)
def make_move(state, move):
    """Copy-make: return a new state with `move` played. `state` is untouched."""
    new = state.copy()
    frm = move_from(move)
    to = move_to(move)
    promo = move_promo(move)
    flag = move_flag(move)
    side = side_to_move(state)
    them = 1 - side
    from_bb = bit(frm)
    to_bb = bit(to)

    piece = piece_at(state, frm)
    captured = False
    if flag == FLAG_EP:
        # The captured pawn sits behind the target square, not on it
        cap_sq = to - ONE_RANK if side == WHITE else to + ONE_RANK
        new[piece_index(them, PAWN)] &= ~bit(cap_sq)
        captured = True
    else:
        for i in range(piece_index(them, PAWN), piece_index(them, PIECES_PER_COLOR)):
            if (new[i] & to_bb) != U0:
                new[i] &= ~to_bb
                captured = True
                break

    new[piece] &= ~from_bb
    if promo != NO_PROMO:
        new[piece_index(side, promo)] |= to_bb
    else:
        new[piece] |= to_bb

    if flag == FLAG_CASTLE:
        home = rank_of(to)
        if file_of(to) == FILE_G:  # king side: h-rook to f-file
            rook_from, rook_to = square(FILE_H, home), square(FILE_F, home)
        else:  # queen side: a-rook to d-file
            rook_from, rook_to = square(FILE_A, home), square(FILE_D, home)
        new[piece_index(side, ROOK)] ^= bit(rook_from) | bit(rook_to)

    rights = castling_rights(state) & CASTLE_KEEP[frm] & CASTLE_KEEP[to]
    ep = (frm + to) // 2 if flag == FLAG_DOUBLE else NO_SQ
    halfmove = 0 if piece % PIECES_PER_COLOR == PAWN or captured else halfmove_clock(state) + 1
    fullmove = fullmove_number(state) + (1 if side == BLACK else 0)

    update_occupancy(new)
    new[META] = pack_meta(them, rights, ep, halfmove, fullmove)
    return new


@njit(cache=True)
def generate_legal(state, moves):
    """Fill `moves` with legal moves; return the count."""
    pseudo = np.empty(MAX_MOVES, dtype=np.int64)
    count = generate_pseudo_legal(state, pseudo)
    side = side_to_move(state)
    n = 0
    for i in range(count):
        after = make_move(state, pseudo[i])
        # Pins and en passant discovered checks fall out of this for free
        if not is_square_attacked(after, king_square(after, side), 1 - side):
            moves[n] = pseudo[i]
            n += 1
    return n


@njit(cache=True)
def has_legal_move(state):
    pseudo = np.empty(MAX_MOVES, dtype=np.int64)
    count = generate_pseudo_legal(state, pseudo)
    side = side_to_move(state)
    for i in range(count):
        after = make_move(state, pseudo[i])
        if not is_square_attacked(after, king_square(after, side), 1 - side):
            return True
    return False


@njit(cache=True)
def is_checkmate(state):
    return in_check(state) and not has_legal_move(state)


@njit(cache=True)
def is_stalemate(state):
    return not in_check(state) and not has_legal_move(state)


@njit(cache=True)
def perft(state, depth):
    """Count leaf nodes of the legal move tree; the standard move generator test."""
    if depth == 0:
        return 1
    moves = np.empty(MAX_MOVES, dtype=np.int64)
    n = generate_legal(state, moves)
    if depth == 1:
        return n
    total = 0
    for i in range(n):
        total += perft(make_move(state, moves[i]), depth - 1)
    return total
