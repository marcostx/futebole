"""
Unit tests for pass mechanics: the quick turn toward the receiver and
distance-scaled (long) passes.

When passing, the carrier instantly turns to face the receiver and brings
the carried ball to that side, so the ball can be played backward/sideways
while dribbling another way. Kick power is sized to the pass distance (soft
taps stay soft, long balls are driven), and the AI considers forward
teammates beyond short range when they are clearly open.
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src.ai import (AIController, LONG_PASS_DIST, LONG_PASS_MIN_OPENNESS,
                    MAX_PASS_DIST)
from src.entities import (BALL_MAX_SPEED, PASS_POWER_MIN, Ball, Player, Team)


def _carrier_with_ball(x=300.0, y=300.0):
    team = Team("Team 1", (255, 0, 0))
    carrier = Player("T1P1", x, y, team.color)
    carrier.home_x, carrier.home_y = x, y
    team.add_player(carrier)
    ball = Ball(x, y)
    ball.possession = carrier
    return team, carrier, ball


def _add_player(team, name, x, y):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    team.add_player(p)
    return p


class QuickTurnTest(unittest.TestCase):
    def test_carrier_turns_to_face_a_backward_receiver(self):
        team, carrier, ball = _carrier_with_ball()
        # Dribbling right: facing +x, ball glued ahead on the right.
        carrier.facing_x, carrier.facing_y = 1.0, 0.0
        carrier.carry_ball(ball)
        self.assertGreater(ball.x, carrier.x)

        mate = _add_player(team, "T1P2", carrier.x - 100, carrier.y)
        self.assertTrue(carrier.pass_ball(ball, mate))

        # Turned to face the receiver, and the ball was released from that
        # side, travelling backward.
        self.assertAlmostEqual(carrier.facing_x, -1.0)
        self.assertAlmostEqual(carrier.facing_y, 0.0)
        self.assertLess(ball.x, carrier.x)
        self.assertLess(ball.vx, 0.0)

    def test_facing_stays_normalized_for_diagonal_receiver(self):
        team, carrier, ball = _carrier_with_ball()
        mate = _add_player(team, "T1P2", carrier.x + 60, carrier.y + 80)
        carrier.pass_ball(ball, mate)
        self.assertAlmostEqual(math.hypot(carrier.facing_x, carrier.facing_y),
                               1.0)
        self.assertAlmostEqual(carrier.facing_x, 0.6)
        self.assertAlmostEqual(carrier.facing_y, 0.8)


class PassPowerTest(unittest.TestCase):
    def _pass_speed(self, dist):
        team, carrier, ball = _carrier_with_ball()
        mate = _add_player(team, "T1P2", carrier.x + dist, carrier.y)
        carrier.pass_ball(ball, mate)
        return math.hypot(ball.vx, ball.vy)

    def test_longer_passes_are_driven_harder(self):
        short = self._pass_speed(60)
        longer = self._pass_speed(240)
        self.assertGreater(longer, short)
        self.assertLessEqual(longer, BALL_MAX_SPEED)

    def test_tap_pass_keeps_minimum_zip(self):
        self.assertAlmostEqual(self._pass_speed(20), PASS_POWER_MIN)

    def test_long_ball_rolls_close_to_the_receiver(self):
        team, carrier, ball = _carrier_with_ball()
        mate = _add_player(team, "T1P2", carrier.x + 240, carrier.y)
        carrier.pass_ball(ball, mate)
        for _ in range(60 * 5):  # 5 simulated seconds
            ball.update(1 / 60)
        # The driven ball must come to rest near the receiver (within a
        # step or two), not die in no-man's-land halfway.
        self.assertLess(abs(mate.x - ball.x), 60)


class LongPassTargetTest(unittest.TestCase):
    def _ai(self, carrier_xy=(300.0, 300.0)):
        team = Team("Team 1", (255, 0, 0))
        carrier = _add_player(team, "T1P1", *carrier_xy)
        opp = Team("Team 2", (0, 0, 255))
        ball = Ball(carrier.x, carrier.y)
        ball.possession = carrier
        ai = AIController(team, opp, ball)
        ai.team_state = "attack"
        ai.active_player = carrier
        return ai, carrier

    def test_clearly_open_far_teammate_is_a_long_pass_target(self):
        ai, carrier = self._ai()
        far_open = _add_player(ai.team, "T1P2", carrier.x + 200, carrier.y)
        self.assertGreater(carrier.distance_to(far_open), MAX_PASS_DIST)

        self.assertIs(ai._best_pass_target(carrier), far_open)

    def test_marked_far_teammate_is_not_worth_the_long_ball(self):
        ai, carrier = self._ai()
        far_marked = _add_player(ai.team, "T1P2", carrier.x + 200, carrier.y)
        # Marker near the receiver but outside the lane's blocked corridor.
        _add_player(ai.opponent_team, "T2P1",
                    far_marked.x, far_marked.y + LONG_PASS_MIN_OPENNESS - 10)

        self.assertIsNone(ai._best_pass_target(carrier))

    def test_teammate_beyond_long_range_is_excluded(self):
        ai, carrier = self._ai()
        _add_player(ai.team, "T1P2", carrier.x + LONG_PASS_DIST + 20, carrier.y)

        self.assertIsNone(ai._best_pass_target(carrier))

    def test_backward_outlets_stay_short_range(self):
        ai, carrier = self._ai()
        _add_player(ai.team, "T1P2", carrier.x - 200, carrier.y)

        self.assertIsNone(ai._best_pass_target(carrier, allow_backward=True))


if __name__ == "__main__":
    unittest.main()
