"""
Unit tests for the human/CPU control-mode switch on GameEngine (Tier 5, task 1).

Team 1 or Team 2 can be designated human-controlled; that side is then driven
by an attached human controller instead of its AIController. The default is
all-AI so the headless tools keep running unchanged, and a human-designated
side with no controller attached yet falls back to its AI so nothing freezes.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src import game_engine
from src.game_engine import GameEngine


def _step_once(engine):
    """Run a single deterministic engine frame (dt == 0)."""
    engine.last_update_time = 1000
    with mock.patch.object(game_engine.pygame.time, "get_ticks",
                           return_value=1000):
        engine.update()


class ControlModeConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_default_is_all_cpu(self):
        engine = GameEngine()
        self.assertIsNone(engine.human_team)
        self.assertIsNone(engine.human_controller)
        self.assertFalse(engine.is_human_controlled(engine.team1))
        self.assertFalse(engine.is_human_controlled(engine.team2))

    def test_human_team1_by_name(self):
        engine = GameEngine(human_team="team1")
        self.assertIs(engine.human_team, engine.team1)
        self.assertTrue(engine.is_human_controlled(engine.team1))
        self.assertFalse(engine.is_human_controlled(engine.team2))

    def test_human_team2_by_name(self):
        engine = GameEngine(human_team="team2")
        self.assertIs(engine.human_team, engine.team2)
        self.assertTrue(engine.is_human_controlled(engine.team2))
        self.assertFalse(engine.is_human_controlled(engine.team1))

    def test_team_instance_spec_is_accepted(self):
        engine = GameEngine()
        # Post-construction reconfiguration via a resolved Team instance.
        self.assertIs(engine._resolve_team(engine.team2), engine.team2)

    def test_invalid_spec_raises(self):
        with self.assertRaises(ValueError):
            GameEngine(human_team="team3")


class ControlModeRoutingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_default_runs_both_ais(self):
        engine = GameEngine()
        engine.team1_ai = mock.Mock()
        engine.team2_ai = mock.Mock()

        _step_once(engine)

        engine.team1_ai.update.assert_called_once()
        engine.team2_ai.update.assert_called_once()

    def test_human_controller_replaces_only_its_ai(self):
        engine = GameEngine(human_team="team1")
        engine.team1_ai = mock.Mock()
        engine.team2_ai = mock.Mock()
        human = mock.Mock()
        engine.set_human_controller(human)

        _step_once(engine)

        human.update.assert_called_once()
        engine.team1_ai.update.assert_not_called()
        engine.team2_ai.update.assert_called_once()

    def test_human_team_without_controller_falls_back_to_ai(self):
        engine = GameEngine(human_team="team1")
        engine.team1_ai = mock.Mock()
        engine.team2_ai = mock.Mock()

        _step_once(engine)

        engine.team1_ai.update.assert_called_once()
        engine.team2_ai.update.assert_called_once()


if __name__ == "__main__":
    unittest.main()
