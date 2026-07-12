"""
Unit tests for the kickoff setup (fix: players starting in the wrong half).

At every kickoff (match start, after goals, game reset) each team lines up
entirely inside its own half — formation homes past the halfway line (the
striker's) are clamped back. The kicking-off team's most advanced outfield
player starts on the center spot with the ball and passes to one of its two
closest teammates, chosen at random each kickoff.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src import game_engine
from src.game_engine import (KICKOFF_HALF_MARGIN, KICKOFF_OPPONENT_MARGIN,
                             GameEngine)


class KickoffLineupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_all_players_start_in_their_own_half(self):
        engine = GameEngine()
        center_x = engine.field_x + engine.field_width / 2

        for p in engine.team1.players:
            self.assertLessEqual(p.x, center_x)
        for p in engine.team2.players:
            self.assertGreaterEqual(p.x, center_x)

        # The old bug: both strikers' formation homes sit past the halfway
        # line; at kickoff they must be clamped back into their own halves.
        t1_striker = [p for p in engine.team1.players if p.role == "striker"][0]
        t2_striker = [p for p in engine.team2.players if p.role == "striker"][0]
        self.assertGreater(t1_striker.home_x, center_x)  # home is advanced...
        self.assertLessEqual(t1_striker.x, center_x)  # ...but lineup is not
        self.assertGreaterEqual(t2_striker.x, center_x)

    def test_non_taker_players_keep_the_half_margin(self):
        engine = GameEngine()
        center_x = engine.field_x + engine.field_width / 2
        taker = engine.ball.possession

        for p in engine.team1.players:
            if p is not taker:
                self.assertLessEqual(p.x, center_x - KICKOFF_HALF_MARGIN)

    def test_opposing_team_stays_out_of_the_center_circle(self):
        engine = GameEngine()  # Team 1 kicks off
        center_x = engine.field_x + engine.field_width / 2

        for p in engine.team2.players:
            self.assertGreaterEqual(p.x, center_x + KICKOFF_OPPONENT_MARGIN)

    def test_kickoff_taker_starts_on_the_center_spot_with_the_ball(self):
        engine = GameEngine()
        center_x = engine.field_x + engine.field_width / 2
        center_y = engine.field_y + engine.field_height / 2

        taker = engine.ball.possession
        self.assertIsNotNone(taker)
        self.assertIn(taker, engine.team1.players)  # Team 1 opens the match
        self.assertFalse(taker.is_goalkeeper)
        self.assertEqual((taker.x, taker.y), (center_x, center_y))
        self.assertEqual((engine.ball.x, engine.ball.y), (center_x, center_y))
        self.assertTrue(engine.kickoff_pending)

    def test_conceding_team_takes_the_kickoff_after_a_goal(self):
        engine = GameEngine()
        engine.kickoff_pending = False
        top, bottom = engine.goal_mouth()
        engine.ball.possession = None
        engine.ball.x = engine.field_x + engine.field_width + 1  # right net
        engine.ball.y = (top + bottom) / 2

        scorer = engine.handle_ball_boundaries()

        self.assertEqual(scorer, "team1")
        self.assertIn(engine.ball.possession, engine.team2.players)
        self.assertTrue(engine.kickoff_pending)

    def test_reset_without_kickoff_team_leaves_a_free_ball(self):
        engine = GameEngine()
        engine.reset_positions()
        self.assertIsNone(engine.ball.possession)
        self.assertFalse(engine.kickoff_pending)


class KickoffPassTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_pass_goes_to_one_of_the_two_closest_teammates(self):
        engine = GameEngine()
        taker = engine.ball.possession
        mates = [p for p in engine.team1.players
                 if p is not taker and not p.is_goalkeeper]
        expected_two_closest = set(sorted(mates, key=taker.distance_to)[:2])

        seen = []

        def capture(candidates):
            seen.append(set(candidates))
            return candidates[0]

        with mock.patch.object(game_engine.random, "choice",
                               side_effect=capture):
            engine._perform_kickoff_pass()

        self.assertEqual(seen, [expected_two_closest])
        # The kickoff pass was actually played: ball released and in flight.
        self.assertIsNone(engine.ball.possession)
        self.assertGreater(engine.ball.loose_timer, 0.0)
        self.assertFalse(engine.kickoff_pending)

    def test_receiver_is_rechosen_every_kickoff(self):
        engine = GameEngine()
        calls = []

        def capture(candidates):
            calls.append(list(candidates))
            return candidates[-1]

        with mock.patch.object(game_engine.random, "choice",
                               side_effect=capture):
            engine._perform_kickoff_pass()
            engine.reset_positions(kickoff_team=engine.team2)
            engine._perform_kickoff_pass()

        self.assertEqual(len(calls), 2)  # a fresh random pick per kickoff

    def test_taker_on_cooldown_keeps_the_kickoff_pending(self):
        engine = GameEngine()
        taker = engine.ball.possession
        taker.action_cooldown = 0.5

        engine._perform_kickoff_pass()

        self.assertTrue(engine.kickoff_pending)
        self.assertIs(engine.ball.possession, taker)

        taker.action_cooldown = 0.0
        engine._perform_kickoff_pass()
        self.assertFalse(engine.kickoff_pending)
        self.assertIsNone(engine.ball.possession)


if __name__ == "__main__":
    unittest.main()
