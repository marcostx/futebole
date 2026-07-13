"""
Unit tests for gradual stamina effects (Tier 4).

Sprinting drains stamina and resting recovers it; a player's movement speed
and kick power scale smoothly with their remaining stamina (floored, so a
gassed player is slower and softer but never immobile or powerless).
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src.entities import (MIN_POWER_FACTOR, MIN_SPEED_FACTOR,
                          RECOVERY_THRESHOLD, SPRINT_THRESHOLD, Ball, Player)


def _player(stamina=100.0):
    p = Player("P", 300.0, 300.0, (255, 0, 0))
    p.current_stamina = stamina
    return p


class SpeedFactorTest(unittest.TestCase):
    def test_speed_scales_gradually_with_stamina(self):
        self.assertAlmostEqual(_player(100).speed_factor(), 1.0)
        self.assertAlmostEqual(_player(0).speed_factor(), MIN_SPEED_FACTOR)
        expected_mid = MIN_SPEED_FACTOR + (1 - MIN_SPEED_FACTOR) * 0.5
        self.assertAlmostEqual(_player(50).speed_factor(), expected_mid)

    def test_move_towards_applies_the_fatigue_scale(self):
        fresh, tired = _player(100), _player(0)
        for p in (fresh, tired):
            p.move_towards(p.x + 100, p.y, p.max_speed)

        fresh_speed = math.hypot(fresh.vx, fresh.vy)
        tired_speed = math.hypot(tired.vx, tired.vy)
        self.assertAlmostEqual(fresh_speed, fresh.max_speed)
        self.assertAlmostEqual(tired_speed,
                               tired.max_speed * MIN_SPEED_FACTOR)


class StaminaDrainRecoveryTest(unittest.TestCase):
    def test_sprinting_drains_stamina(self):
        p = _player(100)
        before = p.current_stamina
        # One second of flat-out sprinting, with the AI re-issuing movement
        # every frame as it does in the real loop.
        for _ in range(60):
            p.vx, p.vy = p.max_speed, 0.0
            p.update(1 / 60)
        self.assertLess(p.current_stamina, before - 3)

    def test_jogging_is_sustainable(self):
        p = _player(50)
        # Between the recovery and sprint thresholds: no drain, no recovery.
        p.vx = p.max_speed * (SPRINT_THRESHOLD + RECOVERY_THRESHOLD) / 2
        before = p.current_stamina
        p.update(1 / 60)  # one frame, so friction keeps speed in the band
        self.assertAlmostEqual(p.current_stamina, before)

    def test_resting_recovers_stamina(self):
        p = _player(40)
        p.vx = p.vy = 0.0
        p.update(1.0)
        self.assertGreater(p.current_stamina, 40)

    def test_stamina_stays_within_bounds(self):
        exhausted = _player(0.05)
        for _ in range(60):  # keep sprinting on empty: clamped at zero
            exhausted.vx, exhausted.vy = exhausted.max_speed, 0.0
            exhausted.update(1 / 60)
        self.assertGreaterEqual(exhausted.current_stamina, 0.0)

        fresh = _player(99.9)
        fresh.vx = fresh.vy = 0.0
        fresh.update(5.0)
        self.assertLessEqual(fresh.current_stamina, fresh.stamina)


class GradualPowerTest(unittest.TestCase):
    def _shot_speed(self, stamina):
        p = _player(stamina)
        ball = Ball(p.x, p.y)
        ball.possession = p
        p.shoot(ball, 700.0, 300.0)
        return math.hypot(ball.vx, ball.vy)

    def test_shot_power_scales_gradually(self):
        p = _player(50)
        expected_mid = MIN_POWER_FACTOR + (1 - MIN_POWER_FACTOR) * 0.5
        self.assertAlmostEqual(p.power_factor(), expected_mid)

        full = self._shot_speed(100)
        mid = self._shot_speed(50)
        empty = self._shot_speed(0)
        self.assertGreater(full, mid)
        self.assertGreater(mid, empty)
        self.assertAlmostEqual(mid, full * expected_mid, delta=1.0)

    def test_pass_power_scales_gradually(self):
        speeds = []
        for stamina in (100, 50, 0):
            p = _player(stamina)
            mate = Player("Q", p.x + 100, p.y, (255, 0, 0))
            ball = Ball(p.x, p.y)
            ball.possession = p
            p.pass_ball(ball, mate)
            speeds.append(math.hypot(ball.vx, ball.vy))
        self.assertGreater(speeds[0], speeds[1])
        self.assertGreater(speeds[1], speeds[2])


if __name__ == "__main__":
    unittest.main()
