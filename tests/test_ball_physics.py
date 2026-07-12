"""
Unit tests for improved ball physics (Tier 3 #2): max speed and bounce.
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.entities import BALL_MAX_SPEED, BALL_RESTITUTION, Ball
from src.game_engine import GameEngine


class BallSpeedCapTest(unittest.TestCase):
    def test_cap_speed_limits_velocity(self):
        ball = Ball(0.0, 0.0)
        ball.vx, ball.vy = 5000.0, 0.0
        ball.cap_speed()
        self.assertAlmostEqual(math.hypot(ball.vx, ball.vy), BALL_MAX_SPEED)

    def test_cap_speed_preserves_direction(self):
        ball = Ball(0.0, 0.0)
        ball.vx, ball.vy = 3000.0, 4000.0  # 3-4-5 direction
        ball.cap_speed()
        # Direction (ratio) preserved after clamping.
        self.assertAlmostEqual(ball.vy / ball.vx, 4.0 / 3.0, places=5)
        self.assertAlmostEqual(math.hypot(ball.vx, ball.vy), BALL_MAX_SPEED)

    def test_update_caps_an_overpowered_kick(self):
        ball = Ball(0.0, 0.0)
        ball.kick(1.0, 0.0, 100000.0)  # absurd power
        ball.update(1.0 / 60)
        self.assertLessEqual(math.hypot(ball.vx, ball.vy), BALL_MAX_SPEED + 1e-6)

    def test_normal_shot_is_not_capped(self):
        ball = Ball(0.0, 0.0)
        ball.kick(1.0, 0.0, 500.0)  # a normal full-power shot
        ball.cap_speed()
        self.assertAlmostEqual(math.hypot(ball.vx, ball.vy), 500.0)


class BallBounceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _engine(self):
        engine = GameEngine()
        engine.team1_ai.update = lambda dt: None
        engine.team2_ai.update = lambda dt: None
        # Tear down the kickoff so the ball is genuinely free/untouched.
        engine.kickoff_pending = False
        engine.ball.possession = None
        engine.ball.last_toucher = None
        return engine

    def test_bounce_reverses_and_dampens_horizontal(self):
        engine = self._engine()
        top, _ = engine.goal_mouth()
        # Off-target at the left edge, above the goal mouth => wall bounce.
        engine.ball.x = engine.field_x - 1
        engine.ball.y = top - 20
        engine.ball.vx = -200.0

        engine.handle_ball_boundaries()

        self.assertAlmostEqual(engine.ball.vx, 200.0 * BALL_RESTITUTION)
        self.assertGreater(engine.ball.vx, 0)  # reversed inward

    def test_bounce_reverses_and_dampens_vertical(self):
        engine = self._engine()
        engine.ball.x = engine.field_x + engine.field_width // 2
        engine.ball.y = engine.field_y - 5
        engine.ball.vy = -150.0

        engine.handle_ball_boundaries()

        self.assertAlmostEqual(engine.ball.vy, 150.0 * BALL_RESTITUTION)
        self.assertGreater(engine.ball.vy, 0)


if __name__ == "__main__":
    unittest.main()
