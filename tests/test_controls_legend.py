"""
Unit tests for the on-screen controls legend (Tier 5): a compact hint of the
human controls is drawn while a human is playing, and not in all-AI mode.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.game_engine import GameEngine


class ControlsLegendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_legend_drawn_in_human_mode(self):
        engine = GameEngine(human_team="team1")
        engine.ui.draw_controls_legend = mock.Mock()
        engine.render()
        engine.ui.draw_controls_legend.assert_called_once()

    def test_no_legend_in_all_ai_mode(self):
        engine = GameEngine()  # no human side
        engine.ui.draw_controls_legend = mock.Mock()
        engine.render()
        engine.ui.draw_controls_legend.assert_not_called()

    def test_legend_renders_without_error(self):
        engine = GameEngine(human_team="team1")
        engine.ui.draw_controls_legend()  # must not raise


if __name__ == "__main__":
    unittest.main()
