"""
Unit tests for smarter shooting (Tier 3 #5).

Shots aim just inside the corner away from the opposing keeper, with aim
noise that grows with distance. A shot is only taken when the goal mouth
subtends a wide enough angle from the shooter; from sharp positions the
carrier passes instead, or dribbles toward the middle to open the angle.
"""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src import ai as ai_module
from src.ai import (AIController, GOAL_MOUTH_BOTTOM, GOAL_MOUTH_TOP,
                    MIN_SHOT_ANGLE, PRESSURE_DIST, SHOOT_RANGE,
                    SHOT_CORNER_MARGIN)
from src.entities import Ball, Player, Team

TOP_CORNER = GOAL_MOUTH_TOP + SHOT_CORNER_MARGIN
BOTTOM_CORNER = GOAL_MOUTH_BOTTOM - SHOT_CORNER_MARGIN


def _add_player(team, name, x, y, *, goalkeeper=False):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    if goalkeeper:
        p.is_goalkeeper = True
        p.role = "goalkeeper"
    team.add_player(p)
    return p


def _shooter_scenario(shooter_xy):
    """Team 1 (attacks the right goal at x=750) with the ball on the shooter."""
    team = Team("Team 1", (255, 0, 0))
    shooter = _add_player(team, "T1P1", *shooter_xy)
    opp = Team("Team 2", (0, 0, 255))
    ball = Ball(shooter.x, shooter.y)
    ball.possession = shooter
    ai = AIController(team, opp, ball)
    ai.team_state = "attack"
    ai.active_player = shooter
    return ai, shooter, ball


class ShotAngleTest(unittest.TestCase):
    def test_wide_open_in_front_of_goal(self):
        ai, shooter, _ = _shooter_scenario((600.0, 300.0))
        self.assertGreater(ai._shot_angle(shooter), MIN_SHOT_ANGLE)

    def test_tight_from_sharp_position_near_goal_line(self):
        # In shooting range but well outside the mouth, hugging the goal line.
        ai, shooter, _ = _shooter_scenario((740.0, 160.0))
        self.assertLess(shooter.distance_to(Player("g", 750.0, 300.0, (0, 0, 0))),
                        SHOOT_RANGE)
        self.assertLess(ai._shot_angle(shooter), MIN_SHOT_ANGLE)

    def test_angle_shrinks_with_distance(self):
        ai, near, _ = _shooter_scenario((650.0, 300.0))
        far = _add_player(ai.team, "T1P2", 400.0, 300.0)
        self.assertGreater(ai._shot_angle(near), ai._shot_angle(far))


class ShotTargetTest(unittest.TestCase):
    def _no_noise(self):
        return mock.patch.object(ai_module.random, "uniform", return_value=0.0)

    def test_aims_at_corner_away_from_keeper_top(self):
        ai, shooter, _ = _shooter_scenario((650.0, 300.0))
        # Keeper guarding the top half: shoot at the bottom corner.
        _add_player(ai.opponent_team, "T2GK", 729.0, 250.0, goalkeeper=True)
        with self._no_noise():
            tx, ty = ai._pick_shot_target(shooter)
        self.assertEqual(tx, 750)
        self.assertAlmostEqual(ty, BOTTOM_CORNER)

    def test_aims_at_corner_away_from_keeper_bottom(self):
        ai, shooter, _ = _shooter_scenario((650.0, 300.0))
        _add_player(ai.opponent_team, "T2GK", 729.0, 350.0, goalkeeper=True)
        with self._no_noise():
            _, ty = ai._pick_shot_target(shooter)
        self.assertAlmostEqual(ty, TOP_CORNER)

    def test_aims_at_near_corner_without_defenders(self):
        ai, shooter, _ = _shooter_scenario((650.0, 220.0))
        with self._no_noise():
            _, ty = ai._pick_shot_target(shooter)
        self.assertAlmostEqual(ty, TOP_CORNER)

    def test_aim_noise_grows_with_distance(self):
        bounds = []

        def capture(a, b):
            bounds.append(b)
            return 0.0

        ai, close, _ = _shooter_scenario((700.0, 300.0))
        far = _add_player(ai.team, "T1P2", 605.0, 300.0)
        with mock.patch.object(ai_module.random, "uniform", side_effect=capture):
            ai._pick_shot_target(close)
            ai._pick_shot_target(far)

        close_noise, far_noise = bounds
        self.assertGreater(far_noise, close_noise)


class ShotDecisionTest(unittest.TestCase):
    def test_shoots_at_open_corner_when_angle_is_good(self):
        ai, shooter, ball = _shooter_scenario((650.0, 300.0))
        _add_player(ai.opponent_team, "T2GK", 729.0, 250.0, goalkeeper=True)

        with mock.patch.object(ai_module.random, "uniform", return_value=0.0):
            ai.execute_attack_behavior(1 / 60)

        # Shot fired toward the bottom corner (750, 385): down and to the right.
        self.assertIsNone(ball.possession)
        self.assertGreater(ball.vx, 0.0)
        self.assertGreater(ball.vy, 0.0)
        angle = math.atan2(ball.vy, ball.vx)
        expected = math.atan2(BOTTOM_CORNER - shooter.y, 750 - shooter.x)
        self.assertAlmostEqual(angle, expected, places=5)

    def test_passes_instead_of_shooting_from_tight_angle(self):
        # Sharp position in range, pressed, with an open teammate: offload,
        # don't force a shot from a near-impossible angle.
        ai, shooter, ball = _shooter_scenario((740.0, 160.0))
        _add_player(ai.opponent_team, "T2P1", 750.0, 150.0)  # presser
        mate = _add_player(ai.team, "T1P2", 745.0, 260.0)
        self.assertLess(shooter.distance_to(ai.opponent_team.players[0]),
                        PRESSURE_DIST)

        shooter.shoot = mock.Mock(wraps=shooter.shoot)
        shooter.pass_ball = mock.Mock(wraps=shooter.pass_ball)
        ai.execute_attack_behavior(1 / 60)

        shooter.shoot.assert_not_called()
        shooter.pass_ball.assert_called_once()
        self.assertIs(shooter.pass_ball.call_args.args[1], mate)
        self.assertIsNone(ball.possession)

    def test_dribbles_toward_goal_mouth_from_tight_angle_with_no_pass(self):
        # Sharp position, nobody to pass to: keep the ball and cut toward the
        # middle to open the angle instead of driving into the corner.
        ai, shooter, ball = _shooter_scenario((740.0, 160.0))

        ai.execute_attack_behavior(1 / 60)

        self.assertIs(ball.possession, shooter)
        self.assertGreater(shooter.vy, 0.0)  # steering down toward y=300

    def test_still_shoots_under_pressure_when_angle_is_good(self):
        ai, shooter, ball = _shooter_scenario((650.0, 300.0))
        _add_player(ai.opponent_team, "T2P1", 660.0, 300.0)  # presser

        ai.execute_attack_behavior(1 / 60)

        self.assertIsNone(ball.possession)
        self.assertGreater(ball.vx, 0.0)


if __name__ == "__main__":
    unittest.main()
