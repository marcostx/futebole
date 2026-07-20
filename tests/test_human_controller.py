"""
Unit tests for the HumanController (Tier 5, task 3): the human steers one
selected player from the input vector while the team AI positions the rest,
and the selected player is fully excluded from AI movement and actions.
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.game_engine import GameEngine
from src.human_controller import HumanController
from src.input import Action, InputFrame

DT = 1.0 / 60


class HumanControllerSetupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_engine_builds_controller_for_human_team(self):
        engine = GameEngine(human_team="team1")
        self.assertIsInstance(engine.human_controller, HumanController)
        self.assertIs(engine.human_controller.team, engine.team1)

    def test_no_controller_when_all_ai(self):
        engine = GameEngine()
        self.assertIsNone(engine.human_controller)

    def test_default_selection_is_an_outfield_striker(self):
        engine = GameEngine(human_team="team1")
        sp = engine.human_controller.selected_player
        self.assertIsNotNone(sp)
        self.assertEqual(sp.role, "striker")
        self.assertFalse(sp.is_goalkeeper)
        self.assertIn(sp, engine.team1.players)


class HumanControllerMovementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _engine(self):
        engine = GameEngine(human_team="team1")
        return engine, engine.human_controller

    def test_input_steers_selected_player(self):
        engine, hc = self._engine()
        sp = hc.selected_player
        sp.vx = sp.vy = 0.0
        engine.set_player_input(InputFrame(move=(1.0, 0.0)))
        hc.update(DT)
        self.assertGreater(sp.vx, 0.0)                 # accelerating right
        self.assertAlmostEqual(sp.vy, 0.0, delta=1e-6)

    def test_idle_input_leaves_selected_player_uncommanded(self):
        engine, hc = self._engine()
        sp = hc.selected_player
        sp.vx, sp.vy = 42.0, 0.0                        # some prior velocity
        engine.set_player_input(InputFrame())           # neutral: move == (0, 0)
        hc.update(DT)
        # Neither the human nor the AI touched the selected player's velocity;
        # the engine's friction (applied elsewhere) decelerates it naturally.
        self.assertEqual((sp.vx, sp.vy), (42.0, 0.0))

    def test_missing_input_frame_is_safe(self):
        engine, hc = self._engine()
        engine.player_input = None                      # before first read
        hc.update(DT)                                   # must not raise

    def test_roster_is_restored_after_update(self):
        engine, hc = self._engine()
        before = list(engine.team1.players)
        engine.set_player_input(InputFrame(move=(0.0, 1.0)))
        hc.update(DT)
        self.assertEqual(engine.team1.players, before)  # same members & order


class HumanControllerExclusionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_ai_presser_excludes_the_controlled_player(self):
        engine = GameEngine(human_team="team1")
        hc = engine.human_controller
        engine.ball.possession = None                # loose ball -> defending
        engine.ball.x, engine.ball.y = 60, 300
        outfield = [p for p in engine.team1.players if not p.is_goalkeeper]
        for i, player in enumerate(outfield):
            player.x, player.y = 100 + i * 100, 300
        engine.set_player_input(InputFrame())
        hc.update(DT)
        # The human controls the closest player; the AI's active player is
        # someone else (the exclusion keeps the AI off the human's player).
        self.assertIs(hc.selected_player, outfield[0])
        self.assertIsNotNone(engine.team1_ai.active_player)
        self.assertIsNot(engine.team1_ai.active_player, outfield[0])

    def test_selected_player_is_excluded_from_ai_actions(self):
        engine = GameEngine(human_team="team1")
        hc = engine.human_controller
        sp = hc.selected_player
        # Put the selected player on the ball in a clear shooting position:
        # were it visible to the AI, execute_attack_behavior would shoot
        # (deterministic in range with a good angle). Exclusion must prevent it.
        sp.x, sp.y = 620, 300
        sp.action_cooldown = 0.0
        engine.ball.possession = sp
        engine.ball.loose_timer = 0.0
        engine.team1.shots = 0
        engine.set_player_input(InputFrame())

        hc.update(DT)

        self.assertIs(engine.ball.possession, sp)       # ball not kicked away
        self.assertEqual(engine.team1.shots, 0)         # no AI shot recorded


class DefensiveSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _defending_engine(self):
        """Human engine defending a free ball, with outfielders spread along x
        so distance-to-ball ordering is unambiguous (distances 50..450)."""
        engine = GameEngine(human_team="team1")
        engine.ball.possession = None                # free ball -> defending
        engine.ball.x, engine.ball.y = 50, 300
        outfield = [p for p in engine.team1.players if not p.is_goalkeeper]
        for i, player in enumerate(outfield):
            player.x, player.y = 100 + i * 100, 300
        return engine, engine.human_controller, outfield

    def test_auto_selects_closest_when_defending(self):
        engine, hc, outfield = self._defending_engine()
        engine.set_player_input(InputFrame())
        hc._update_selection()
        self.assertIs(hc.selected_player, outfield[0])

    def test_switch_selects_second_closest(self):
        engine, hc, outfield = self._defending_engine()
        engine.set_player_input(InputFrame())
        hc._update_selection()                       # closest
        engine.set_player_input(
            InputFrame(actions=frozenset({Action.SWITCH_PLAYER})))
        hc._update_selection()                       # second closest
        self.assertIs(hc.selected_player, outfield[1])

    def test_repeated_switches_cycle_in_distance_order(self):
        engine, hc, outfield = self._defending_engine()
        engine.set_player_input(InputFrame())
        hc._update_selection()
        seen = [hc.selected_player]
        for _ in range(len(outfield)):               # one extra: test wrap-around
            engine.set_player_input(
                InputFrame(actions=frozenset({Action.SWITCH_PLAYER})))
            hc._update_selection()
            seen.append(hc.selected_player)
        self.assertEqual(seen, outfield + [outfield[0]])

    def test_switch_is_debounced_to_one_advance_per_press(self):
        engine, hc, outfield = self._defending_engine()
        engine.set_player_input(
            InputFrame(actions=frozenset({Action.SWITCH_PLAYER})))
        hc._update_selection()                       # one press -> second closest
        self.assertIs(hc.selected_player, outfield[1])
        # Key still physically held but no new KEYDOWN => no further advances.
        for _ in range(3):
            engine.set_player_input(InputFrame())
            hc._update_selection()
        self.assertIs(hc.selected_player, outfield[1])

    def test_goalkeeper_is_excluded_while_defending(self):
        engine, hc, outfield = self._defending_engine()
        keeper = next(p for p in engine.team1.players if p.is_goalkeeper)
        engine.ball.x, engine.ball.y = keeper.x, keeper.y   # ball on the keeper
        engine.set_player_input(InputFrame())
        hc._update_selection()
        self.assertFalse(hc.selected_player.is_goalkeeper)
        self.assertIn(hc.selected_player, outfield)

    def test_goalkeeper_is_selected_while_holding_the_ball(self):
        engine, hc, _ = self._defending_engine()
        keeper = next(p for p in engine.team1.players if p.is_goalkeeper)
        engine.ball.possession = keeper
        engine.set_player_input(InputFrame())
        hc._update_selection()
        self.assertIs(hc.selected_player, keeper)

    def test_regaining_possession_snaps_to_carrier_and_resets_cycle(self):
        engine, hc, outfield = self._defending_engine()
        engine.set_player_input(
            InputFrame(actions=frozenset({Action.SWITCH_PLAYER})))
        hc._update_selection()                       # switched to 2nd-closest
        self.assertEqual(hc.switch_offset, 1)
        engine.ball.possession = outfield[2]         # a teammate wins the ball
        engine.set_player_input(InputFrame())
        hc._update_selection()
        self.assertEqual(hc.switch_offset, 0)        # cycle reset
        self.assertIs(hc.selected_player, outfield[2])  # control snaps to carrier

    def test_update_steers_the_auto_selected_defender(self):
        engine, hc, outfield = self._defending_engine()
        engine.set_player_input(InputFrame(move=(1.0, 0.0)))
        hc.update(DT)
        sp = hc.selected_player
        self.assertIs(sp, outfield[0])               # closest was auto-selected
        self.assertGreater(sp.vx, 0.0)               # and steered right


class AttackSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_controls_the_ball_carrier_while_in_possession(self):
        engine = GameEngine(human_team="team1")
        hc = engine.human_controller
        carrier = [p for p in engine.team1.players if not p.is_goalkeeper][2]
        engine.ball.possession = carrier
        hc._update_selection()
        self.assertIs(hc.selected_player, carrier)
        self.assertEqual(hc.switch_offset, 0)

    def test_teammates_stay_in_attack_when_human_carries_the_ball(self):
        # Regression for the PR #30/#31 finding: the old roster-removal trick
        # made the team read its own possession as the opponent's and defend.
        engine = GameEngine(human_team="team1")
        hc = engine.human_controller
        sp = hc.selected_player
        engine.ball.possession = sp
        engine.ball.loose_timer = 0.0
        engine.set_player_input(InputFrame())
        hc.update(DT)
        self.assertEqual(engine.team1_ai.team_state, "attack")

    def test_ai_leaves_the_controlled_carrier_but_moves_teammates(self):
        engine = GameEngine(human_team="team1")
        hc = engine.human_controller
        sp = hc.selected_player
        engine.ball.possession = sp
        engine.ball.loose_timer = 0.0
        for player in engine.team1.players:
            player.vx = player.vy = 0.0
        engine.set_player_input(InputFrame())        # no human movement
        hc.update(DT)
        self.assertEqual((sp.vx, sp.vy), (0.0, 0.0))  # AI left the carrier alone
        teammates = [p for p in engine.team1.players if p is not sp]
        self.assertTrue(any(p.vx or p.vy for p in teammates))  # AI moved others

    def test_controlled_player_flag_is_set_on_the_ai(self):
        engine = GameEngine(human_team="team1")
        hc = engine.human_controller
        engine.set_player_input(InputFrame())
        hc.update(DT)
        self.assertIs(engine.team1_ai.controlled_player, hc.selected_player)


class OnBallActionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _carrier_engine(self):
        """Human engine with the selected player on the ball in midfield,
        off cooldown, with room to pass or shoot."""
        engine = GameEngine(human_team="team1")
        hc = engine.human_controller
        sp = hc.selected_player
        sp.x, sp.y = 400, 300
        sp.action_cooldown = 0.0
        engine.ball.possession = sp
        engine.ball.loose_timer = 0.0
        return engine, hc, sp

    def test_shoot_releases_the_ball_and_counts_a_shot(self):
        engine, hc, sp = self._carrier_engine()
        engine.team1.shots = 0
        engine.set_player_input(InputFrame(actions=frozenset({Action.SHOOT})))
        hc.update(DT)
        self.assertIsNone(engine.ball.possession)        # ball was kicked
        self.assertGreater(engine.ball.loose_timer, 0.0)  # in flight
        self.assertEqual(engine.team1.shots, 1)
        self.assertGreater(engine.ball.vx, 0.0)          # toward the right goal

    def test_pass_goes_to_a_teammate_in_the_aim_direction(self):
        engine, hc, sp = self._carrier_engine()
        outfield = [p for p in engine.team1.players
                    if p is not sp and not p.is_goalkeeper]
        mate = outfield[0]
        mate.x, mate.y = 500, 260                         # up-and-right of carrier
        for other in outfield[1:]:
            other.x, other.y = 200, 520                   # far, behind the carrier
        engine.set_player_input(
            InputFrame(move=(1.0, 0.0), actions=frozenset({Action.PASS})))
        hc.update(DT)
        self.assertIsNone(engine.ball.possession)         # ball released
        self.assertGreater(engine.ball.vx, 0.0)           # toward the aimed mate

    def test_actions_require_holding_the_ball(self):
        engine, hc, sp = self._carrier_engine()
        engine.ball.possession = None                     # not on the ball
        engine.team1.shots = 0
        engine.set_player_input(InputFrame(actions=frozenset({Action.SHOOT})))
        hc.update(DT)
        self.assertEqual(engine.team1.shots, 0)

    def test_actions_are_gated_by_the_cooldown(self):
        engine, hc, sp = self._carrier_engine()
        sp.action_cooldown = 0.5                          # just kicked
        engine.team1.shots = 0
        engine.set_player_input(InputFrame(actions=frozenset({Action.SHOOT})))
        hc.update(DT)
        self.assertEqual(engine.team1.shots, 0)           # cooldown blocks it
        self.assertIs(engine.ball.possession, sp)         # still on the ball

    def test_sprint_increases_movement_speed(self):
        engine, hc, sp = self._carrier_engine()
        sp.vx = sp.vy = 0.0
        engine.set_player_input(InputFrame(move=(1.0, 0.0)))
        hc.update(DT)
        jog_vx = sp.vx

        engine2, hc2, sp2 = self._carrier_engine()
        sp2.vx = sp2.vy = 0.0
        engine2.set_player_input(
            InputFrame(move=(1.0, 0.0), held=frozenset({Action.SPRINT})))
        hc2.update(DT)
        sprint_vx = sp2.vx

        self.assertGreater(sprint_vx, jog_vx)


if __name__ == "__main__":
    unittest.main()
