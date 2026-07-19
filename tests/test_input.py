"""
Unit tests for the input layer (Tier 5, task 2): raw keys -> semantic actions
and an 8-direction movement vector, plus the engine seam that stores the latest
input frame. All resolved without opening a window (stub events, a dict-like
held-key state).
"""

import math
import os
import unittest
from collections import defaultdict

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src import input as game_input
from src.input import Action, InputFrame, KeyBindings


class _Event:
    """Minimal stand-in for a pygame event (type + key); no window needed."""

    def __init__(self, type_, key=None):
        self.type = type_
        self.key = key


def _pressed(*keys):
    """A get_pressed()-like mapping with the given keys held down."""
    state = defaultdict(bool)
    for key in keys:
        state[key] = True
    return state


class MovementVectorTest(unittest.TestCase):
    def test_no_keys_is_zero(self):
        self.assertEqual(game_input.movement_vector(_pressed()), (0.0, 0.0))

    def test_cardinal_directions(self):
        self.assertEqual(game_input.movement_vector(_pressed(pygame.K_UP)),
                         (0.0, -1.0))
        self.assertEqual(game_input.movement_vector(_pressed(pygame.K_DOWN)),
                         (0.0, 1.0))
        self.assertEqual(game_input.movement_vector(_pressed(pygame.K_LEFT)),
                         (-1.0, 0.0))
        self.assertEqual(game_input.movement_vector(_pressed(pygame.K_RIGHT)),
                         (1.0, 0.0))

    def test_wasd_matches_arrows(self):
        self.assertEqual(game_input.movement_vector(_pressed(pygame.K_w)),
                         (0.0, -1.0))
        self.assertEqual(game_input.movement_vector(_pressed(pygame.K_d)),
                         (1.0, 0.0))

    def test_diagonal_is_normalised(self):
        dx, dy = game_input.movement_vector(_pressed(pygame.K_RIGHT, pygame.K_DOWN))
        self.assertAlmostEqual(dx, math.sqrt(0.5))
        self.assertAlmostEqual(dy, math.sqrt(0.5))
        self.assertAlmostEqual(math.hypot(dx, dy), 1.0)

    def test_opposing_keys_cancel(self):
        self.assertEqual(
            game_input.movement_vector(_pressed(pygame.K_LEFT, pygame.K_RIGHT)),
            (0.0, 0.0))
        self.assertEqual(
            game_input.movement_vector(
                _pressed(pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT)),
            (-1.0, 0.0))


class PressedActionsTest(unittest.TestCase):
    def test_keydown_maps_to_actions(self):
        events = [_Event(pygame.KEYDOWN, pygame.K_j),
                  _Event(pygame.KEYDOWN, pygame.K_TAB)]
        self.assertEqual(game_input.pressed_actions(events),
                         {Action.PASS, Action.SWITCH_PLAYER})

    def test_non_keydown_events_ignored(self):
        events = [_Event(pygame.KEYUP, pygame.K_j),
                  _Event(pygame.MOUSEBUTTONDOWN),
                  _Event(pygame.KEYDOWN, pygame.K_k)]
        self.assertEqual(game_input.pressed_actions(events), {Action.SHOOT})

    def test_unbound_key_ignored(self):
        self.assertEqual(
            game_input.pressed_actions([_Event(pygame.KEYDOWN, pygame.K_p)]),
            set())

    def test_no_events(self):
        self.assertEqual(game_input.pressed_actions([]), set())


class HeldActionsTest(unittest.TestCase):
    def test_sprint_held_by_either_shift(self):
        self.assertEqual(game_input.held_actions(_pressed(pygame.K_LSHIFT)),
                         {Action.SPRINT})
        self.assertEqual(game_input.held_actions(_pressed(pygame.K_RSHIFT)),
                         {Action.SPRINT})

    def test_nothing_held(self):
        self.assertEqual(game_input.held_actions(_pressed()), set())

    def test_movement_keys_are_not_actions(self):
        self.assertEqual(game_input.held_actions(_pressed(pygame.K_w)), set())


class ReadInputTest(unittest.TestCase):
    def test_combines_move_actions_held(self):
        pressed = _pressed(pygame.K_UP, pygame.K_LSHIFT)
        events = [_Event(pygame.KEYDOWN, pygame.K_k)]
        frame = game_input.read_input(pressed, events)
        self.assertEqual(frame.move, (0.0, -1.0))
        self.assertEqual(frame.actions, frozenset({Action.SHOOT}))
        self.assertEqual(frame.held, frozenset({Action.SPRINT}))

    def test_neutral_frame(self):
        self.assertEqual(game_input.NEUTRAL,
                         InputFrame((0.0, 0.0), frozenset(), frozenset()))


class RebindingTest(unittest.TestCase):
    def test_custom_bindings_take_effect(self):
        bindings = KeyBindings(
            up=(pygame.K_i,), down=(pygame.K_k,),
            left=(pygame.K_j,), right=(pygame.K_l,),
            actions={Action.PASS: (pygame.K_SPACE,)})
        self.assertEqual(
            game_input.movement_vector(_pressed(pygame.K_i), bindings),
            (0.0, -1.0))
        # The default pass key no longer passes under the custom bindings...
        self.assertEqual(
            game_input.pressed_actions([_Event(pygame.KEYDOWN, pygame.K_j)], bindings),
            set())
        # ...the rebound key does.
        self.assertEqual(
            game_input.pressed_actions([_Event(pygame.KEYDOWN, pygame.K_SPACE)], bindings),
            {Action.PASS})


class EngineInputSeamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_default_player_input_is_none(self):
        from src.game_engine import GameEngine
        engine = GameEngine()
        self.assertIsNone(engine.player_input)

    def test_set_player_input_stores_frame(self):
        from src.game_engine import GameEngine
        engine = GameEngine()
        frame = game_input.read_input(_pressed(pygame.K_RIGHT), [])
        engine.set_player_input(frame)
        self.assertIs(engine.player_input, frame)


if __name__ == "__main__":
    unittest.main()
