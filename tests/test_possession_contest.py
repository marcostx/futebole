"""
Unit tests for central possession resolution (Tier 1 fix #3).

Verifies the fair, order-independent contest that replaced the old per-AI
"last writer wins" possession grabs:
- a free ball goes to the closest eligible (in-range, off-cooldown) player
- a player on cooldown (e.g. just kicked) cannot instantly reclaim the ball
- the holder keeps the ball against teammates and only loses to an opponent
  that wins a probabilistic tackle
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src import game_engine
from src.game_engine import GameEngine


class PossessionContestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _engine(self):
        engine = GameEngine()
        engine.team1_ai.update = lambda dt: None
        engine.team2_ai.update = lambda dt: None
        # Park everyone far from the ball and off cooldown by default.
        for i, p in enumerate(engine.team1.players + engine.team2.players):
            p.x = 10000.0 + i * 100
            p.y = 10000.0
            p.action_cooldown = 0.0
        engine.ball.x, engine.ball.y = 400.0, 300.0
        engine.ball.possession = None
        return engine

    def _place_on_ball(self, engine, player):
        player.x, player.y = engine.ball.x, engine.ball.y

    def test_free_ball_goes_to_closest_eligible_player(self):
        engine = self._engine()
        near = engine.team1.players[0]
        self._place_on_ball(engine, near)

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, near)

    def test_free_ball_prefers_closer_of_two(self):
        engine = self._engine()
        closer = engine.team1.players[0]
        farther = engine.team2.players[0]
        closer.x, closer.y = engine.ball.x + 3, engine.ball.y
        farther.x, farther.y = engine.ball.x + 10, engine.ball.y

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, closer)

    def test_player_on_cooldown_cannot_gain_free_ball(self):
        engine = self._engine()
        near = engine.team1.players[0]
        self._place_on_ball(engine, near)
        near.action_cooldown = 0.5  # e.g. just kicked

        engine.resolve_possession()

        self.assertIsNone(engine.ball.possession)

    def test_eligible_player_wins_over_closer_cooldown_player(self):
        engine = self._engine()
        on_cd = engine.team1.players[0]
        eligible = engine.team2.players[0]
        on_cd.x, on_cd.y = engine.ball.x + 2, engine.ball.y
        on_cd.action_cooldown = 0.5
        eligible.x, eligible.y = engine.ball.x + 8, engine.ball.y

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, eligible)

    def test_holder_keeps_against_teammate(self):
        engine = self._engine()
        holder = engine.team1.players[0]
        mate = engine.team1.players[1]
        self._place_on_ball(engine, holder)  # holder is actually on the ball
        engine.ball.possession = holder
        self._place_on_ball(engine, mate)  # teammate right on the ball

        # Even if the tackle RNG "succeeds", teammates never steal.
        with mock.patch.object(game_engine.random, "random", return_value=0.0):
            engine.resolve_possession()

        self.assertIs(engine.ball.possession, holder)

    def test_opponent_wins_tackle_when_roll_succeeds(self):
        engine = self._engine()
        holder = engine.team1.players[0]
        opponent = engine.team2.players[0]
        self._place_on_ball(engine, holder)  # holder is actually on the ball
        engine.ball.possession = holder
        self._place_on_ball(engine, opponent)  # opponent contests at the ball

        with mock.patch.object(game_engine.random, "random", return_value=0.0):
            engine.resolve_possession()

        self.assertIs(engine.ball.possession, opponent)

    def test_opponent_fails_tackle_when_roll_fails(self):
        engine = self._engine()
        holder = engine.team1.players[0]
        opponent = engine.team2.players[0]
        self._place_on_ball(engine, holder)  # holder is actually on the ball
        engine.ball.possession = holder
        self._place_on_ball(engine, opponent)  # opponent contests at the ball

        with mock.patch.object(game_engine.random, "random", return_value=1.0):
            engine.resolve_possession()

        self.assertIs(engine.ball.possession, holder)

    def test_holder_keeps_when_uncontested(self):
        engine = self._engine()
        holder = engine.team1.players[0]
        self._place_on_ball(engine, holder)  # holder is on the ball
        engine.ball.possession = holder  # everyone else is far away

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, holder)

    def test_stale_out_of_range_holder_is_freed(self):
        # A recorded holder that is nowhere near the ball must lose it, so the
        # ball isn't teleported back to a stale possessor by carry_ball().
        engine = self._engine()
        holder = engine.team1.players[0]  # left parked far away by _engine()
        engine.ball.possession = holder

        engine.resolve_possession()

        self.assertIsNone(engine.ball.possession)


if __name__ == "__main__":
    unittest.main()
