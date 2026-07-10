"""
Unit tests for ball possession / dribbling.

Covers Tier 1 fix #1: the ball must stay glued just ahead of its carrier
until it is kicked, instead of being left behind when the player moves.

Run with:  python -m unittest discover -s tests
"""

import math
import os
import unittest

# Headless SDL so pygame can be imported without a display/audio device.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.entities import Ball, Player


class CarryBallTest(unittest.TestCase):
    def setUp(self):
        self.player = Player("P", 100.0, 100.0, (255, 0, 0))
        self.ball = Ball(500.0, 500.0)  # far away on purpose

    def test_carry_positions_ball_ahead_of_player(self):
        self.ball.possession = self.player
        self.player.facing_x, self.player.facing_y = 1.0, 0.0

        self.player.carry_ball(self.ball)

        offset = self.player.radius + self.ball.radius
        self.assertAlmostEqual(self.ball.x, self.player.x + offset)
        self.assertAlmostEqual(self.ball.y, self.player.y)
        # Ball ends up exactly `offset` away from the player.
        self.assertAlmostEqual(self.player.distance_to(self.ball), offset)

    def test_carry_respects_facing_direction(self):
        self.ball.possession = self.player
        # Facing straight up.
        self.player.facing_x, self.player.facing_y = 0.0, -1.0

        self.player.carry_ball(self.ball)

        offset = self.player.radius + self.ball.radius
        self.assertAlmostEqual(self.ball.x, self.player.x)
        self.assertAlmostEqual(self.ball.y, self.player.y - offset)

    def test_carry_is_noop_when_not_possessor(self):
        # Ball is possessed by someone else (None here).
        self.ball.possession = None
        original = (self.ball.x, self.ball.y)

        self.player.carry_ball(self.ball)

        self.assertEqual((self.ball.x, self.ball.y), original)

    def test_carry_syncs_ball_velocity_to_player(self):
        self.ball.possession = self.player
        self.player.vx, self.player.vy = 42.0, -7.0

        self.player.carry_ball(self.ball)

        self.assertAlmostEqual(self.ball.vx, 42.0)
        self.assertAlmostEqual(self.ball.vy, -7.0)


class FacingTest(unittest.TestCase):
    def test_facing_updates_from_movement(self):
        player = Player("P", 0.0, 0.0, (0, 0, 255))
        player.move_towards(100.0, 0.0, player.max_speed)  # aim right
        player.update(0.1)
        self.assertGreater(player.facing_x, 0.9)
        self.assertAlmostEqual(player.facing_y, 0.0, places=5)

    def test_facing_preserved_when_stationary(self):
        player = Player("P", 0.0, 0.0, (0, 0, 255))
        player.facing_x, player.facing_y = 0.0, 1.0
        player.vx, player.vy = 0.0, 0.0
        player.update(0.1)
        # No movement => facing unchanged.
        self.assertAlmostEqual(player.facing_x, 0.0)
        self.assertAlmostEqual(player.facing_y, 1.0)


class KickReleasesPossessionTest(unittest.TestCase):
    def test_shoot_releases_possession(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        ball = Ball(player.x + 15, player.y)
        ball.possession = player

        self.assertTrue(player.shoot(ball, 700.0, 100.0))
        self.assertIsNone(ball.possession)
        # Ball now has outward velocity (it was kicked).
        self.assertGreater(math.hypot(ball.vx, ball.vy), 0.0)

    def test_carry_stops_after_release(self):
        player = Player("P", 100.0, 100.0, (255, 0, 0))
        ball = Ball(player.x + 15, player.y)
        ball.possession = player
        player.pass_ball(ball, Player("Q", 300.0, 100.0, (255, 0, 0)))

        # After release, moving the player must NOT drag the ball.
        player.x = 400.0
        player.carry_ball(ball)
        self.assertNotAlmostEqual(ball.x, player.x + player.radius + ball.radius)


class EngineIntegrationTest(unittest.TestCase):
    """The ball must follow its carrier across GameEngine.update() frames."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        # Deterministic virtual clock so each update() advances a fixed dt
        # (wall-clock dt would be ~0 in a tight test loop => no movement).
        self._vms = {"t": 0}
        self._real_get_ticks = pygame.time.get_ticks
        pygame.time.get_ticks = lambda: self._vms["t"]

    def tearDown(self):
        pygame.time.get_ticks = self._real_get_ticks

    def _make_engine(self):
        from src.game_engine import GameEngine
        engine = GameEngine()  # captures last_update_time at virtual t=0
        # Freeze AI so possession is stable for the test.
        engine.team1_ai.update = lambda dt: None
        engine.team2_ai.update = lambda dt: None
        return engine

    def _tick(self, engine, dt_ms=16):
        self._vms["t"] += dt_ms
        engine.update()

    def test_ball_follows_carrier_across_frames(self):
        engine = self._make_engine()
        carrier = engine.team1.players[0]
        engine.ball.possession = carrier

        offset = carrier.radius + engine.ball.radius

        # Drive the carrier to the right for several frames and confirm the
        # ball stays glued to it (instead of being left at kickoff spot).
        for _ in range(30):
            carrier.move_towards(carrier.x + 50, carrier.y, carrier.max_speed)
            self._tick(engine)
            if engine.ball.possession is not carrier:
                break  # a goal/reset happened; stop asserting
            self.assertLessEqual(
                carrier.distance_to(engine.ball), offset + 1.0,
                "Ball drifted away from its carrier",
            )

    def test_ball_moves_with_carrier_not_static(self):
        engine = self._make_engine()
        carrier = engine.team1.players[0]
        engine.ball.possession = carrier

        # Let the ball snap to the carrier first, then measure displacement.
        carrier.move_towards(carrier.x + 50, carrier.y, carrier.max_speed)
        self._tick(engine)
        ball_x_after_snap = engine.ball.x
        carrier_x_after_snap = carrier.x

        for _ in range(30):
            carrier.move_towards(carrier.x + 50, carrier.y, carrier.max_speed)
            self._tick(engine)

        # Both the carrier and the ball travelled meaningfully to the right,
        # and the ball tracked the carrier's movement.
        self.assertGreater(carrier.x - carrier_x_after_snap, 20.0)
        self.assertGreater(engine.ball.x - ball_x_after_snap, 20.0)


if __name__ == "__main__":
    unittest.main()
