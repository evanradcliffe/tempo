"""Copy-make and pin-aware legality must agree everywhere.

Run from the root of the winter26 repo:
    python3 -m unittest ccc26.user.eradcliffe.tests.test_legal_modes
    TEMPO_DIFF_GAMES=3000 python3 -m unittest ccc26.user.eradcliffe.tests.test_legal_modes   # the full check

Numba caveat: cache=True only recompiles a function when its own file changes, so
after editing bitboard.py or attacks.py, delete the *.nbi/*.nbc cache files (or set
NUMBA_CACHE_DIR to an empty folder) or these tests may run stale compiled code.

Three layers:
    pinned_pieces on hand-made positions (pins on a file and a diagonal, and three non-pins),
    perft against the published Chess Programming Wiki counts in both modes,
    random games from those positions, comparing both modes and python-chess at every node.
"""

import os
import random
import unittest

import chess
import numpy as np

from ..attacks import pinned_pieces
from ..b import Board, legal_mode
from ..bitboard import MAX_MOVES, U0, WHITE, bit
from ..movegen import LEGAL_COPYMAKE, LEGAL_MODES, LEGAL_PINAWARE, generate_legal, make_move, perft, perft_every_leaf
from ..notation import export_fen, move_to_uci, parse_fen, parse_square

# https://www.chessprogramming.org/Perft_Results, positions 1-6. Counts are kept to
# depths that run in well under a second; the bench and TEMPO_DIFF_GAMES go further.
POSITIONS = [
    ("1 start", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", [20, 400, 8_902, 197_281]),
    ("2 kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", [48, 2_039, 97_862]),
    ("3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", [14, 191, 2_812, 43_238, 674_624]),
    ("4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", [6, 264, 9_467, 422_333]),
    ("5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", [44, 1_486, 62_379]),
    ("6", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", [46, 2_079, 89_890]),
]
GAMES = int(os.environ.get("TEMPO_DIFF_GAMES", "100"))  # per position
PLIES = 40
SEED = 2026


def legal(state: np.ndarray, mode: int) -> list[int]:
    moves = np.empty(MAX_MOVES, dtype=np.int64)
    n = generate_legal(state, moves, mode)
    return sorted(int(m) for m in moves[:n])


def squares(*names: str):
    bb = U0
    for name in names:
        bb |= bit(parse_square(name))
    return bb


class PinnedPieces(unittest.TestCase):
    def check(self, fen: str, expected: list[str]) -> None:
        got = pinned_pieces(parse_fen(fen), WHITE)
        self.assertEqual(got, squares(*expected), fen)

    def test_rook_pins_along_a_file(self):
        self.check("4r1k1/8/8/8/8/8/4B3/4K3 w - - 0 1", ["e2"])

    def test_bishop_pins_along_a_diagonal(self):
        self.check("6k1/8/8/b7/8/8/3N4/4K3 w - - 0 1", ["d2"])

    def test_pawn_pinned_on_a_rank(self):  # perft position 3: b5 sits between Ka5 and rh5
        self.check("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", ["b5"])

    def test_two_own_blockers_is_no_pin(self):
        self.check("4r1k1/8/8/8/8/4N3/4B3/4K3 w - - 0 1", [])

    def test_slider_of_the_wrong_type_is_no_pin(self):  # a bishop can't pin along a file
        self.check("4b1k1/8/8/8/8/8/4B3/4K3 w - - 0 1", [])

    def test_enemy_blocker_is_no_pin(self):
        self.check("4r1k1/8/8/8/8/8/4n3/4K3 w - - 0 1", [])


class PublishedPerft(unittest.TestCase):
    def test_both_modes_match_published_counts(self):
        for name, fen, counts in POSITIONS:
            state = parse_fen(fen)
            for mode_name, mode in LEGAL_MODES.items():
                for depth, expected in enumerate(counts, 1):
                    with self.subTest(position=name, mode=mode_name, depth=depth):
                        self.assertEqual(int(perft(state, depth, mode)), expected)
                        if expected <= 100_000:
                            self.assertEqual(int(perft_every_leaf(state, depth, mode)), expected)


class RandomGames(unittest.TestCase):
    def test_modes_and_python_chess_agree_at_every_node(self):
        rng = random.Random(SEED)
        for name, fen, _ in POSITIONS:
            for game in range(GAMES):
                state, ref = parse_fen(fen), chess.Board(fen)
                for _ in range(PLIES):
                    old, new = legal(state, LEGAL_COPYMAKE), legal(state, LEGAL_PINAWARE)
                    if old != new:
                        self.fail(f"{name} game {game}, {export_fen(state)}: "
                                  f"copymake only {sorted(move_to_uci(m) for m in set(old) - set(new))}, "
                                  f"pinaware only {sorted(move_to_uci(m) for m in set(new) - set(old))}")
                    ours = sorted(move_to_uci(m) for m in old)
                    theirs = sorted(m.uci() for m in ref.legal_moves)
                    if ours != theirs:
                        self.fail(f"{name} game {game}, {export_fen(state)}: "
                                  f"ours only {sorted(set(ours) - set(theirs))}, "
                                  f"python-chess only {sorted(set(theirs) - set(ours))}")
                    if not old:
                        break
                    move = rng.choice(old)
                    ref.push_uci(move_to_uci(move))
                    state = make_move(state, np.int64(move))


class BoardMode(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.pop("TEMPO_LEGAL", None)

    def tearDown(self):
        os.environ.pop("TEMPO_LEGAL", None)
        if self.saved is not None:
            os.environ["TEMPO_LEGAL"] = self.saved

    def test_default_is_copymake(self):
        self.assertEqual(Board().legal, "copymake")

    def test_environment_variable_sets_the_default(self):
        os.environ["TEMPO_LEGAL"] = "pinaware"
        self.assertEqual(Board().legal, "pinaware")

    def test_argument_beats_environment(self):
        os.environ["TEMPO_LEGAL"] = "pinaware"
        self.assertEqual(Board(legal="copymake").legal, "copymake")

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            legal_mode("magic")

    def test_both_modes_give_the_same_moves_through_board(self):
        fen = POSITIONS[1][1]
        self.assertEqual(sorted(Board(fen, legal="copymake").legal_moves),
                         sorted(Board(fen, legal="pinaware").legal_moves))


if __name__ == "__main__":
    unittest.main()
