"""
Unit tests for player kick actions: cooldown and power floor.

Covers Tier 1 fix #2 from the v0.1.0 baseline report: shots/passes had no
cooldown (the AI fired every frame, draining stamina to zero) and power could
collapse to nearly zero, so the ball barely moved and nobody scored.

Run with:  python -m unittest discover -s tests
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.entities import ACTION_COOLDOWN, MIN_POWER_FACTOR, Ball, Player


def _possessed_ball(player):
    ball = Ball(player.x + player.radius + 5, player.y)
    ball.possession = player
    return ball


class ActionCooldownTest(unittest.TestCase):
    def test_can_act_reflects_cooldown(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        self.assertTrue(player.can_act())
        player.action_cooldown = ACTION_COOLDOWN
        self.assertFalse(player.can_act())

    def test_shoot_sets_cooldown_and_blocks_immediate_reshoot(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        ball = _possessed_ball(player)

        self.assertTrue(player.shoot(ball, 700.0, 100.0))
        self.assertAlmostEqual(player.action_cooldown, ACTION_COOLDOWN)

        # A shot re-attaches nothing; simulate still having the ball.
        ball.possession = player
        self.assertFalse(player.shoot(ball, 700.0, 100.0),
                          "player should not shoot again while on cooldown")

    def test_pass_sets_cooldown_and_blocks_immediate_repass(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        mate = Player("Q", 300.0, 100.0, (255, 0, 0))
        ball = _possessed_ball(player)

        self.assertTrue(player.pass_ball(ball, mate))
        ball.possession = player
        self.assertFalse(player.pass_ball(ball, mate),
                         "player should not pass again while on cooldown")

    def test_cooldown_expires_after_update(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        ball = _possessed_ball(player)
        player.shoot(ball, 700.0, 100.0)
        self.assertFalse(player.can_act())

        # Advance enough time for the cooldown to elapse.
        player.update(ACTION_COOLDOWN + 0.01)
        self.assertTrue(player.can_act())

        ball.possession = player
        self.assertTrue(player.shoot(ball, 700.0, 100.0),
                        "player should shoot again after cooldown expires")

    def test_action_count_is_bounded_over_time(self):
        """Over 1 simulated second a player can act at most ~1/cooldown times."""
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        ball = _possessed_ball(player)

        dt = 1.0 / 60
        actions = 0
        for _ in range(60):  # 1 second at 60 fps
            if player.shoot(ball, 700.0, 100.0):
                actions += 1
                ball.possession = player  # pretend possession regained
            player.update(dt)

        # ~1s / 0.5s cooldown => at most 2-3 actions, nowhere near 60.
        self.assertLessEqual(actions, math.ceil(1.0 / ACTION_COOLDOWN) + 1)
        self.assertGreaterEqual(actions, 1)


class PowerFloorTest(unittest.TestCase):
    def test_shot_power_does_not_collapse_when_exhausted(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        player.current_stamina = 0  # fully exhausted
        ball = _possessed_ball(player)

        self.assertTrue(player.shoot(ball, 700.0, 100.0))
        speed = math.hypot(ball.vx, ball.vy)
        expected_min = player.shoot_power * MIN_POWER_FACTOR
        self.assertGreaterEqual(speed, expected_min - 1e-6)
        self.assertGreater(speed, 50.0)  # clearly moving, not a dribble

    def test_full_stamina_shot_is_full_power(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        player.current_stamina = 100
        ball = _possessed_ball(player)

        player.shoot(ball, 700.0, 100.0)
        speed = math.hypot(ball.vx, ball.vy)
        self.assertAlmostEqual(speed, player.shoot_power, delta=1.0)


if __name__ == "__main__":
    unittest.main()
