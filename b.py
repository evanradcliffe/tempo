"""AbstractChessBoard implementation on top of the Numba bitboard engine.

The engine lives in sibling modules, each importing only from the ones above it:
    bitboard  constants, bit tricks, state-array layout and accessors
    attacks   precomputed attack tables and attack detection
    movegen   move encoding, generation, make-move, game end, perft
    notation  FEN, square names, UCI and printing

Set NUMBA_DISABLE_JIT=1 to run the engine as ordinary Python for debugging.
"""

from collections.abc import Iterable

import numpy as np

from ...board import AbstractChessBoard
from .bitboard import MAX_MOVES, STARTING_FEN, WHITE, side_to_move
from .attacks import in_check
from .movegen import generate_legal, is_checkmate, is_stalemate, make_move, perft
from .notation import export_fen, move_to_uci, parse_fen, render


class Move(int):
    """An encoded move that prints as UCI, so perft's divide output can match python-chess."""

    def __str__(self) -> str:
        return move_to_uci(int(self))  # Numba won't type an int subclass

    def __repr__(self) -> str:
        return f"Move({str(self)!r})"


class Board(AbstractChessBoard):
    """Friendly wrapper: UCI strings in and out, numpy state inside."""

    def __init__(self, fen: str | None = None) -> None:
        self._stack: list[np.ndarray] = []
        super().__init__(fen)  # assigns self.fen, which parses it into self.state

    @property
    def fen(self) -> str:
        """FEN of the current position, built on demand so push/pop stay cheap."""
        return export_fen(self.state)

    @fen.setter
    def fen(self, fen: str | None) -> None:
        self.state = parse_fen(STARTING_FEN if fen is None else fen)
        self._stack.clear()

    # --- AbstractChessBoard interface ---

    def get_legal_moves(self) -> Iterable[Move]:
        return [Move(m) for m in self._legal_encoded()]

    def push_move(self, move: Move) -> None:
        self._stack.append(self.state)
        self.state = make_move(self.state, np.int64(move))

    def pop_move(self) -> None:
        self.pop()

    # --- UCI helpers ---

    def _legal_encoded(self) -> np.ndarray:
        moves = np.empty(MAX_MOVES, dtype=np.int64)
        n = generate_legal(self.state, moves)
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
                self._stack.append(self.state)
                self.state = make_move(self.state, m)
                return
        raise ValueError(f"illegal move: {uci!r} in {self.fen}")

    def pop(self) -> None:
        """Undo the last push (copy-make keeps every previous state)."""
        self.state = self._stack.pop()

    def is_check(self) -> bool:
        return bool(in_check(self.state))

    def is_checkmate(self) -> bool:
        return bool(is_checkmate(self.state))

    def is_stalemate(self) -> bool:
        return bool(is_stalemate(self.state))

    def perft(self, depth: int) -> int:
        return int(perft(self.state, depth))

    def __str__(self) -> str:
        return render(self.state)

    def __repr__(self) -> str:
        return f"Board({self.fen!r})"


__all__ = ["Board", "Move"]
