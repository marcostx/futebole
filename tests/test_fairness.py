"""
Fairness invariants for human control (Tier 5): the human-controlled player is
subject to the same central possession contest as every AI player. The human
only supplies movement and actions; it never assigns possession, never bypasses
the restart entitlement, and wins/loses the ball by the same rules.

(Offside is not engine-enforced — it is only an AI pass heuristic in ai.py —
so there is no offside whistle for the human to bypass. Fouls book the fouler
with an action cooldown, and the human's actions are cooldown-gated too; that
gating is covered in test_human_controller.OnBallActionsTest.)
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.game_engine import GameEngine
from src.input import InputFrame

DT = 1.0 / 60


class HumanPossessionFairnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _engine(self):
        engine = GameEngine(human_team="team1")
        engine.kickoff_pending = False   # skip the scripted kickoff pass
        return engine, engine.human_controller

    @staticmethod
    def _isolate(engine, ball_xy, near):
        """Put the ball at `ball_xy`, park everyone far away, then place the
        `near` players at their given spots; clear cooldowns and loose timer."""
        engine.ball.x, engine.ball.y = ball_xy
        engine.ball.loose_timer = 0.0
        for player in engine.team1.players + engine.team2.players:
            player.x, player.y = 100, 520
            player.action_cooldown = 0.0
        for player, (x, y) in near.items():
            player.x, player.y = x, y

    def test_human_controller_never_assigns_possession(self):
        # An opponent holds the ball right next to the human's player; running
        # the human controller must not hand possession to the human. Only the
        # engine's central contest may change possession.
        engine, hc = self._engine()
        sp = hc.selected_player
        opponent = engine.team2.players[0]
        self._isolate(engine, (403, 300), {sp: (400, 300), opponent: (402, 300)})
        engine.ball.possession = opponent
        engine.set_player_input(InputFrame(move=(1.0, 0.0)))

        hc.update(DT)

        self.assertIs(engine.ball.possession, opponent)

    def test_free_ball_is_not_privileged_to_the_human(self):
        # Free ball with an opponent closer than the human's player: the
        # central contest awards it to the nearer opponent, not the human.
        engine, hc = self._engine()
        sp = hc.selected_player
        opponent = engine.team2.players[0]
        self._isolate(engine, (400, 300), {opponent: (403, 300), sp: (418, 300)})
        engine.ball.possession = None

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, opponent)

    def test_human_can_win_a_free_ball_by_the_same_rule(self):
        # Same contest, human's player closest -> it wins, exactly like any AI.
        engine, hc = self._engine()
        sp = hc.selected_player
        opponent = engine.team2.players[0]
        self._isolate(engine, (400, 300), {sp: (403, 300), opponent: (418, 300)})
        engine.ball.possession = None

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, sp)

    def test_human_cannot_take_an_opponents_restart(self):
        # A restart is awarded to the opponent (team2). Even with the human's
        # player closest to the dead ball, it may not take it.
        engine, hc = self._engine()
        sp = hc.selected_player
        self._isolate(engine, (400, 300), {sp: (402, 300)})
        engine.ball.possession = None
        engine.restart_team = engine.team2

        engine.resolve_possession()

        self.assertNotIn(engine.ball.possession, engine.team1.players)

    def test_human_can_take_its_own_teams_restart(self):
        # When the human's team is entitled, its nearest player takes the
        # restart through the same contest (no special-casing either way).
        engine, hc = self._engine()
        sp = hc.selected_player
        self._isolate(engine, (400, 300), {sp: (402, 300)})
        engine.ball.possession = None
        engine.restart_team = engine.team1

        engine.resolve_possession()

        self.assertIs(engine.ball.possession, sp)


if __name__ == "__main__":
    unittest.main()
