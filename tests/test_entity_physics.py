"""
Unit tests for frame-rate independent entity friction (Tier 3 #1).
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401  (ensures headless SDL is importable in this suite)

from src.entities import ENTITY_FRICTION_PER_SEC, Entity


def _coast(entity, seconds, fps):
    dt = 1.0 / fps
    for _ in range(int(round(seconds * fps))):
        entity.update(dt)


class EntityFrictionTest(unittest.TestCase):
    def test_friction_slows_the_entity(self):
        e = Entity(0.0, 0.0)
        e.vx, e.vy = 100.0, 0.0
        e.update(0.1)
        self.assertLess(e.vx, 100.0)
        self.assertGreater(e.vx, 0.0)

    def test_velocity_after_one_second_matches_constant(self):
        e = Entity(0.0, 0.0)
        e.vx = 100.0
        _coast(e, seconds=1.0, fps=1000)  # fine steps ~ continuous decay
        self.assertAlmostEqual(e.vx, 100.0 * ENTITY_FRICTION_PER_SEC, delta=1.0)

    def test_friction_is_frame_rate_independent(self):
        a = Entity(0.0, 0.0)
        b = Entity(0.0, 0.0)
        a.vx = b.vx = 200.0
        _coast(a, seconds=1.0, fps=60)
        _coast(b, seconds=1.0, fps=240)
        # Position and remaining velocity should be close regardless of fps.
        self.assertAlmostEqual(a.x, b.x, delta=0.05 * max(a.x, 1.0))
        self.assertAlmostEqual(a.vx, b.vx, delta=1.0)

    def test_matches_legacy_behavior_at_60fps(self):
        # Old model decayed velocity by 0.95 each frame at 60 fps.
        e = Entity(0.0, 0.0)
        e.vx = 100.0
        legacy = 100.0
        for _ in range(10):
            e.update(1.0 / 60)
            legacy *= 0.95
        self.assertAlmostEqual(e.vx, legacy, delta=0.5)


if __name__ == "__main__":
    unittest.main()
