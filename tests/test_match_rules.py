"""
Unit tests for match rules (Tier 4 #1): out-of-bounds restarts (throw-ins,
corners, goal kicks), fouls, and the offside rule.

A loose ball leaving the field awards a dead-ball restart that only the
entitled team may take (tracked via the ball's last toucher). Won tackles
can be whistled as fouls (holder keeps the ball, fouler booked with a long
cooldown). Passes are never aimed at teammates in an offside position.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src import game_engine
from src.ai import AIController
from src.entities import Ball, Player, Team
from src.game_engine import FOUL_COOLDOWN, GOAL_KICK_DIST, GameEngine


def _quiet_engine():
    """Engine with AI disabled and everyone parked far from the ball."""
    engine = GameEngine()
    engine.team1_ai.update = lambda dt: None
    engine.team2_ai.update = lambda dt: None
    for i, p in enumerate(engine.team1.players + engine.team2.players):
        p.x, p.y = 10000.0 + i * 100, 10000.0
        p.action_cooldown = 0.0
    engine.ball.x, engine.ball.y = 400.0, 300.0
    engine.ball.possession = None
    engine.ball.last_toucher = None
    return engine


class LastToucherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_claiming_a_free_ball_records_the_toucher(self):
        engine = _quiet_engine()
        taker = engine.team1.players[0]
        taker.x, taker.y = engine.ball.x, engine.ball.y

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, taker)
        self.assertIs(engine.ball.last_toucher, taker)

    def test_reset_positions_clears_toucher_and_restart(self):
        engine = _quiet_engine()
        engine.ball.last_toucher = engine.team1.players[0]
        engine.restart_team = engine.team2

        engine.reset_positions()

        self.assertIsNone(engine.ball.last_toucher)
        self.assertIsNone(engine.restart_team)


class ThrowInTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_ball_over_sideline_awards_throw_in_to_other_team(self):
        engine = _quiet_engine()
        engine.ball.last_toucher = engine.team1.players[0]
        engine.ball.x = 400.0
        engine.ball.y = engine.field_y - 5  # over the top sideline
        engine.ball.vy = -100.0

        scorer = engine.handle_ball_boundaries()

        self.assertIsNone(scorer)
        self.assertIs(engine.restart_team, engine.team2)
        self.assertEqual(engine.ball.y, engine.field_y)  # on the line
        self.assertEqual(engine.ball.x, 400.0)
        self.assertEqual((engine.ball.vx, engine.ball.vy), (0, 0))
        self.assertIsNone(engine.ball.possession)

    def test_carried_ball_over_sideline_is_not_a_throw_in(self):
        # A dribbler hugging the line carries the ball glued slightly past
        # it; that must not be whistled out of play.
        engine = _quiet_engine()
        carrier = engine.team1.players[0]
        engine.ball.possession = carrier
        engine.ball.last_toucher = carrier
        engine.ball.y = engine.field_y - 5
        engine.ball.vy = -100.0

        engine.handle_ball_boundaries()

        self.assertIsNone(engine.restart_team)
        self.assertIs(engine.ball.possession, carrier)

    def test_only_entitled_team_can_take_the_restart(self):
        engine = _quiet_engine()
        engine.ball.last_toucher = engine.team1.players[0]
        engine.ball.y = engine.field_y - 5
        engine.handle_ball_boundaries()  # throw-in for team2

        # A team1 player on the ball cannot claim it...
        intruder = engine.team1.players[1]
        intruder.x, intruder.y = engine.ball.x, engine.ball.y
        engine.resolve_possession()
        self.assertIsNone(engine.ball.possession)

        # ...but a team2 player can, which clears the restart lock.
        taker = engine.team2.players[0]
        taker.x, taker.y = engine.ball.x, engine.ball.y
        engine.resolve_possession()
        self.assertIs(engine.ball.possession, taker)
        self.assertIsNone(engine.restart_team)


class GoalLineRestartTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_defender_touch_out_over_own_goal_line_gives_corner(self):
        engine = _quiet_engine()
        # Team 1 defends the left goal; its player put the ball out above
        # the goal mouth: corner for Team 2 at the nearest (top-left) corner.
        engine.ball.last_toucher = engine.team1.players[0]
        engine.ball.x = engine.field_x - 2
        engine.ball.y = engine.field_y + 30  # above the mouth, top half

        scorer = engine.handle_ball_boundaries()

        self.assertIsNone(scorer)
        self.assertIs(engine.restart_team, engine.team2)
        self.assertEqual(engine.ball.x, engine.field_x)
        self.assertEqual(engine.ball.y, engine.field_y)

    def test_corner_goes_to_nearest_corner_bottom_half(self):
        engine = _quiet_engine()
        engine.ball.last_toucher = engine.team1.players[0]
        engine.ball.x = engine.field_x - 2
        engine.ball.y = engine.field_y + engine.field_height - 30  # bottom half

        engine.handle_ball_boundaries()

        self.assertEqual(engine.ball.y, engine.field_y + engine.field_height)

    def test_attacker_touch_out_over_goal_line_gives_goal_kick(self):
        engine = _quiet_engine()
        # Team 2 attacks the left goal: its own touch out means a goal kick
        # for Team 1, placed in front of the goal.
        engine.ball.last_toucher = engine.team2.players[0]
        engine.ball.x = engine.field_x - 2
        engine.ball.y = engine.field_y + 30

        scorer = engine.handle_ball_boundaries()

        self.assertIsNone(scorer)
        self.assertIs(engine.restart_team, engine.team1)
        self.assertEqual(engine.ball.x, engine.field_x + GOAL_KICK_DIST)
        self.assertEqual(engine.ball.y, engine.field_y + engine.field_height / 2)

    def test_goal_in_the_mouth_still_scores_with_a_last_toucher(self):
        engine = _quiet_engine()
        engine.ball.last_toucher = engine.team2.players[0]
        top, bottom = engine.goal_mouth()
        engine.ball.x = engine.field_x - 1
        engine.ball.y = (top + bottom) / 2

        scorer = engine.handle_ball_boundaries()

        self.assertEqual(scorer, "team2")
        self.assertEqual(engine.team2_score, 1)
        self.assertIsNone(engine.restart_team)


class FoulTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _contest(self, engine):
        holder = engine.team1.players[0]
        tackler = engine.team2.players[0]
        holder.x, holder.y = engine.ball.x, engine.ball.y
        tackler.x, tackler.y = engine.ball.x + 5, engine.ball.y
        engine.ball.possession = holder
        return holder, tackler

    def test_foul_keeps_ball_with_holder_and_books_the_fouler(self):
        engine = _quiet_engine()
        holder, tackler = self._contest(engine)

        # First roll wins the tackle, second whistles it as a foul.
        with mock.patch.object(game_engine.random, "random",
                               side_effect=[0.0, 0.0]):
            engine.resolve_possession()

        self.assertIs(engine.ball.possession, holder)
        self.assertEqual(tackler.action_cooldown, FOUL_COOLDOWN)

    def test_clean_tackle_still_wins_the_ball(self):
        engine = _quiet_engine()
        holder, tackler = self._contest(engine)

        with mock.patch.object(game_engine.random, "random",
                               side_effect=[0.0, 0.9]):
            engine.resolve_possession()

        self.assertIs(engine.ball.possession, tackler)
        self.assertIs(engine.ball.last_toucher, tackler)


def _ai_scenario(carrier_xy):
    """Team 1 (attacks right) carrier with the ball at carrier_xy."""
    team = Team("Team 1", (255, 0, 0))
    carrier = Player("T1P1", *carrier_xy, team.color)
    carrier.home_x, carrier.home_y = carrier.x, carrier.y
    team.add_player(carrier)
    opp = Team("Team 2", (0, 0, 255))
    ball = Ball(carrier.x, carrier.y)
    ball.possession = carrier
    ai = AIController(team, opp, ball)
    ai.team_state = "attack"
    ai.active_player = carrier
    return ai, carrier, ball


def _add_player(team, name, x, y):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    team.add_player(p)
    return p


class OffsideTest(unittest.TestCase):
    def _with_back_line(self, ai, keeper_x=729.0, defender_x=600.0):
        _add_player(ai.opponent_team, "T2GK", keeper_x, 300.0)
        _add_player(ai.opponent_team, "T2D", defender_x, 300.0)

    def test_beyond_second_last_opponent_is_offside(self):
        ai, carrier, _ = _ai_scenario((450.0, 300.0))
        self._with_back_line(ai)  # offside line at x=600
        mate = _add_player(ai.team, "T1P2", 650.0, 200.0)
        self.assertTrue(ai._is_offside_position(mate))

    def test_behind_the_offside_line_is_onside(self):
        ai, carrier, _ = _ai_scenario((450.0, 300.0))
        self._with_back_line(ai)
        mate = _add_player(ai.team, "T1P2", 590.0, 200.0)
        self.assertFalse(ai._is_offside_position(mate))

    def test_behind_the_ball_is_onside(self):
        ai, carrier, _ = _ai_scenario((700.0, 300.0))
        self._with_back_line(ai)  # line at 600, but the ball is at 700
        mate = _add_player(ai.team, "T1P2", 650.0, 200.0)
        self.assertFalse(ai._is_offside_position(mate))

    def test_own_half_is_never_offside(self):
        ai, carrier, _ = _ai_scenario((150.0, 300.0))
        # Opponents pressed high: their second-last is inside our half.
        self._with_back_line(ai, keeper_x=350.0, defender_x=300.0)
        mate = _add_player(ai.team, "T1P2", 380.0, 200.0)
        self.assertFalse(ai._is_offside_position(mate))

    def test_pass_target_never_offside(self):
        ai, carrier, _ = _ai_scenario((560.0, 300.0))
        self._with_back_line(ai)  # offside line at x=600
        offside_mate = _add_player(ai.team, "T1P2", 660.0, 250.0)
        self.assertTrue(ai._is_offside_position(offside_mate))

        # The only forward option is offside: no pass.
        self.assertIsNone(ai._best_pass_target(carrier))

        # Bring the defensive line deeper so the mate is now onside: the
        # same teammate becomes a valid target.
        ai.opponent_team.players[1].x = 700.0
        self.assertFalse(ai._is_offside_position(offside_mate))
        self.assertIs(ai._best_pass_target(carrier), offside_mate)


if __name__ == "__main__":
    unittest.main()
