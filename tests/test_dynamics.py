"""
Unit tests for the game-dynamics rework: player acceleration/momentum,
phase tempo, and long-range shooting.

Movement commands now blend velocity toward the desired vector (momentum)
instead of snapping; defending players track back faster than attacking
players push up; and carriers occasionally let fly from long range with
distance-powered shots that actually reach the goal.
"""

import math
import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src import ai as ai_module
from src.ai import (AIController, ATTACK_TEMPO, DEFENSE_TEMPO,
                    LONG_SHOT_PROB, LONG_SHOT_RANGE, SHOOT_RANGE)
from src.entities import (BALL_FRICTION_PER_SEC, MAX_SHOT_POWER,
                          MOVE_ACCEL_BLEND, Ball, Player, Team)


def _player(x=300.0, y=300.0):
    return Player("P", x, y, (255, 0, 0))


class AccelerationTest(unittest.TestCase):
    def test_first_command_reaches_only_a_fraction_of_speed(self):
        p = _player()
        p.move_towards(p.x + 100, p.y, p.max_speed)
        speed = math.hypot(p.vx, p.vy)
        self.assertAlmostEqual(speed, p.max_speed * MOVE_ACCEL_BLEND)

    def test_repeated_commands_converge_on_full_speed(self):
        p = _player()
        for _ in range(60):
            p.move_towards(p.x + 100, p.y, p.max_speed)
        self.assertAlmostEqual(math.hypot(p.vx, p.vy), p.max_speed, delta=0.5)

    def test_turns_keep_momentum_instead_of_snapping(self):
        p = _player()
        for _ in range(60):
            p.move_towards(p.x + 100, p.y, p.max_speed)  # sprint right
        p.move_towards(p.x, p.y + 100, p.max_speed)  # cut downward

        # One command later the player is still mostly carried rightward:
        # the turn takes several frames instead of flipping instantly.
        self.assertGreater(p.vx, 0.0)
        self.assertGreater(p.vx, p.vy)
        self.assertGreater(p.vy, 0.0)  # but the turn has begun


class PhaseTempoTest(unittest.TestCase):
    def test_defenders_track_back_faster_than_attackers_push_up(self):
        self.assertGreater(DEFENSE_TEMPO, ATTACK_TEMPO)


class LongShotTest(unittest.TestCase):
    def _attack_ai(self, carrier_xy):
        team = Team("Team 1", (255, 0, 0))
        carrier = Player("T1P1", *carrier_xy, team.color)
        team.add_player(carrier)
        opp = Team("Team 2", (0, 0, 255))
        ball = Ball(carrier.x, carrier.y)
        ball.possession = carrier
        ai = AIController(team, opp, ball)
        ai.team_state = "attack"
        ai.active_player = carrier
        return ai, carrier, ball

    def test_long_shot_fires_when_the_roll_hits(self):
        # Between SHOOT_RANGE and LONG_SHOT_RANGE with a favorable roll.
        ai, carrier, ball = self._attack_ai((500.0, 300.0))
        dist = math.hypot(750 - carrier.x, 300 - carrier.y)
        self.assertGreater(dist, SHOOT_RANGE)
        self.assertLess(dist, LONG_SHOT_RANGE)

        with mock.patch.object(ai_module.random, "random", return_value=0.0), \
             mock.patch.object(ai_module.random, "uniform", return_value=0.0):
            ai.execute_attack_behavior(1 / 60)

        self.assertIsNone(ball.possession)  # shot away
        self.assertGreater(ball.vx, 0.0)
        self.assertEqual(ai.team.shots, 1)

    def test_no_long_shot_when_the_roll_misses(self):
        ai, carrier, ball = self._attack_ai((500.0, 300.0))

        with mock.patch.object(ai_module.random, "random",
                               return_value=LONG_SHOT_PROB + 0.01):
            ai.execute_attack_behavior(1 / 60)

        self.assertIs(ball.possession, carrier)
        self.assertEqual(ai.team.shots, 0)

    def test_no_long_shot_beyond_long_range(self):
        ai, carrier, ball = self._attack_ai((300.0, 300.0))
        dist = math.hypot(750 - carrier.x, 300 - carrier.y)
        self.assertGreater(dist, LONG_SHOT_RANGE)

        with mock.patch.object(ai_module.random, "random", return_value=0.0):
            ai.execute_attack_behavior(1 / 60)

        self.assertIs(ball.possession, carrier)

    def test_long_shot_reaches_the_goal_line(self):
        # A 300px shot must arrive at the goal with pace, not die short.
        p = _player(x=450.0, y=300.0)
        ball = Ball(p.x, p.y)
        ball.possession = p

        self.assertTrue(p.shoot(ball, 760.0, 300.0))
        for _ in range(60 * 3):
            ball.update(1 / 60)

        self.assertGreater(ball.x, 750.0)

    def test_shot_power_scales_with_distance_up_to_the_cap(self):
        speeds = []
        for target_x in (420.0, 520.0, 760.0):
            p = _player(x=300.0, y=300.0)
            ball = Ball(p.x, p.y)
            ball.possession = p
            p.shoot(ball, target_x, 300.0)
            speeds.append(math.hypot(ball.vx, ball.vy))

        close, mid, far = speeds
        self.assertGreater(mid, close)  # scaled beyond the base power
        self.assertGreater(far, mid)
        self.assertLessEqual(far, MAX_SHOT_POWER)


if __name__ == "__main__":
    unittest.main()
