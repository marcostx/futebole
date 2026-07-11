"""
Unit tests for circle-based player separation (Tier 2 fix #1).

Verifies that overlapping players are pushed apart, non-overlapping players
are left alone, perfectly coincident players are still separated, and that
separation keeps players inside the field.
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.game_engine import GameEngine


class PlayerSeparationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _engine(self):
        engine = GameEngine()
        engine.team1_ai.update = lambda dt: None
        engine.team2_ai.update = lambda dt: None
        # Park everyone well apart and inside the field.
        for i, p in enumerate(engine.team1.players + engine.team2.players):
            p.x = engine.field_x + 100 + i * 40
            p.y = engine.field_y + 50
        return engine

    def test_overlapping_players_are_pushed_apart(self):
        engine = self._engine()
        a, b = engine.team1.players[0], engine.team1.players[1]
        cx = engine.field_x + engine.field_width // 2
        cy = engine.field_y + engine.field_height // 2
        a.x, a.y = cx, cy
        b.x, b.y = cx + 5, cy  # heavily overlapping (min_dist = 20)

        engine.separate_players()

        min_dist = a.radius + b.radius
        self.assertGreaterEqual(a.distance_to(b), min_dist - 1e-6)

    def test_non_overlapping_players_unchanged(self):
        engine = self._engine()
        a, b = engine.team1.players[0], engine.team1.players[1]
        cx = engine.field_x + engine.field_width // 2
        cy = engine.field_y + engine.field_height // 2
        a.x, a.y = cx, cy
        b.x, b.y = cx + 100, cy  # far apart
        before = (a.x, a.y, b.x, b.y)

        engine.separate_players()

        self.assertEqual((a.x, a.y, b.x, b.y), before)

    def test_coincident_players_are_separated(self):
        engine = self._engine()
        a, b = engine.team1.players[0], engine.team2.players[0]
        cx = engine.field_x + engine.field_width // 2
        cy = engine.field_y + engine.field_height // 2
        a.x, a.y = cx, cy
        b.x, b.y = cx, cy  # exactly the same point

        engine.separate_players()

        self.assertGreater(a.distance_to(b), 0.0)

    def test_separation_keeps_players_in_field(self):
        engine = self._engine()
        a, b = engine.team1.players[0], engine.team1.players[1]
        # Overlap right in the top-left corner so the push could exit the field.
        a.x, a.y = engine.field_x, engine.field_y
        b.x, b.y = engine.field_x + 3, engine.field_y

        engine.separate_players()

        for p in (a, b):
            self.assertGreaterEqual(p.x, engine.field_x)
            self.assertLessEqual(p.x, engine.field_x + engine.field_width)
            self.assertGreaterEqual(p.y, engine.field_y)
            self.assertLessEqual(p.y, engine.field_y + engine.field_height)

    def test_repeated_passes_declutter_a_pile(self):
        """Several frames of separation should resolve a stack of players."""
        engine = self._engine()
        cx = engine.field_x + engine.field_width // 2
        cy = engine.field_y + engine.field_height // 2
        players = engine.team1.players
        for k, p in enumerate(players):
            p.x, p.y = cx + k * 2, cy  # all piled within a few px

        for _ in range(60):
            engine.separate_players()

        # No two teammates should still be overlapping after relaxation.
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                self.assertGreaterEqual(
                    players[i].distance_to(players[j]),
                    players[i].radius + players[j].radius - 1.0,
                )


if __name__ == "__main__":
    unittest.main()
