"""In-place XOR make/unmake must behave exactly like copy-make.

Run from the root of the winter26 repo:
    python3 -m unittest ccc26.user.eradcliffe.tests.test_make_modes
    TEMPO_DIFF_GAMES=3000 python3 -m unittest ccc26.user.eradcliffe.tests.test_make_modes   # the full check

Numba caveat: cache=True only recompiles a function when its own file changes, so
after editing bitboard.py or attacks.py, delete the *.nbi/*.nbc cache files (or set
NUMBA_CACHE_DIR to an empty folder) or these tests may run stale compiled code.

Layers:
    every legal move at every node of random games: make_inplace gives the same array as
    make_move, and unmake_inplace restores the original bit for bit,
    generate_legal gives the same moves with either make mode and leaves the state as it was,
    perft against the published counts for every legality x make combination,
    b.Board push/pop in xor mode tracks a copy-mode board through random games and back.
"""

import os
import random
import unittest

import numpy as np
from numba import njit

from ..b import Board, make_mode
from ..bitboard import MAX_MOVES, STATE_SIZE
from ..movegen import (
    LEGAL_MODES,
    MAKE_COPY,
    MAKE_MODES,
    MAKE_XOR,
    generate_legal,
    make_inplace,
    make_move,
    perft,
    perft_every_leaf,
    unmake_inplace,
)
from ..notation import export_fen, move_to_uci, parse_fen
from .test_legal_modes import GAMES, PLIES, POSITIONS, SEED

# Why a move failed, from first_mismatch
MAKE_DIFFERS, UNMAKE_DIFFERS = 1, 2


@njit
def first_mismatch(state, moves, n):
    """(index of the first move whose in-place make or unmake disagrees, which one), or (-1, 0)."""
    work = state.copy()
    for i in range(n):
        expected = make_move(state, moves[i])
        captured, old_meta = make_inplace(work, moves[i])
        for w in range(STATE_SIZE):
            if work[w] != expected[w]:
                return i, MAKE_DIFFERS
        unmake_inplace(work, moves[i], captured, old_meta)
        for w in range(STATE_SIZE):
            if work[w] != state[w]:
                return i, UNMAKE_DIFFERS
    return -1, 0


def legal(state: np.ndarray, mode: int, make: int) -> np.ndarray:
    moves = np.empty(MAX_MOVES, dtype=np.int64)
    n = generate_legal(state, moves, mode, make)
    return moves[:n]


def random_games():
    """Yield (position name, game number, state) at every node of seeded random games."""
    rng = random.Random(SEED)
    for name, fen, _ in POSITIONS:
        for game in range(GAMES):
            state = parse_fen(fen)
            for _ in range(PLIES):
                yield name, game, state
                moves = legal(state, LEGAL_MODES["copymake"], MAKE_COPY)
                if len(moves) == 0:
                    break
                state = make_move(state, moves[rng.randrange(len(moves))])


class InPlaceMatchesCopy(unittest.TestCase):
    def test_every_move_at_every_node(self):
        for name, game, state in random_games():
            moves = legal(state, LEGAL_MODES["copymake"], MAKE_COPY)
            i, why = first_mismatch(state, moves, len(moves))
            if i >= 0:
                what = "make_inplace differs from make_move" if why == MAKE_DIFFERS else "unmake_inplace didn't restore"
                self.fail(f"{name} game {game}, {export_fen(state)}, move {move_to_uci(int(moves[i]))}: {what}")

    def test_generate_legal_same_moves_and_state_untouched(self):
        for name, game, state in random_games():
            for mode_name, mode in LEGAL_MODES.items():
                before = state.copy()
                copy_moves = sorted(legal(state, mode, MAKE_COPY).tolist())
                xor_moves = sorted(legal(state, mode, MAKE_XOR).tolist())
                if copy_moves != xor_moves:
                    self.fail(f"{name} game {game}, {export_fen(state)}, {mode_name}: copy and xor legal moves differ")
                if not np.array_equal(state, before):
                    self.fail(f"{name} game {game}, {export_fen(before)}, {mode_name}: xor legality trials left the state changed")


class PublishedPerft(unittest.TestCase):
    def test_every_combination_matches_published_counts(self):
        for name, fen, counts in POSITIONS:
            state = parse_fen(fen)
            before = state.copy()
            for legal_name, mode in LEGAL_MODES.items():
                for make_name, make in MAKE_MODES.items():
                    for depth, expected in enumerate(counts, 1):
                        with self.subTest(position=name, legal=legal_name, make=make_name, depth=depth):
                            self.assertEqual(int(perft(state, depth, mode, make)), expected)
                            if expected <= 100_000:
                                self.assertEqual(int(perft_every_leaf(state, depth, mode, make)), expected)
                            self.assertTrue(np.array_equal(state, before), "perft left the state changed")


class BoardXor(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.pop("TEMPO_MAKE", None)

    def tearDown(self):
        os.environ.pop("TEMPO_MAKE", None)
        if self.saved is not None:
            os.environ["TEMPO_MAKE"] = self.saved

    def test_default_is_copy(self):
        self.assertEqual(Board().make, "copy")

    def test_environment_variable_sets_the_default(self):
        os.environ["TEMPO_MAKE"] = "xor"
        self.assertEqual(Board().make, "xor")

    def test_argument_beats_environment(self):
        os.environ["TEMPO_MAKE"] = "xor"
        self.assertEqual(Board(make="copy").make, "copy")

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            make_mode("magic")

    def test_push_pop_tracks_copy_mode(self):
        rng = random.Random(SEED)
        for name, fen, _ in POSITIONS:
            for game in range(max(1, GAMES // 10)):
                copy, xor = Board(fen, make="copy"), Board(fen, make="xor")
                array = xor.state
                fens = [copy.fen]
                for _ in range(PLIES):
                    moves = copy.get_legal_moves()
                    self.assertEqual(sorted(map(str, moves)), sorted(map(str, xor.get_legal_moves())), copy.fen)
                    if not moves:
                        break
                    move = rng.choice(moves)
                    copy.push_move(move)
                    xor.push_move(move)
                    self.assertEqual(xor.fen, copy.fen, f"{name} game {game} after {move}")
                    fens.append(copy.fen)
                for expected in reversed(fens[:-1]):
                    xor.pop_move()
                    self.assertEqual(xor.fen, expected, f"{name} game {game} while popping")
                self.assertIs(xor.state, array, "xor mode should keep one state array")


if __name__ == "__main__":
    unittest.main()
