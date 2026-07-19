"""
Input Module
Maps raw keyboard state to semantic gameplay actions for the human-controlled
team (Tier 5). The engine and controllers never look at raw key codes; they
consume the semantic :class:`Action` values and the movement vector produced
here, so the bindings are rebindable and the whole layer is unit-testable
without opening a window.

Two kinds of input are exposed:

* Movement — a continuous 8-direction unit vector read from *held* keys
  (arrows and/or WASD) via ``pygame.key.get_pressed()``.
* Actions — discrete intents mapped from keys. ``pressed_actions`` reads
  edge-triggered presses from a frame's KEYDOWN events (pass, shoot, switch
  player, and also sprint if a key-down happens), while ``held_actions``
  reports which action keys are currently held (used for sprint, which is a
  hold-to-run modifier rather than a one-shot press).
"""

import enum
import math

import pygame


class Action(enum.Enum):
    """Semantic gameplay intents the human can trigger."""
    PASS = "pass"
    SHOOT = "shoot"
    SPRINT = "sprint"
    SWITCH_PLAYER = "switch_player"


class KeyBindings:
    """Rebindable map from physical keys to movement directions and actions.

    Each direction and each action maps to a *tuple* of key codes so several
    keys can trigger the same intent (e.g. both the arrows and WASD move, and
    either shift key sprints).
    """

    def __init__(self, up, down, left, right, actions):
        self.up = tuple(up)
        self.down = tuple(down)
        self.left = tuple(left)
        self.right = tuple(right)
        # Action -> tuple of key codes.
        self.actions = {action: tuple(keys) for action, keys in actions.items()}


# Default control scheme. Movement uses the arrows and WASD; action keys are
# chosen to avoid the movement keys and the system keys handled in main.py
# (ESC quit, SPACE pause, R reset).
DEFAULT_BINDINGS = KeyBindings(
    up=(pygame.K_UP, pygame.K_w),
    down=(pygame.K_DOWN, pygame.K_s),
    left=(pygame.K_LEFT, pygame.K_a),
    right=(pygame.K_RIGHT, pygame.K_d),
    actions={
        Action.PASS: (pygame.K_j,),
        Action.SHOOT: (pygame.K_k,),
        Action.SPRINT: (pygame.K_LSHIFT, pygame.K_RSHIFT),
        Action.SWITCH_PLAYER: (pygame.K_TAB,),
    },
)


class InputFrame:
    """One frame of resolved human input.

    * ``move``: an ``(dx, dy)`` unit vector (screen space, +y is down), or
      ``(0.0, 0.0)`` when no direction is held.
    * ``actions``: the set of edge-triggered :class:`Action` presses this
      frame (consumed one-shot: pass, shoot, switch player).
    * ``held``: the set of :class:`Action` values whose key is currently held
      (used for the sprint hold modifier).
    """

    __slots__ = ("move", "actions", "held")

    def __init__(self, move=(0.0, 0.0), actions=frozenset(), held=frozenset()):
        self.move = move
        self.actions = frozenset(actions)
        self.held = frozenset(held)

    def __eq__(self, other):
        return (isinstance(other, InputFrame)
                and self.move == other.move
                and self.actions == other.actions
                and self.held == other.held)

    def __repr__(self):
        return (f"InputFrame(move={self.move}, actions={set(self.actions)}, "
                f"held={set(self.held)})")


# A no-input frame; a convenient default before any input is read.
NEUTRAL = InputFrame()


def _any_pressed(pressed, keys):
    """Whether any key in `keys` is down in a `pygame.key.get_pressed()`-like
    sequence (any object indexable by key code, e.g. a ``defaultdict(bool)``
    in tests)."""
    return any(pressed[key] for key in keys)


def movement_vector(pressed, bindings=DEFAULT_BINDINGS):
    """Resolve held direction keys into an 8-direction unit vector.

    Opposing keys on an axis cancel out; diagonals are normalised so moving
    diagonally is not faster than moving straight.
    """
    dx = float(_any_pressed(pressed, bindings.right)) \
        - float(_any_pressed(pressed, bindings.left))
    dy = float(_any_pressed(pressed, bindings.down)) \
        - float(_any_pressed(pressed, bindings.up))
    if dx == 0.0 and dy == 0.0:
        return (0.0, 0.0)
    magnitude = math.hypot(dx, dy)
    return (dx / magnitude, dy / magnitude)


def _key_to_actions(bindings):
    """Reverse index: key code -> list of actions bound to it."""
    index = {}
    for action, keys in bindings.actions.items():
        for key in keys:
            index.setdefault(key, []).append(action)
    return index


def pressed_actions(events, bindings=DEFAULT_BINDINGS):
    """Edge-triggered actions from this frame's events (KEYDOWN only).

    `events` is any iterable of objects exposing ``.type`` and ``.key`` (real
    pygame events, or lightweight stubs in tests). Non-KEYDOWN events and
    unbound keys are ignored.
    """
    index = _key_to_actions(bindings)
    triggered = set()
    for event in events:
        if event.type != pygame.KEYDOWN:
            continue
        triggered.update(index.get(event.key, ()))
    return triggered


def held_actions(pressed, bindings=DEFAULT_BINDINGS):
    """Actions whose bound key is currently held (used for the sprint modifier)."""
    return {action for action, keys in bindings.actions.items()
            if _any_pressed(pressed, keys)}


def read_input(pressed, events, bindings=DEFAULT_BINDINGS):
    """Build the :class:`InputFrame` for one frame from held keys and events."""
    return InputFrame(
        move=movement_vector(pressed, bindings),
        actions=pressed_actions(events, bindings),
        held=held_actions(pressed, bindings),
    )
