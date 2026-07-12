"""
Unit tests for goal detection and ball rolling physics (Tier 1 fix #4).

Verifies that:
- the ball actually travels far enough for a shot to reach the goal
- rolling friction is frame-rate independent
- a kick puts the ball "in flight" (loose) and possession cannot be regained
  until the flight window elapses
- goal detection scores for the right team inside the goal mouth and bounces
  the ball off the woodwork/walls otherwise
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.entities import LOOSE_BALL_TIME, Ball, Player
from src.game_engine import GameEngine


def _integrate(ball, seconds, fps):
    dt = 1.0 / fps
    for _ in range(int(seconds * fps)):
        ball.update(dt)


class BallPhysicsTest(unittest.TestCase):
    def test_kick_sets_loose_flight_and_releases_possession(self):
        ball = Ball(100.0, 100.0)
        ball.possession = object()
        ball.kick(1.0, 0.0, 400.0)
        self.assertIsNone(ball.possession)
        self.assertAlmostEqual(ball.loose_timer, LOOSE_BALL_TIME)

    def test_loose_timer_counts_down_on_update(self):
        ball = Ball(100.0, 100.0)
        ball.kick(1.0, 0.0, 400.0)
        ball.update(0.1)
        self.assertAlmostEqual(ball.loose_timer, LOOSE_BALL_TIME - 0.1, places=5)

    def test_shot_travels_far_enough_to_reach_goal(self):
        # Use the actual tuning constant so this stays aligned if it changes.
        full_power = Player("S", 0.0, 0.0, (255, 0, 0)).shoot_power
        ball = Ball(100.0, 100.0)
        ball.kick(1.0, 0.0, full_power)  # a full-power shot to the right
        _integrate(ball, seconds=3.0, fps=60)
        travelled = ball.x - 100.0
        # Shooting range is <150px; the ball must be able to cover that.
        self.assertGreater(travelled, 150.0)

        # The ball should not roll forever; its velocity should decay to ~0.
        _integrate(ball, seconds=10.0, fps=60)
        self.assertLess(abs(ball.vx), 1.0)
        self.assertLess(abs(ball.vy), 1.0)

    def test_rolling_friction_slows_the_ball(self):
        ball = Ball(0.0, 0.0)
        ball.kick(1.0, 0.0, 400.0)
        speed_before = abs(ball.vx)
        ball.update(0.5)
        self.assertLess(abs(ball.vx), speed_before)

    def test_friction_is_frame_rate_independent(self):
        a = Ball(0.0, 0.0)
        b = Ball(0.0, 0.0)
        a.kick(1.0, 0.0, 400.0)
        b.kick(1.0, 0.0, 400.0)
        _integrate(a, seconds=2.0, fps=60)
        _integrate(b, seconds=2.0, fps=30)
        # Distance travelled should be close regardless of frame rate.
        self.assertAlmostEqual(a.x, b.x, delta=0.05 * a.x)


class GoalDetectionTest(unittest.TestCase):
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

    def test_goal_in_left_net_scores_for_team2(self):
        engine = self._engine()
        top, bottom = engine.goal_mouth()
        engine.ball.x = engine.field_x - 1
        engine.ball.y = (top + bottom) / 2

        scorer = engine.handle_ball_boundaries()

        self.assertEqual(scorer, "team2")
        self.assertEqual(engine.team2_score, 1)
        self.assertEqual(engine.team1_score, 0)
        # Ball reset to center after the goal.
        self.assertAlmostEqual(engine.ball.x, engine.field_x + engine.field_width // 2)

    def test_goal_in_right_net_scores_for_team1(self):
        engine = self._engine()
        top, bottom = engine.goal_mouth()
        engine.ball.x = engine.field_x + engine.field_width + 1
        engine.ball.y = (top + bottom) / 2

        scorer = engine.handle_ball_boundaries()

        self.assertEqual(scorer, "team1")
        self.assertEqual(engine.team1_score, 1)
        self.assertEqual(engine.team2_score, 0)

    def test_ball_off_target_bounces_without_scoring(self):
        engine = self._engine()
        top, _ = engine.goal_mouth()
        engine.ball.x = engine.field_x - 1
        engine.ball.y = top - 20  # above the goal mouth
        engine.ball.vx = -100.0

        scorer = engine.handle_ball_boundaries()

        self.assertIsNone(scorer)
        self.assertEqual(engine.team1_score, 0)
        self.assertEqual(engine.team2_score, 0)
        self.assertAlmostEqual(engine.ball.x, engine.field_x)  # clamped in
        self.assertGreater(engine.ball.vx, 0)  # bounced back inward

    def test_ball_bounces_off_side_walls(self):
        engine = self._engine()
        engine.ball.x = engine.field_x + engine.field_width // 2
        engine.ball.y = engine.field_y - 5
        engine.ball.vy = -100.0

        scorer = engine.handle_ball_boundaries()

        self.assertIsNone(scorer)
        self.assertAlmostEqual(engine.ball.y, engine.field_y)
        self.assertGreater(engine.ball.vy, 0)


class LooseBallPossessionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_no_possession_while_ball_in_flight(self):
        engine = GameEngine()
        engine.team1_ai.update = lambda dt: None
        engine.team2_ai.update = lambda dt: None
        for i, p in enumerate(engine.team1.players + engine.team2.players):
            p.x, p.y = 10000.0 + i * 100, 10000.0
            p.action_cooldown = 0.0
        engine.ball.x, engine.ball.y = 400.0, 300.0
        engine.ball.possession = None

        near = engine.team1.players[0]
        near.x, near.y = engine.ball.x, engine.ball.y

        engine.ball.loose_timer = 0.2  # in flight
        engine.resolve_possession()
        self.assertIsNone(engine.ball.possession)

        engine.ball.loose_timer = 0.0  # flight over
        engine.resolve_possession()
        self.assertIs(engine.ball.possession, near)


if __name__ == "__main__":
    unittest.main()
