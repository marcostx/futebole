"""
Unit tests for AIController attacking behavior.

Covers the follow-up to Tier 1 fix #2: when the ball carrier is on cooldown
it must keep moving (dribble) instead of standing still while repeatedly
attempting a shot/pass that cannot fire.

Run with:  python -m unittest discover -s tests
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.ai import AIController
from src.entities import ACTION_COOLDOWN, Ball, Player, Team


def _make_scenario(carrier_x=700.0, carrier_y=300.0):
    """Team 1 carrier near the right-hand goal, one far-away opponent."""
    team = Team("Team 1", (255, 0, 0))
    carrier = Player("T1P1", carrier_x, carrier_y, team.color)
    team.add_player(carrier)

    opponent_team = Team("Team 2", (0, 0, 255))
    opponent_team.add_player(Player("T2P1", 100.0, 100.0, opponent_team.color))

    ball = Ball(carrier.x, carrier.y)
    ball.possession = carrier

    ai = AIController(team, opponent_team, ball)
    ai.team_state = "attack"
    return ai, carrier, ball


class AttackCooldownTest(unittest.TestCase):
    def test_carrier_dribbles_when_on_cooldown_in_range(self):
        ai, carrier, ball = _make_scenario()
        carrier.action_cooldown = ACTION_COOLDOWN  # can't kick yet
        carrier.vx = carrier.vy = 0.0

        ai.execute_attack_behavior(1 / 60)

        # It must not just stand still: some movement was issued.
        self.assertGreater(math.hypot(carrier.vx, carrier.vy), 0.0,
                           "carrier froze while on cooldown instead of dribbling")
        # And it did not manage to shoot (still has the ball).
        self.assertIs(ball.possession, carrier)

    def test_carrier_shoots_when_off_cooldown_in_range(self):
        ai, carrier, ball = _make_scenario()
        carrier.action_cooldown = 0.0  # ready to kick

        ai.execute_attack_behavior(1 / 60)

        # A shot fired: possession released and the ball is moving.
        self.assertIsNone(ball.possession)
        self.assertGreater(math.hypot(ball.vx, ball.vy), 0.0)
        self.assertAlmostEqual(carrier.action_cooldown, ACTION_COOLDOWN)

    def test_carrier_moves_when_on_cooldown_out_of_range(self):
        ai, carrier, ball = _make_scenario(carrier_x=300.0, carrier_y=300.0)
        carrier.action_cooldown = ACTION_COOLDOWN
        carrier.vx = carrier.vy = 0.0

        ai.execute_attack_behavior(1 / 60)

        self.assertGreater(math.hypot(carrier.vx, carrier.vy), 0.0)
        self.assertIs(ball.possession, carrier)


if __name__ == "__main__":
    unittest.main()
