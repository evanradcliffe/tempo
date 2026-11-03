"""FEN, square names, UCI moves and text rendering.

Plain Python, outside the hot path.
"""

import numpy as np

from .bitboard import (
    BISHOP,
    BLACK,
    BOARD_WIDTH,
    CASTLE_BK,
    CASTLE_BQ,
    CASTLE_WK,
    CASTLE_WQ,
    FILE_A,
    FILE_H,
    KNIGHT,
    META,
    NO_SQ,
    NUM_PIECE_BOARDS,
    NUM_SQUARES,
    QUEEN,
    RANK_1,
    RANK_8,
    ROOK,
    STATE_SIZE,
    WHITE,
    castling_rights,
    ep_square,
    file_of,
    fullmove_number,
    halfmove_clock,
    pack_meta,
    rank_of,
    side_to_move,
    square,
    update_occupancy,
)
from .movegen import (
    move_from,
    move_promo,
    move_to,
)


# --- Constants ---------------------------------------------------------------

PIECE_CHARS = "PNBRQKpnbrqk"
PROMO_CHARS = {KNIGHT: "n", BISHOP: "b", ROOK: "r", QUEEN: "q"}
CASTLE_CHARS = [(CASTLE_WK, "K"), (CASTLE_WQ, "Q"), (CASTLE_BK, "k"), (CASTLE_BQ, "q")]


FILE_NAMES = "abcdefgh"


def square_name(sq: int) -> str:
    return FILE_NAMES[file_of(sq)] + str(rank_of(sq) + 1)


def parse_square(name: str) -> int:
    if len(name) != 2 or name[0] not in FILE_NAMES or not name[1].isdigit():
        raise ValueError(f"bad square: {name!r}")
    f, r = FILE_NAMES.index(name[0]), int(name[1]) - 1
    if not RANK_1 <= r <= RANK_8:
        raise ValueError(f"bad square: {name!r}")
    return int(square(f, r))


def parse_fen(fen: str) -> np.ndarray:
    fields = fen.split()
    if len(fields) < 4:
        raise ValueError(f"FEN needs at least 4 fields: {fen!r}")
    placement, side, castling, ep = fields[:4]
    halfmove = int(fields[4]) if len(fields) > 4 else 0
    fullmove = int(fields[5]) if len(fields) > 5 else 1

    boards = [0] * NUM_PIECE_BOARDS
    ranks = placement.split("/")
    if len(ranks) != BOARD_WIDTH:
        raise ValueError(f"FEN needs {BOARD_WIDTH} ranks: {fen!r}")
    for i, rank_text in enumerate(ranks):  # FEN lists rank 8 first
        rank, f = RANK_8 - i, FILE_A
        for ch in rank_text:
            if ch.isdigit():
                f += int(ch)
            elif ch in PIECE_CHARS:
                if f > FILE_H:
                    raise ValueError(f"rank {rank + 1} too long: {fen!r}")
                boards[PIECE_CHARS.index(ch)] |= 1 << int(square(f, rank))
                f += 1
            else:
                raise ValueError(f"bad piece {ch!r}: {fen!r}")
        if f != BOARD_WIDTH:
            raise ValueError(f"rank {rank + 1} has {f} squares: {fen!r}")

    if side not in ("w", "b"):
        raise ValueError(f"bad side to move {side!r}")
    rights = 0
    if castling != "-":
        for flag, ch in CASTLE_CHARS:
            if ch in castling:
                rights |= flag

    state = np.zeros(STATE_SIZE, dtype=np.uint64)
    state[:NUM_PIECE_BOARDS] = boards
    update_occupancy(state)
    state[META] = pack_meta(
        WHITE if side == "w" else BLACK,
        rights,
        NO_SQ if ep == "-" else parse_square(ep),
        halfmove,
        fullmove,
    )
    return state


def _piece_grid(state: np.ndarray) -> list[str | None]:
    grid: list[str | None] = [None] * NUM_SQUARES
    for i, ch in enumerate(PIECE_CHARS):
        bb = int(state[i])
        for sq in range(NUM_SQUARES):
            if bb >> sq & 1:
                grid[sq] = ch
    return grid


def export_fen(state: np.ndarray) -> str:
    grid = _piece_grid(state)
    rows = []
    for rank in range(RANK_8, RANK_1 - 1, -1):
        row, empty = "", 0
        for f in range(BOARD_WIDTH):
            ch = grid[square(f, rank)]
            if ch is None:
                empty += 1
                continue
            if empty:
                row += str(empty)
                empty = 0
            row += ch
        rows.append(row + (str(empty) if empty else ""))

    rights = int(castling_rights(state))
    castling = "".join(ch for flag, ch in CASTLE_CHARS if rights & flag) or "-"
    ep = int(ep_square(state))
    return " ".join([
        "/".join(rows),
        "w" if side_to_move(state) == WHITE else "b",
        castling,
        "-" if ep == NO_SQ else square_name(ep),
        str(int(halfmove_clock(state))),
        str(int(fullmove_number(state))),
    ])


def render(state: np.ndarray) -> str:
    """Board as text, rank 8 at the top, like python-chess's str(board)."""
    grid = _piece_grid(state)
    return "\n".join(
        " ".join(grid[square(f, rank)] or "." for f in range(BOARD_WIDTH))
        for rank in range(RANK_8, RANK_1 - 1, -1)
    )


def move_to_uci(move: int) -> str:
    promo = int(move_promo(move))
    return square_name(int(move_from(move))) + square_name(int(move_to(move))) + PROMO_CHARS.get(promo, "")
