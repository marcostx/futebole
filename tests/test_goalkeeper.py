"""
Unit tests for the goalkeeper role (Tier 3 #4).

Each team fields one goalkeeper that never presses or supports, holds its
goal line tracking the ball's height (clamped to the goal mouth), rushes a
threatening ball near its own goal, and distributes (pass or long clearance)
when it wins the ball.
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.ai import (AIController, GK_MOUTH_MARGIN, GK_RUSH_DIST,
                    GOAL_MOUTH_BOTTOM, GOAL_MOUTH_TOP)
from src.entities import Ball, Player, Team


def _velocity_angle_towards(entity, target_x, target_y):
    """Angle (rad) between the entity's velocity and the direction to target."""
    speed = math.hypot(entity.vx, entity.vy)
    dx, dy = target_x - entity.x, target_y - entity.y
    dist = math.hypot(dx, dy)
    if speed == 0 or dist == 0:
        return math.pi
    cos = (entity.vx * dx + entity.vy * dy) / (speed * dist)
    return math.acos(max(-1.0, min(1.0, cos)))


def _make_player(team, name, x, y, *, goalkeeper=False):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    if goalkeeper:
        p.is_goalkeeper = True
        p.role = "goalkeeper"
    team.add_player(p)
    return p


def _keeper_scenario(keeper_xy=(71.0, 300.0)):
    """Team 1 (defends the left goal at x=50) with one goalkeeper."""
    team = Team("Team 1", (255, 0, 0))
    keeper = _make_player(team, "T1GK", *keeper_xy, goalkeeper=True)
    opp = Team("Team 2", (0, 0, 255))
    ball = Ball(400.0, 300.0)
    ai = AIController(team, opp, ball)
    return ai, keeper, ball


class GoalkeeperLineTest(unittest.TestCase):
    def test_holds_line_tracking_ball_height(self):
        ai, keeper, ball = _keeper_scenario(keeper_xy=(71.0, 250.0))
        mate = _make_player(ai.team, "T1P2", 400.0, 300.0)
        ball.x, ball.y = mate.x, mate.y
        ball.possession = mate  # safely ours: keeper stays home

        ai._update_goalkeeper(keeper, 1 / 60)

        # Moving toward (home_x, ball.y) = (71, 300): straight down.
        angle = _velocity_angle_towards(keeper, keeper.home_x, ball.y)
        self.assertLess(angle, 0.01)

    def test_tracking_is_clamped_to_the_goal_mouth(self):
        ai, keeper, ball = _keeper_scenario(keeper_xy=(71.0, 100.0))
        ball.x, ball.y = 400.0, 60.0  # far ball, well above the goal mouth
        ball.possession = None

        ai._update_goalkeeper(keeper, 1 / 60)

        # Unclamped tracking would move up (toward y=60); the clamped target
        # (GOAL_MOUTH_TOP + margin = 210) is below the keeper, so it moves down.
        expected_y = GOAL_MOUTH_TOP + GK_MOUTH_MARGIN
        angle = _velocity_angle_towards(keeper, keeper.home_x, expected_y)
        self.assertLess(angle, 0.01)
        self.assertGreater(keeper.vy, 0.0)

    def test_mouth_constants_match_engine_goal_mouth(self):
        from src.game_engine import GameEngine
        pygame.init()
        engine = GameEngine()
        top, bottom = engine.goal_mouth()
        self.assertAlmostEqual(top, GOAL_MOUTH_TOP)
        self.assertAlmostEqual(bottom, GOAL_MOUTH_BOTTOM)


class GoalkeeperRushTest(unittest.TestCase):
    def test_rushes_loose_ball_near_own_goal(self):
        ai, keeper, ball = _keeper_scenario(keeper_xy=(71.0, 380.0))
        ball.x, ball.y = 100.0, 300.0  # 50px from own goal center
        ball.possession = None

        ai._update_goalkeeper(keeper, 1 / 60)

        angle = _velocity_angle_towards(keeper, ball.x, ball.y)
        self.assertLess(angle, 0.01)

    def test_rushes_opponent_carrier_near_own_goal(self):
        ai, keeper, ball = _keeper_scenario(keeper_xy=(71.0, 380.0))
        raider = _make_player(ai.opponent_team, "T2P1", 110.0, 300.0)
        ball.x, ball.y = raider.x, raider.y
        ball.possession = raider

        ai._update_goalkeeper(keeper, 1 / 60)

        angle = _velocity_angle_towards(keeper, ball.x, ball.y)
        self.assertLess(angle, 0.01)

    def test_does_not_rush_a_distant_ball(self):
        ai, keeper, ball = _keeper_scenario(keeper_xy=(71.0, 300.0))
        ball.x, ball.y = 400.0, 300.0  # 350px away, > GK_RUSH_DIST
        ball.possession = None
        self.assertGreater(math.hypot(ball.x - 50.0, ball.y - 300.0), GK_RUSH_DIST)

        ai._update_goalkeeper(keeper, 1 / 60)

        # Holding the line at home, not sprinting to the ball.
        angle_to_ball = _velocity_angle_towards(keeper, ball.x, ball.y)
        self.assertGreater(angle_to_ball, 0.1)


class GoalkeeperDistributionTest(unittest.TestCase):
    def test_passes_to_open_teammate(self):
        ai, keeper, ball = _keeper_scenario()
        mate = _make_player(ai.team, "T1P2", keeper.x + 100, keeper.y)
        ball.x, ball.y = keeper.x, keeper.y
        ball.possession = keeper

        ai._update_goalkeeper(keeper, 1 / 60)

        self.assertIsNone(ball.possession)
        self.assertGreater(ball.loose_timer, 0.0)
        self.assertGreater(ball.vx, 0.0)  # toward the teammate upfield

    def test_clears_long_when_no_pass_is_open(self):
        ai, keeper, ball = _keeper_scenario()
        # A teammate whose lane is blocked by an opponent: no pass option.
        _make_player(ai.team, "T1P2", keeper.x + 100, keeper.y)
        _make_player(ai.opponent_team, "T2P1", keeper.x + 50, keeper.y)
        ball.x, ball.y = keeper.x, keeper.y
        ball.possession = keeper
        self.assertIsNone(ai._best_pass_target(keeper))

        ai._update_goalkeeper(keeper, 1 / 60)

        # Booted upfield (+x for Team 1), released and in flight.
        self.assertIsNone(ball.possession)
        self.assertGreater(ball.loose_timer, 0.0)
        self.assertGreater(ball.vx, 0.0)

    def test_holds_still_on_cooldown_instead_of_dribbling_out(self):
        ai, keeper, ball = _keeper_scenario()
        _make_player(ai.team, "T1P2", keeper.x + 100, keeper.y)
        ball.x, ball.y = keeper.x, keeper.y
        ball.possession = keeper
        keeper.action_cooldown = 0.5
        keeper.vx = keeper.vy = 50.0

        ai._update_goalkeeper(keeper, 1 / 60)

        self.assertIs(ball.possession, keeper)
        self.assertEqual(keeper.vx, 0)
        self.assertEqual(keeper.vy, 0)


class GoalkeeperRoleAssignmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_keeper_never_presses_even_when_nearest(self):
        ai, keeper, ball = _keeper_scenario(keeper_xy=(300.0, 300.0))
        outfielder = _make_player(ai.team, "T1P2", 600.0, 300.0)
        carrier = _make_player(ai.opponent_team, "T2P1", 310.0, 300.0)
        ball.x, ball.y = carrier.x, carrier.y
        ball.possession = carrier  # they have it: defense state

        ai.update(1 / 60)

        self.assertEqual(ai.team_state, "defense")
        self.assertIs(ai.active_player, outfielder)

    def test_keeper_never_supports_the_carrier(self):
        ai, keeper, ball = _keeper_scenario(keeper_xy=(71.0, 300.0))
        carrier = _make_player(ai.team, "T1P2", 100.0, 300.0)
        far_mate = _make_player(ai.team, "T1P3", 600.0, 300.0)
        _make_player(ai.opponent_team, "T2P1", 700.0, 300.0)
        ball.x, ball.y = carrier.x, carrier.y
        ball.possession = carrier  # we have it: attack state

        ai.update(1 / 60)

        self.assertEqual(ai.team_state, "attack")
        # The keeper is nearest to the carrier but must not be the support.
        self.assertIs(ai.support_player, far_mate)


if __name__ == "__main__":
    unittest.main()
