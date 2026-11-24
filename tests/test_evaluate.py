"""The compiled static evaluation must match a material count written here on python-chess.

Run from the root of the winter26 repo:
    python3 -m unittest ccc26.user.eradcliffe.tests.test_evaluate
    TEMPO_DIFF_GAMES=3000 python3 -m unittest ccc26.user.eradcliffe.tests.test_evaluate   # the full check

Numba caveat: cache=True only recompiles a function when its own file changes, so
after editing bitboard.py or attacks.py, delete the *.nbi/*.nbc cache files (or set
NUMBA_CACHE_DIR to an empty folder) or these tests may run stale compiled code.

Layers:
    hand-made positions: the start position is 0, material imbalances score +x with one
    side to move and -x with the other,
    a mirrored position (python-chess Board.mirror(): colors and side to move swapped)
    scores the same,
    a differential against material() below at every node of seeded random games,
    the AbstractEvaluator adapter on a b.Board.

The harness's SimpleMaterialEvaluator is not used as a reference: it calls the
is_white_to_move property as a method.
"""

import random
import unittest
from collections.abc import Iterator

import chess
import numpy as np

from ..b import Board
from ..bitboard import STARTING_FEN
from ..evaluate import EVAL_MATERIAL, EVAL_MODES, Evaluator, evaluate
from ..notation import parse_fen
from .test_legal_modes import GAMES, PLIES, POSITIONS, SEED

VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}

# Piece placement, castling, en passant and clocks without the side to move, and the
# material balance from White's view. Each is checked with White and with Black to
# move; all were checked legal with python-chess both ways.
IMBALANCES = [
    ("4k3/8/8/8/8/8/8/3QK3 {} - - 0 1", 900),  # an extra queen
    ("2b1k3/8/8/8/8/8/8/1N2K3 {} - - 0 1", -10),  # knight against bishop
    ("4k3/pp6/8/8/8/8/8/R3K3 {} - - 0 1", 300),  # rook against two pawns
    ("4k3/8/8/8/8/8/8/QQ2K3 {} - - 0 1", 1800),  # two queens, as after a promotion
    ("r3k3/1q6/8/8/8/8/5PPP/2B1K1N1 {} - - 0 1", -450),  # a mix on both sides
]


def material(board: chess.Board) -> int:
    """Material balance in centipawns from the side to move's view, from python-chess's piece map."""
    score = sum(VALUES[p.piece_type] * (1 if p.color == chess.WHITE else -1) for p in board.piece_map().values())
    return score if board.turn == chess.WHITE else -score


def random_boards(games: int = GAMES) -> Iterator[tuple[str, int, int, chess.Board]]:
    """(position name, game number, ply, board) at every node of seeded random games from POSITIONS."""
    rng = random.Random(SEED)
    for name, fen, _ in POSITIONS:
        for game in range(games):
            board = chess.Board(fen)
            for ply in range(PLIES):
                yield name, game, ply, board.copy(stack=False)
                moves = list(board.legal_moves)
                if not moves:
                    break
                board.push(rng.choice(moves))


def ours(fen: str) -> int:
    state = parse_fen(fen)
    before = state.copy()
    score = int(evaluate(state, EVAL_MATERIAL))
    assert np.array_equal(state, before), f"evaluate changed the state: {fen}"
    return score


class HandMade(unittest.TestCase):
    def test_start_position_is_zero(self):
        self.assertEqual(ours(STARTING_FEN), 0)

    def test_imbalances_with_each_side_to_move(self):
        for template, white_view in IMBALANCES:
            for side, expected in (("w", white_view), ("b", -white_view)):
                fen = template.format(side)
                with self.subTest(fen=fen):
                    self.assertEqual(ours(fen), expected)
                    self.assertEqual(material(chess.Board(fen)), expected)  # the reference agrees too

    def test_mirrored_position_scores_the_same(self):
        fens = [t.format(side) for t, _ in IMBALANCES for side in "wb"] + [fen for _, fen, _ in POSITIONS]
        for fen in fens:
            with self.subTest(fen=fen):
                self.assertEqual(ours(chess.Board(fen).mirror().fen()), ours(fen))


class RandomGames(unittest.TestCase):
    def test_matches_material_count_and_mirror_at_every_node(self):
        for name, game, ply, board in random_boards():
            fen = board.fen()
            got, expected = ours(fen), material(board)
            if got != expected:
                self.fail(f"{name} game {game} ply {ply}, {fen}: evaluate {got}, material count {expected}")
            mirrored = ours(board.mirror().fen())
            if mirrored != got:
                self.fail(f"{name} game {game} ply {ply}, {fen}: {got}, but {mirrored} mirrored")


class EvaluatorAdapter(unittest.TestCase):
    def test_scores_a_board_from_the_side_to_move(self):
        for template, white_view in IMBALANCES:
            for side, expected in (("w", white_view), ("b", -white_view)):
                for make in ("copy", "xor"):
                    board = Board(template.format(side), make=make)
                    with self.subTest(fen=board.fen, make=make):
                        self.assertEqual(Evaluator().evaluate(board), expected)

    def test_returns_a_plain_int(self):
        self.assertIs(type(Evaluator().evaluate(Board())), int)

    def test_follows_the_board_through_push_and_pop(self):
        board = Board("4k3/8/8/3q4/8/8/3R4/4K3 w - - 0 1")
        evaluator = Evaluator()
        self.assertEqual(evaluator.evaluate(board), -400)
        board.push("d2d5")  # rook takes the queen; Black to move, down a rook
        self.assertEqual(evaluator.evaluate(board), -500)
        board.pop()
        self.assertEqual(evaluator.evaluate(board), -400)

    def test_every_mode_is_known_and_unknown_modes_raise(self):
        for name, mode in EVAL_MODES.items():
            self.assertEqual(Evaluator(name).mode, mode)
        with self.assertRaises(ValueError):
            Evaluator("magic")


if __name__ == "__main__":
    unittest.main()
