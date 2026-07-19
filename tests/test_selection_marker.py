"""
Unit tests for the selected-player visual marker (Tier 5, task 7): a cyan
chevron is drawn above the human-controlled player, and only that player.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.game_engine import GameEngine
from src.ui import UI


class SelectionMarkerWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_render_marks_only_the_selected_player(self):
        engine = GameEngine(human_team="team1")
        engine.ui.draw_selection_marker = mock.Mock()
        engine.render()
        engine.ui.draw_selection_marker.assert_called_once_with(
            engine.human_controller.selected_player)

    def test_all_ai_render_marks_nobody(self):
        engine = GameEngine()  # no human side
        engine.ui.draw_selection_marker = mock.Mock()
        engine.render()
        engine.ui.draw_selection_marker.assert_not_called()

    def test_draw_player_marker_toggles_with_selected_flag(self):
        engine = GameEngine(human_team="team1")
        engine.ui.draw_selection_marker = mock.Mock()
        player = engine.team1.players[0]
        engine.ui.draw_player(player, selected=False)
        engine.ui.draw_selection_marker.assert_not_called()
        engine.ui.draw_player(player, selected=True)
        engine.ui.draw_selection_marker.assert_called_once_with(player)


class SelectionMarkerPixelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @staticmethod
    def _marker_band(screen, player):
        """RGB pixels straight above the player's head, across the chevron."""
        x = int(player.x)
        return [tuple(screen.get_at((x, y)))[:3]
                for y in range(int(player.y - player.radius - 30),
                               int(player.y - player.radius - 17))]

    def test_marker_is_cyan_above_the_selected_player(self):
        engine = GameEngine(human_team="team1")
        sp = engine.human_controller.selected_player
        # Clear the area: park everyone else far away, center the selection.
        for p in engine.team1.players + engine.team2.players:
            p.x, p.y = 700, 520
        sp.x, sp.y = 400, 300
        engine.render()
        self.assertIn(UI.SELECT_MARKER_COLOR, self._marker_band(engine.screen, sp))

    def test_no_marker_over_a_non_selected_player(self):
        engine = GameEngine(human_team="team1")
        sp = engine.human_controller.selected_player
        other = next(p for p in engine.team1.players if p is not sp)
        for p in engine.team1.players + engine.team2.players:
            p.x, p.y = 700, 520
        sp.x, sp.y = 400, 300
        other.x, other.y = 150, 150
        engine.render()
        self.assertNotIn(UI.SELECT_MARKER_COLOR,
                         self._marker_band(engine.screen, other))


if __name__ == "__main__":
    unittest.main()
