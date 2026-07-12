"""
Unit tests for the ball carrier offloading under pressure (Tier 2).

When an opponent chases too close, the carrier must release the ball (pass, or
shoot if in range) instead of dribbling into the presser, which previously led
to a ball ping-pong loop.
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.ai import AIController, PRESSURE_DIST, SHOOT_RANGE
from src.entities import Ball, Player, Team


def _scenario(carrier_x=300.0, carrier_y=300.0):
    """Team 1 with a carrier + two teammates, and one opponent we can place."""
    team = Team("Team 1", (255, 0, 0))
    carrier = Player("T1P1", carrier_x, carrier_y, team.color)
    # Both teammates are forward and within MAX_PASS_DIST so selection is
    # decided by openness, not by the reachability filter.
    mate_near = Player("T1P2", carrier_x + 55, carrier_y - 10, team.color)
    mate_far = Player("T1P3", carrier_x + 45, carrier_y + 70, team.color)
    for p in (carrier, mate_near, mate_far):
        p.home_x, p.home_y = p.x, p.y
        team.add_player(p)

    opp = Team("Team 2", (0, 0, 255))
    opponent = Player("T2P1", 700.0, 300.0, opp.color)
    opp.add_player(opponent)

    ball = Ball(carrier.x, carrier.y)
    ball.possession = carrier

    ai = AIController(team, opp, ball)
    ai.team_state = "attack"
    ai.active_player = carrier
    ai.support_player = mate_near
    return ai, carrier, ball, opponent


class PressuredOffloadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_carrier_passes_when_pressured_out_of_range(self):
        # Carrier far from goal but with an opponent right on top of it.
        ai, carrier, ball, opponent = _scenario(carrier_x=300.0)
        opponent.x, opponent.y = carrier.x + 10, carrier.y  # within PRESSURE_DIST
        self.assertLess(carrier.distance_to(opponent), PRESSURE_DIST)

        ai.execute_attack_behavior(1 / 60)

        # The ball was released (kicked): possession cleared and in flight.
        self.assertIsNone(ball.possession)
        self.assertGreater(ball.loose_timer, 0.0)

    def test_carrier_dribbles_when_not_pressured(self):
        ai, carrier, ball, opponent = _scenario(carrier_x=300.0)
        opponent.x, opponent.y = 700.0, 300.0  # far away
        self.assertGreater(carrier.distance_to(opponent), PRESSURE_DIST)

        # No pressure and no openness advantage for either teammate (opponent
        # is deeper than both), so build-up keeps the ball and dribbles.
        ai.execute_attack_behavior(1 / 60)

        self.assertIs(ball.possession, carrier)
        self.assertGreater(abs(carrier.vx) + abs(carrier.vy), 0.0)

    def test_pressured_carrier_shoots_when_in_range(self):
        # Carrier near the opponent goal (right side) and under pressure.
        ai, carrier, ball, opponent = _scenario(carrier_x=630.0, carrier_y=300.0)
        opponent.x, opponent.y = carrier.x + 10, carrier.y
        # Within shooting range of the right goal (x=750).
        self.assertLess(abs(750 - carrier.x), SHOOT_RANGE)

        ai.execute_attack_behavior(1 / 60)

        # A shot was taken: ball released and moving toward the goal (+x).
        self.assertIsNone(ball.possession)
        self.assertGreater(ball.vx, 0.0)

    def test_best_pass_target_prefers_open_forward_teammate(self):
        ai, carrier, ball, opponent = _scenario(carrier_x=300.0)
        # mate_near is open and forward; mark mate_far tightly.
        mate_near = ai.team.players[1]
        mate_far = ai.team.players[2]
        opponent.x, opponent.y = mate_far.x, mate_far.y  # smother mate_far

        target = ai._best_pass_target(carrier)
        self.assertIs(target, mate_near)


if __name__ == "__main__":
    unittest.main()
