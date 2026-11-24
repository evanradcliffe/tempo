"""The compiled negamax / alpha-beta search must find simple tactics and agree with a reference.

Run from the root of the winter26 repo:
    python3 -m unittest ccc26.user.eradcliffe.tests.test_search
    TEMPO_DIFF_GAMES=3000 python3 -m unittest ccc26.user.eradcliffe.tests.test_search   # the full check

Numba caveat: cache=True only recompiles a function when its own file changes, so
after editing bitboard.py, attacks.py, movegen.py or evaluate.py, delete the
*.nbi/*.nbc cache files (or set NUMBA_CACHE_DIR to an empty folder) or these tests
may run stale compiled code.

Layers:
    hand-made tactics (mate in 1 and 2, a hanging queen, a defended pawn) and checkmate
    and stalemate at the root, in both search modes. Every FEN was checked with
    python-chess: legal, and the mate or tactic really exists,
    alpha-beta and plain negamax give the same root score at depths 1-3 on positions
    from random games, and alpha-beta never visits more nodes,
    the root score equals reference_negamax() below, written on python-chess with the
    same material eval and leaf rules, at depth 2 (depth 3 on a few positions),
    the state array is bit-for-bit unchanged after every search,
    the AbstractSearch adapter, skipped while the harness's ccc26.search fails to import.

Scores are compared, not moves: equal-scoring moves are a legitimate tie.
"""

import unittest

import chess
import numpy as np

from ....evaluator.evaluator import CHECKMATE_SCORE, DRAW_SCORE, AbstractEvaluator
from ..b import Board
from ..evaluate import EVAL_MATERIAL, Evaluator
from ..notation import move_to_uci, parse_fen
from ..search import INF, NO_MOVE, SEARCH_ALPHABETA, SEARCH_MODES, SEARCH_NEGAMAX, negamax, search_root
from .test_evaluate import material, random_boards
from .test_legal_modes import GAMES, POSITIONS

MATE_IN_1 = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"  # Ra8#
MATE_IN_2 = "7k/8/8/8/8/8/R7/1R4K1 w - - 0 1"  # e.g. Ra7 Kg8 Rb8#; no mate in 1
HANGING_QUEEN = "4k3/8/8/3q4/8/8/3R4/4K3 w - - 0 1"  # Rxd5, nothing defends d5
DEFENDED_PAWN = "4k3/8/2p5/3p4/8/8/8/3QK3 w - - 0 1"  # Qxd5?? cxd5
CHECKMATED = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"  # fool's mate, White to move
STALEMATED = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"  # Black to move, no legal move, not in check

SEARCH_GAMES = max(1, GAMES // 50)  # random games per start position for the search layers
SAMPLE_EVERY = 4  # plies between sampled positions in each game
REFERENCE_DEPTH_3 = [POSITIONS[0][1], POSITIONS[2][1], POSITIONS[4][1]]  # start, CPW 3, CPW 5: small trees


def run(fen: str, depth: int, search_mode: int = SEARCH_ALPHABETA) -> tuple[int, int, int]:
    """(best move, score, nodes) from search_root, checking the state comes back unchanged."""
    state = parse_fen(fen)
    before = state.copy()
    move, score, nodes = search_root(state, depth, EVAL_MATERIAL, search_mode)
    assert np.array_equal(state, before), f"search_root changed the state: {fen} depth {depth}"
    return int(move), int(score), int(nodes)


def sampled_fens() -> list[tuple[str, str]]:
    """(description, FEN) every SAMPLE_EVERY plies of SEARCH_GAMES random games per position."""
    return [(f"{name} game {game} ply {ply}", board.fen())
            for name, game, ply, board in random_boards(SEARCH_GAMES) if ply % SAMPLE_EVERY == 0]


def reference_negamax(board: chess.Board, depth: int, ply: int = 0) -> int:
    """Plain negamax on python-chess with the same eval and leaf rules as search.py."""
    if depth == 0:
        if board.is_check() and not any(board.legal_moves):
            return -(CHECKMATE_SCORE - ply)
        return material(board)
    moves = list(board.legal_moves)
    if not moves:
        return -(CHECKMATE_SCORE - ply) if board.is_check() else DRAW_SCORE
    best = -INF
    for move in moves:
        board.push(move)
        best = max(best, -reference_negamax(board, depth - 1, ply + 1))
        board.pop()
    return best


def forces_mate_in_1(board: chess.Board) -> bool:
    """After the side to move's move: does every reply allow mate in one?"""
    def mates(b: chess.Board) -> bool:
        for m in list(b.legal_moves):
            b.push(m)
            done = b.is_checkmate()
            b.pop()
            if done:
                return True
        return False

    replies = list(board.legal_moves)
    for reply in replies:
        board.push(reply)
        ok = mates(board)
        board.pop()
        if not ok:
            return False
    return bool(replies)


class Tactics(unittest.TestCase):
    def modes(self):
        for name, mode in SEARCH_MODES.items():
            with self.subTest(search=name):
                yield mode

    def test_mate_in_1_at_depth_1(self):
        for mode in self.modes():
            move, score, _ = run(MATE_IN_1, 1, mode)
            self.assertEqual(score, CHECKMATE_SCORE - 1)
            self.assertEqual(move_to_uci(move), "a1a8")

    def test_mate_in_2_at_depth_3(self):
        for mode in self.modes():
            move, score, _ = run(MATE_IN_2, 3, mode)
            self.assertEqual(score, CHECKMATE_SCORE - 3)
            board = chess.Board(MATE_IN_2)
            board.push_uci(move_to_uci(move))
            self.assertTrue(forces_mate_in_1(board), f"{move_to_uci(move)} doesn't force mate")

    def test_mate_in_2_is_not_seen_at_depth_1(self):
        _, score, _ = run(MATE_IN_2, 1)
        self.assertLess(score, CHECKMATE_SCORE - 3)

    def test_wins_a_hanging_queen_at_depth_1(self):
        for mode in self.modes():
            move, score, _ = run(HANGING_QUEEN, 1, mode)
            self.assertEqual(move_to_uci(move), "d2d5")
            self.assertEqual(score, 500)  # rook against nothing

    def test_takes_a_defended_pawn_at_depth_1_but_not_at_depth_2(self):
        for mode in self.modes():
            move, score, _ = run(DEFENDED_PAWN, 1, mode)
            self.assertEqual((move_to_uci(move), score), ("d1d5", 800))  # the horizon: cxd5 unseen
            move, score, _ = run(DEFENDED_PAWN, 2, mode)
            self.assertNotEqual(move_to_uci(move), "d1d5")
            self.assertEqual(score, 700)  # keeps the queen against two pawns

    def test_checkmate_at_the_root(self):
        for mode in self.modes():
            for depth in (1, 2, 3):
                self.assertEqual(run(CHECKMATED, depth, mode), (NO_MOVE, -CHECKMATE_SCORE, 1))

    def test_stalemate_at_the_root(self):
        for mode in self.modes():
            for depth in (1, 2, 3):
                self.assertEqual(run(STALEMATED, depth, mode), (NO_MOVE, DRAW_SCORE, 1))


class Pruning(unittest.TestCase):
    def test_same_root_score_and_never_more_nodes(self):
        pruned = full = 0
        for where, fen in sampled_fens():
            for depth in (1, 2, 3):
                _, score_ab, nodes_ab = run(fen, depth, SEARCH_ALPHABETA)
                _, score_nm, nodes_nm = run(fen, depth, SEARCH_NEGAMAX)
                if score_ab != score_nm:
                    self.fail(f"{where}, {fen}, depth {depth}: alpha-beta {score_ab}, negamax {score_nm}")
                if nodes_ab > nodes_nm:
                    self.fail(f"{where}, {fen}, depth {depth}: alpha-beta visited {nodes_ab} nodes, "
                              f"negamax {nodes_nm}")
                pruned, full = pruned + nodes_ab, full + nodes_nm
        self.assertLess(pruned, full, "alpha-beta never cut anything")

    def test_negamax_wrapper_matches_the_root_search(self):
        for _, fen, _ in POSITIONS:
            for name, mode in SEARCH_MODES.items():
                state = parse_fen(fen)
                before = state.copy()
                with self.subTest(fen=fen, search=name):
                    self.assertEqual(int(negamax(state, 2, EVAL_MATERIAL, mode)), run(fen, 2, mode)[1])
                    self.assertTrue(np.array_equal(state, before), "negamax changed the state")


class Reference(unittest.TestCase):
    def check(self, where: str, fen: str, depth: int) -> None:
        expected = reference_negamax(chess.Board(fen), depth)
        for name, mode in SEARCH_MODES.items():
            _, score, _ = run(fen, depth, mode)
            if score != expected:
                self.fail(f"{where}, {fen}, depth {depth}, {name}: {score}, python-chess negamax {expected}")

    def test_depth_2_on_random_positions(self):
        for where, fen in sampled_fens():
            self.check(where, fen, 2)

    def test_depth_3_on_a_few_positions(self):
        for fen in REFERENCE_DEPTH_3:
            self.check("published position", fen, 3)

    def test_hand_made_positions(self):
        for fen in (MATE_IN_1, MATE_IN_2, HANGING_QUEEN, DEFENDED_PAWN, CHECKMATED, STALEMATED):
            for depth in (1, 2, 3):
                self.check("hand-made", fen, depth)


class State(unittest.TestCase):
    def test_unchanged_after_a_search(self):  # run() also checks this on every search above
        for _, fen, _ in POSITIONS:
            for mode in SEARCH_MODES.values():
                for depth in (1, 2, 3):
                    state = parse_fen(fen)
                    before = state.copy()
                    search_root(state, depth, EVAL_MATERIAL, mode)
                    self.assertEqual(state.tobytes(), before.tobytes(), f"{fen} depth {depth}")


try:  # the adapter subclasses ccc26.search.AbstractSearch, whose package currently fails to import
    from ....search import SearchLimits
    from ..alphabeta import AlphaBetaSearch
    ADAPTER_ERROR = None
except ImportError as error:
    ADAPTER_ERROR = f"ccc26.search doesn't import yet: {error}"


@unittest.skipIf(ADAPTER_ERROR is not None, ADAPTER_ERROR or "")
class SearchAdapter(unittest.TestCase):
    def test_finds_mate_and_leaves_the_board_as_it_was(self):
        for make in ("copy", "xor"):
            board = Board(MATE_IN_1, make=make)
            result = AlphaBetaSearch().search(board, Evaluator(), SearchLimits(depth=1))
            self.assertEqual(str(result.best_move), "a1a8")
            self.assertEqual(result.score, CHECKMATE_SCORE - 1)
            self.assertEqual(result.depth, 1)
            self.assertEqual(board.fen, MATE_IN_1)

    def test_default_depth_is_3(self):
        result = AlphaBetaSearch().search(Board(MATE_IN_2), Evaluator(), SearchLimits())
        self.assertEqual((result.depth, result.score), (3, CHECKMATE_SCORE - 3))

    def test_no_move_at_checkmate(self):
        result = AlphaBetaSearch().search(Board(CHECKMATED), Evaluator(), SearchLimits(depth=2))
        self.assertIsNone(result.best_move)
        self.assertEqual(result.score, -CHECKMATE_SCORE)

    def test_other_evaluators_are_refused(self):
        class Other(AbstractEvaluator):
            def evaluate(self, board):
                return 0

        with self.assertRaises(TypeError):
            AlphaBetaSearch().search(Board(), Other(), SearchLimits(depth=1))


if __name__ == "__main__":
    unittest.main()
