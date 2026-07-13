"""
Unit tests for rest defense (Tier 5 #2).

While the team attacks, its defenders do not join the push: they hold a
flat cover line goal-side of the ball (trailing it by REST_GAP, bounded so
it never collapses onto the keeper nor crosses the halfway area), and they
are exempt from support-runner duty. A turnover therefore always finds
defenders (plus the keeper) between the ball and the goal.
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src.ai import (AIController, BANK_SPACING, REST_GAP, REST_MAX_DEPTH,
                    REST_MIN_DEPTH)
from src.entities import Ball, Player, Team


def _add_player(team, name, x, y, role="field"):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    p.role = role
    if role == "goalkeeper":
        p.is_goalkeeper = True
    team.add_player(p)
    return p


def _attack_scenario(carrier_xy=(500.0, 300.0)):
    """Team 1 (attacks right, defends the left goal at x=50) in possession."""
    team = Team("Team 1", (255, 0, 0))
    d1 = _add_player(team, "T1P1", 176.0, 225.0, "defender")
    d2 = _add_player(team, "T1P2", 176.0, 375.0, "defender")
    m1 = _add_player(team, "T1P3", 330.0, 200.0, "midfielder")
    st = _add_player(team, "T1P5", *carrier_xy, "striker")
    _add_player(team, "T1GK", 71.0, 300.0, "goalkeeper")
    
    opp = Team("Team 2", (0, 0, 255))
    _add_player(opp, "T2GK", 729.0, 300.0, "goalkeeper")
    
    ball = Ball(st.x, st.y)
    ball.possession = st
    ai = AIController(team, opp, ball)
    ai.team_state = "attack"
    ai.active_player = st
    return ai, (d1, d2), m1, st, ball


def _velocity_angle_towards(entity, target_x, target_y):
    speed = math.hypot(entity.vx, entity.vy)
    dx, dy = target_x - entity.x, target_y - entity.y
    dist = math.hypot(dx, dy)
    if speed == 0 or dist == 0:
        return math.pi
    cos = (entity.vx * dx + entity.vy * dy) / (speed * dist)
    return math.acos(max(-1.0, min(1.0, cos)))


class RestLineGeometryTest(unittest.TestCase):
    def test_cover_line_is_flat_and_trails_the_ball(self):
        ai, (d1, d2), _, _, ball = _attack_scenario(carrier_xy=(500.0, 300.0))
        pos = ai._rest_defense_positions()

        self.assertAlmostEqual(pos[d1][0], pos[d2][0])  # flat line
        # Goal-side of the ball by the configured gap (ball depth 450).
        self.assertAlmostEqual(pos[d1][0], 50.0 + (450.0 - REST_GAP))

    def test_line_never_pushes_past_the_max_depth(self):
        ai, (d1, _), _, _, ball = _attack_scenario(carrier_xy=(700.0, 300.0))
        pos = ai._rest_defense_positions()
        self.assertAlmostEqual(pos[d1][0] - 50.0, REST_MAX_DEPTH)

    def test_line_never_collapses_onto_the_keeper(self):
        ai, (d1, _), _, _, ball = _attack_scenario(carrier_xy=(150.0, 300.0))
        pos = ai._rest_defense_positions()
        self.assertAlmostEqual(pos[d1][0] - 50.0, REST_MIN_DEPTH)

    def test_line_slides_gently_with_the_ball_without_slot_swaps(self):
        ai, (d1, d2), _, _, ball = _attack_scenario()
        ball.y = 150.0
        top = ai._rest_defense_positions()
        ball.y = 450.0
        bottom = ai._rest_defense_positions()

        self.assertLess(top[d1][1], bottom[d1][1])  # follows the ball
        self.assertAlmostEqual(top[d2][1] - top[d1][1], BANK_SPACING)
        self.assertLess(top[d1][1], top[d2][1])  # d1 keeps the higher slot

    def test_defender_carrying_the_ball_is_exempt(self):
        ai, (d1, d2), _, _, ball = _attack_scenario()
        ball.possession = d1  # a defender brings the ball out

        pos = ai._rest_defense_positions()

        self.assertNotIn(d1, pos)
        self.assertIn(d2, pos)  # the other defender still covers


class RestDefenseBehaviorTest(unittest.TestCase):
    def test_defenders_hold_the_cover_line_during_attack(self):
        ai, (d1, d2), _, striker, ball = _attack_scenario()

        ai.execute_attack_behavior(1 / 60)

        pos = ai._rest_defense_positions()
        for d in (d1, d2):
            angle = _velocity_angle_towards(d, *pos[d])
            self.assertLess(angle, 0.01)

    def test_defenders_stay_goal_side_over_time(self):
        # Integrate an attack deep in the opponent half: the defenders must
        # end up (and stay) between the ball and our own goal.
        ai, (d1, d2), _, striker, ball = _attack_scenario(carrier_xy=(650.0, 300.0))
        for _ in range(240):
            ai.execute_attack_behavior(1 / 60)
            for p in ai.team.players:
                p.update(1 / 60)
            striker.vx = striker.vy = 0.0  # keep the carrier planted
            ball.x, ball.y = striker.x, striker.y

        for d in (d1, d2):
            self.assertLess(d.x, ball.x)  # goal-side of the ball
            self.assertLessEqual(d.x - 50.0, REST_MAX_DEPTH + 5)

    def test_defenders_are_never_the_support_runner(self):
        ai, (d1, d2), mid, striker, ball = _attack_scenario()
        # Put a defender nearest to the carrier: it must still not be picked.
        d1.x, d1.y = striker.x - 30, striker.y

        ai.update(1 / 60)

        self.assertEqual(ai.team_state, "attack")
        self.assertIsNot(ai.support_player, d1)
        self.assertIsNot(ai.support_player, d2)
        self.assertIs(ai.support_player, mid)


if __name__ == "__main__":
    unittest.main()
