"""
Unit tests for visual polish (Tier 4): HUD match stats and rendering marks.

Teams accumulate possession time and shot counts for the HUD; goalkeeper
clearances are not counted as shots. Rendering (keeper ring, carrier halo,
stats bar) is smoke-tested headlessly.
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.ai import AIController
from src.entities import Ball, Player, Team
from src.game_engine import GameEngine
from src.ui import UI


def _quiet_engine():
    engine = GameEngine()
    engine.team1_ai.update = lambda dt: None
    engine.team2_ai.update = lambda dt: None
    for i, p in enumerate(engine.team1.players + engine.team2.players):
        p.x, p.y = 10000.0 + i * 100, 10000.0
        p.action_cooldown = 0.0
    engine.ball.x, engine.ball.y = 400.0, 300.0
    engine.ball.possession = None
    engine.ball.last_toucher = None
    return engine


class PossessionTimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_update_accumulates_holder_team_time(self):
        engine = _quiet_engine()
        holder = engine.team1.players[0]
        holder.x, holder.y = engine.ball.x, engine.ball.y
        engine.ball.possession = holder

        # Drive update() with a controlled virtual clock (~0.5s in 60Hz steps).
        now = {"t": pygame.time.get_ticks()}
        orig_ticks = pygame.time.get_ticks
        pygame.time.get_ticks = lambda: now["t"]
        try:
            engine.last_update_time = now["t"]
            for _ in range(30):
                now["t"] += 16
                engine.update()
        finally:
            pygame.time.get_ticks = orig_ticks

        self.assertAlmostEqual(engine.team1.possession_time, 0.48, delta=0.05)
        self.assertEqual(engine.team2.possession_time, 0.0)

    def test_percentages_split_and_handle_no_possession(self):
        t1 = Team("Team 1", (255, 0, 0))
        t2 = Team("Team 2", (0, 0, 255))
        self.assertEqual(UI.possession_percentages(t1, t2), (0, 0))

        t1.possession_time = 30.0
        t2.possession_time = 10.0
        self.assertEqual(UI.possession_percentages(t1, t2), (75, 25))


class ShotCountTest(unittest.TestCase):
    def _attack_ai(self, carrier_xy):
        team = Team("Team 1", (255, 0, 0))
        carrier = Player("T1P1", *carrier_xy, team.color)
        team.add_player(carrier)
        opp = Team("Team 2", (0, 0, 255))
        ball = Ball(carrier.x, carrier.y)
        ball.possession = carrier
        ai = AIController(team, opp, ball)
        ai.team_state = "attack"
        ai.active_player = carrier
        return ai, carrier, ball

    def test_attack_shot_increments_team_shots(self):
        ai, carrier, ball = self._attack_ai((650.0, 300.0))  # in range, wide angle

        ai.execute_attack_behavior(1 / 60)

        self.assertIsNone(ball.possession)  # shot fired
        self.assertEqual(ai.team.shots, 1)

    def test_out_of_range_carrier_does_not_count_a_shot(self):
        ai, carrier, ball = self._attack_ai((300.0, 300.0))

        ai.execute_attack_behavior(1 / 60)

        self.assertEqual(ai.team.shots, 0)

    def test_keeper_clearance_is_not_a_shot(self):
        team = Team("Team 1", (255, 0, 0))
        keeper = Player("T1GK", 71.0, 300.0, team.color)
        keeper.is_goalkeeper = True
        keeper.role = "goalkeeper"
        team.add_player(keeper)
        opp = Team("Team 2", (0, 0, 255))
        ball = Ball(keeper.x, keeper.y)
        ball.possession = keeper
        ai = AIController(team, opp, ball)

        ai._goalkeeper_distribute(keeper)  # no pass option: boots it clear

        self.assertIsNone(ball.possession)  # clearance kicked
        self.assertEqual(team.shots, 0)

    def test_reset_game_clears_stats(self):
        pygame.init()
        engine = _quiet_engine()
        engine.team1.shots = 5
        engine.team2.possession_time = 12.0

        engine.reset_game()

        self.assertEqual(engine.team1.shots, 0)
        self.assertEqual(engine.team2.possession_time, 0.0)


class RenderSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_render_with_carrier_keeper_and_stats(self):
        engine = _quiet_engine()
        carrier = engine.team1.players[0]
        carrier.x, carrier.y = 400.0, 300.0
        engine.ball.possession = carrier
        engine.team1.possession_time = 10.0
        engine.team1.shots = 3

        engine.render()  # must draw halo, keeper rings, and HUD without errors

        # Sanity: the HUD bar area was painted over (not field green).
        pixel = engine.screen.get_at((5, engine.HEIGHT - 5))
        self.assertEqual((pixel.r, pixel.g, pixel.b), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
