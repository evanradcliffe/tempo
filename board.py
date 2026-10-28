# standard imports
from collections.abc import Iterable

# third-party imports
import chess  # The python-chess library

# local imports
from ...board import AbstractChessBoard


class ChessBoard(AbstractChessBoard):
    """A concrete implementation of AbstractChessBoard using the python-chess library.

    This class serves as a reference wrapper, converting python-chess standard
    board operations and move objects into the common interface required by the
    evaluation framework.
    """

    def __init__(self, fen: str | None = None) -> None:
        """Initializes the wrapper board using python-chess internally.

        Args:
            fen: An optional FEN string to set up the board position.
                Defaults to the standard starting position if None.
        """
        super().__init__(fen)
        # Use python-chess default starting position if no FEN is provided
        if fen is None:
            self._board = chess.Board()
        else:
            self._board = chess.Board(fen)

    def get_legal_moves(self) -> Iterable[chess.Move]:
        """Generates all legal moves for the current board position.

        Returns:
            An iterable collection of chess.Move objects representing
            all strictly legal moves available to the active player.
        """
        return self._board.legal_moves

    def push_move(self, move: chess.Move) -> None:
        """Applies a python-chess move to the board state, advancing the game.

        Args:
            move: The chess.Move object to be executed on the board.
        """
        self._board.push(move)
        # Keep the base class FEN attribute synchronized
        self.fen = self._board.fen()

    def pop_move(self) -> None:
        """Reverts the last executed move, restoring the previous board state."""
        self._board.pop()
        # Keep the base class FEN attribute synchronized
        self.fen = self._board.fen()

    def __str__(self) -> str:
        """Returns a string representation of the board state.

        This is useful for debugging and prints a standard ASCII text grid
        of the current position.
        """
        return str(self._board)
