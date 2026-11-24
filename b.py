"""AbstractChessBoard implementation on top of the Numba bitboard engine.

The engine lives in sibling modules, each importing only from the ones above it:
    bitboard  constants, bit tricks, state-array layout and accessors
    attacks   precomputed attack tables and attack detection
    movegen   move encoding, generation, make-move, game end, perft
    notation  FEN, square names, UCI and printing

Set NUMBA_DISABLE_JIT=1 to run the engine as ordinary Python for debugging.
Set TEMPO_LEGAL=copymake|pinaware to pick how Board filters legal moves (default
copymake); see movegen.LEGAL_MODES. Board(legal=...) overrides it per board.
Set TEMPO_MAKE=copy|xor to pick how moves are applied (default copy); see
movegen.MAKE_MODES. Board(make=...) overrides it per board.
"""

import os
from collections.abc import Iterable

import numpy as np

from ...board import AbstractChessBoard
from .bitboard import MAX_MOVES, STARTING_FEN, WHITE, side_to_move
from .attacks import in_check
from .movegen import (
    LEGAL_MODES,
    MAKE_MODES,
    MAKE_XOR,
    generate_legal,
    is_checkmate,
    is_stalemate,
    make_inplace,
    make_move,
    perft,
    unmake_inplace,
)
from .notation import export_fen, move_to_uci, parse_fen, render


class Move(int):
    """An encoded move that prints as UCI, so perft's divide output can match python-chess."""

    def __str__(self) -> str:
        return move_to_uci(int(self))  # Numba won't type an int subclass

    def __repr__(self) -> str:
        return f"Move({str(self)!r})"


DEFAULT_LEGAL = "copymake"
DEFAULT_MAKE = "copy"


def _choose(name: str | None, env: str, default: str, modes: dict[str, int], what: str) -> str:
    name = name or os.environ.get(env) or default
    if name not in modes:
        raise ValueError(f"unknown {what} {name!r}; expected one of {', '.join(modes)}")
    return name


def legal_mode(name: str | None = None) -> str:
    """A legality mode name: `name`, else $TEMPO_LEGAL, else copymake. Raises on unknown names."""
    return _choose(name, "TEMPO_LEGAL", DEFAULT_LEGAL, LEGAL_MODES, "legality mode")


def make_mode(name: str | None = None) -> str:
    """A make mode name: `name`, else $TEMPO_MAKE, else copy. Raises on unknown names."""
    return _choose(name, "TEMPO_MAKE", DEFAULT_MAKE, MAKE_MODES, "make mode")


class Board(AbstractChessBoard):
    """Friendly wrapper: UCI strings in and out, numpy state inside.

    legal: "copymake" or "pinaware" (see movegen.LEGAL_MODES). Defaults to $TEMPO_LEGAL,
    else copymake.
    make: "copy" or "xor" (see movegen.MAKE_MODES). Defaults to $TEMPO_MAKE, else copy.
        copy: every push builds a new state array; pop goes back to the previous array.
        xor:  one state array, changed in place; every push keeps a (move, captured, meta)
              undo record and pop hands it to unmake_inplace. `self.state` is then the
              same array object for the board's whole life, so copy it if you keep it.
    Both are chosen here in Python and passed into the compiled functions.
    """

    def __init__(self, fen: str | None = None, legal: str | None = None, make: str | None = None) -> None:
        self._stack: list[np.ndarray] = []  # copy: earlier state arrays
        self._undo: list[tuple[int, int, int]] = []  # xor: (move, captured, old meta) per push
        self.legal = legal_mode(legal)
        self._mode = LEGAL_MODES[self.legal]
        self.make = make_mode(make)
        self._make = MAKE_MODES[self.make]
        super().__init__(fen)  # assigns self.fen, which parses it into self.state

    @property
    def fen(self) -> str:
        """FEN of the current position, built on demand so push/pop stay cheap."""
        return export_fen(self.state)

    @fen.setter
    def fen(self, fen: str | None) -> None:
        self.state = parse_fen(STARTING_FEN if fen is None else fen)
        self._stack.clear()
        self._undo.clear()

    # --- AbstractChessBoard interface ---

    def get_legal_moves(self) -> Iterable[Move]:
        return [Move(m) for m in self._legal_encoded()]

    def push_move(self, move: Move) -> None:
        self._play(int(move))

    def pop_move(self) -> None:
        self.pop()

    # --- UCI helpers ---

    def _play(self, move: int) -> None:
        if self._make == MAKE_XOR:
            captured, old_meta = make_inplace(self.state, move)
            self._undo.append((move, captured, old_meta))
        else:
            self._stack.append(self.state)
            self.state = make_move(self.state, move)

    def _legal_encoded(self) -> np.ndarray:
        moves = np.empty(MAX_MOVES, dtype=np.int64)
        n = generate_legal(self.state, moves, self._mode, self._make)
        return moves[:n]

    @property
    def legal_moves(self) -> list[str]:
        """Legal moves in UCI notation, e.g. ["e2e4", "g1f3", "e7e8q"]."""
        return [move_to_uci(int(m)) for m in self._legal_encoded()]

    @property
    def turn(self) -> str:
        return "white" if side_to_move(self.state) == WHITE else "black"

    def push(self, uci: str) -> None:
        """Play a move given in UCI notation. Raises ValueError if it's not legal."""
        for m in self._legal_encoded():
            if move_to_uci(int(m)) == uci:
                self._play(int(m))
                return
        raise ValueError(f"illegal move: {uci!r} in {self.fen}")

    def pop(self) -> None:
        """Undo the last push: back to the previous array (copy), or unmake in place (xor)."""
        if self._make == MAKE_XOR:
            move, captured, old_meta = self._undo.pop()
            unmake_inplace(self.state, move, captured, old_meta)
        else:
            self.state = self._stack.pop()

    def is_check(self) -> bool:
        return bool(in_check(self.state))

    def is_checkmate(self) -> bool:
        return bool(is_checkmate(self.state, self._mode, self._make))

    def is_stalemate(self) -> bool:
        return bool(is_stalemate(self.state, self._mode, self._make))

    def perft(self, depth: int) -> int:
        return int(perft(self.state, depth, self._mode, self._make))

    def __str__(self) -> str:
        return render(self.state)

    def __repr__(self) -> str:
        return f"Board({self.fen!r}, legal={self.legal!r}, make={self.make!r})"


__all__ = ["Board", "Move", "legal_mode", "make_mode"]
