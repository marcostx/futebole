"""
Unit tests for role-based home positions and team-shape holding (Tier 2 #2).
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.ai import (AIController, FIELD_CENTER_X, FIELD_CENTER_Y,
                    FIELD_MAX_X, FIELD_MAX_Y, FIELD_MIN_X, FIELD_MIN_Y,
                    SHAPE_SLIDE)
from src.entities import Ball, Player, Team


class RolesAndHomeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _engine(self):
        from src.game_engine import GameEngine
        return GameEngine()

    def test_each_player_has_a_role_and_home_in_field(self):
        engine = self._engine()
        for p in engine.team1.players + engine.team2.players:
            self.assertIn(p.role, ("defender", "midfielder", "striker"))
            self.assertGreaterEqual(p.home_x, engine.field_x)
            self.assertLessEqual(p.home_x, engine.field_x + engine.field_width)
            self.assertGreaterEqual(p.home_y, engine.field_y)
            self.assertLessEqual(p.home_y, engine.field_y + engine.field_height)

    def test_formation_role_counts(self):
        engine = self._engine()
        for team in (engine.team1, engine.team2):
            roles = [p.role for p in team.players]
            self.assertEqual(roles.count("defender"), 2)
            self.assertEqual(roles.count("midfielder"), 2)
            self.assertEqual(roles.count("striker"), 1)

    def test_teams_mirror_horizontally(self):
        engine = self._engine()
        # Team 1 defenders sit on the left, Team 2 defenders on the right.
        t1_def = [p for p in engine.team1.players if p.role == "defender"][0]
        t2_def = [p for p in engine.team2.players if p.role == "defender"][0]
        self.assertLess(t1_def.home_x, FIELD_CENTER_X)
        self.assertGreater(t2_def.home_x, FIELD_CENTER_X)

    def test_reset_positions_sends_players_home(self):
        engine = self._engine()
        p = engine.team1.players[0]
        p.x, p.y = 123.0, 456.0
        engine.reset_positions()
        self.assertAlmostEqual(p.x, p.home_x)
        self.assertAlmostEqual(p.y, p.home_y)


class FormationPositionTest(unittest.TestCase):
    def _ai_with_player(self, home_x=200.0, home_y=200.0):
        team = Team("Team 1", (255, 0, 0))
        player = Player("P", home_x, home_y, team.color)
        player.home_x, player.home_y = home_x, home_y
        team.add_player(player)
        opp = Team("Team 2", (0, 0, 255))
        opp.add_player(Player("O", 600.0, 300.0, opp.color))
        ball = Ball(FIELD_CENTER_X, FIELD_CENTER_Y)
        return AIController(team, opp, ball), player, ball

    def test_holds_home_when_ball_centered(self):
        ai, player, ball = self._ai_with_player()
        ai.team_state = "possession"  # no attack push / defense drop
        ball.x, ball.y = FIELD_CENTER_X, FIELD_CENTER_Y
        tx, ty = ai.formation_position(player)
        self.assertAlmostEqual(tx, player.home_x)
        self.assertAlmostEqual(ty, player.home_y)

    def test_slides_toward_the_ball(self):
        ai, player, ball = self._ai_with_player(home_x=200.0, home_y=300.0)
        ai.team_state = "possession"  # isolate the shape-slide component
        ball.x, ball.y = 600.0, 300.0  # ball to the right of center
        tx, ty = ai.formation_position(player)
        expected_x = player.home_x + (ball.x - FIELD_CENTER_X) * SHAPE_SLIDE
        self.assertAlmostEqual(tx, expected_x)
        self.assertGreater(tx, player.home_x)  # shifted toward the ball

    def test_attack_pushes_forward_defense_drops_back(self):
        ai, player, ball = self._ai_with_player(home_x=300.0, home_y=300.0)
        ball.x, ball.y = FIELD_CENTER_X, FIELD_CENTER_Y  # isolate the push/drop

        ai.team_state = "possession"
        base_x, _ = ai.formation_position(player)
        ai.team_state = "attack"
        attack_x, _ = ai.formation_position(player)
        ai.team_state = "defense"
        defense_x, _ = ai.formation_position(player)

        # Team 1 attacks toward +x and defends toward -x.
        self.assertGreater(attack_x, base_x)
        self.assertLess(defense_x, base_x)

    def test_target_is_clamped_to_field(self):
        ai, player, ball = self._ai_with_player(home_x=FIELD_MAX_X, home_y=FIELD_MAX_Y)
        ball.x, ball.y = FIELD_MAX_X, FIELD_MAX_Y  # extreme corner
        tx, ty = ai.formation_position(player)
        self.assertLessEqual(tx, FIELD_MAX_X)
        self.assertGreaterEqual(tx, FIELD_MIN_X)
        self.assertLessEqual(ty, FIELD_MAX_Y)
        self.assertGreaterEqual(ty, FIELD_MIN_Y)


if __name__ == "__main__":
    unittest.main()
