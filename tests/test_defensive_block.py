"""
Unit tests for the defensive block (Tier 5 #1: "two banks").

Out of possession (and outside the man-marking threat zone), defenders and
midfielders hold two flat lines: the defender bank deeper, the midfielder
bank ahead of it. Line depth tracks the ball's distance from our goal, the
gap between banks compresses as the ball approaches, and both banks slide
laterally with the ball while staying inside the field.
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src.ai import (AIController, BANK_SPACING, DEF_LINE_MAX_DEPTH,
                    DEF_LINE_MIN_DEPTH, FIELD_MAX_Y, FIELD_MIN_Y,
                    FORMATION_MARGIN, LINE_GAP_MAX, LINE_GAP_MIN,
                    MARK_ZONE_DIST)
from src.entities import Ball, Player, Team


def _add_player(team, name, x, y, role="field"):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    p.role = role
    if role == "goalkeeper":
        p.is_goalkeeper = True
    team.add_player(p)
    return p


def _block_scenario(ball_xy=(600.0, 300.0)):
    """Team 1 (defends the left goal at x=50) in its 2-2-1 shape."""
    team = Team("Team 1", (255, 0, 0))
    d1 = _add_player(team, "T1P1", 176.0, 225.0, "defender")
    d2 = _add_player(team, "T1P2", 176.0, 375.0, "defender")
    m1 = _add_player(team, "T1P3", 330.0, 200.0, "midfielder")
    m2 = _add_player(team, "T1P4", 330.0, 400.0, "midfielder")
    st = _add_player(team, "T1P5", 484.0, 300.0, "striker")
    _add_player(team, "T1GK", 71.0, 300.0, "goalkeeper")
    
    opp = Team("Team 2", (0, 0, 255))
    carrier = _add_player(opp, "T2P1", ball_xy[0], ball_xy[1], "striker")
    ball = Ball(*ball_xy)
    ball.possession = carrier
    
    ai = AIController(team, opp, ball)
    ai.team_state = "defense"
    return ai, (d1, d2), (m1, m2), st, ball


def _velocity_angle_towards(entity, target_x, target_y):
    speed = math.hypot(entity.vx, entity.vy)
    dx, dy = target_x - entity.x, target_y - entity.y
    dist = math.hypot(dx, dy)
    if speed == 0 or dist == 0:
        return math.pi
    cos = (entity.vx * dx + entity.vy * dy) / (speed * dist)
    return math.acos(max(-1.0, min(1.0, cos)))


class BankGeometryTest(unittest.TestCase):
    def test_banks_are_flat_lines_with_the_defenders_deeper(self):
        ai, (d1, d2), (m1, m2), _, _ = _block_scenario()
        pos = ai._block_positions()

        self.assertAlmostEqual(pos[d1][0], pos[d2][0])  # flat defender line
        self.assertAlmostEqual(pos[m1][0], pos[m2][0])  # flat midfielder line
        # Team 1 defends the left goal: the defender bank sits at smaller x.
        self.assertLess(pos[d1][0], pos[m1][0])

    def test_block_retreats_as_the_ball_advances(self):
        ai_far, (d1, _), _, _, ball = _block_scenario(ball_xy=(700.0, 300.0))
        far_line = ai_far._block_positions()[d1][0]

        ball.x = 400.0  # attack advances toward our goal
        near_line = ai_far._block_positions()[d1][0]

        self.assertLess(near_line, far_line)
        # Depth stays within the configured bounds (relative to goal x=50).
        self.assertGreaterEqual(near_line - 50.0, DEF_LINE_MIN_DEPTH)
        self.assertLessEqual(far_line - 50.0, DEF_LINE_MAX_DEPTH)

    def test_gap_compresses_as_the_ball_approaches(self):
        ai, (d1, _), (m1, _), _, ball = _block_scenario(ball_xy=(700.0, 300.0))
        pos = ai._block_positions()
        far_gap = pos[m1][0] - pos[d1][0]

        ball.x = 360.0
        pos = ai._block_positions()
        near_gap = pos[m1][0] - pos[d1][0]

        self.assertLess(near_gap, far_gap)
        self.assertGreaterEqual(near_gap, LINE_GAP_MIN)
        self.assertLessEqual(far_gap, LINE_GAP_MAX)

    def test_banks_slide_laterally_with_the_ball(self):
        ai, (d1, d2), _, _, ball = _block_scenario()
        ball.y = 150.0  # ball toward the top sideline
        top_pos = ai._block_positions()
        ball.y = 450.0
        bottom_pos = ai._block_positions()

        self.assertLess(top_pos[d1][1], bottom_pos[d1][1])
        # Teammates keep their spacing and never swap slots (d1 home is
        # higher on the pitch than d2's).
        self.assertAlmostEqual(top_pos[d2][1] - top_pos[d1][1], BANK_SPACING)
        self.assertLess(top_pos[d1][1], top_pos[d2][1])

    def test_bank_stays_inside_the_field_at_the_sideline(self):
        ai, (d1, d2), (m1, m2), _, ball = _block_scenario()
        ball.y = FIELD_MIN_Y  # pinned on the top sideline
        pos = ai._block_positions()

        for p in (d1, d2, m1, m2):
            self.assertGreaterEqual(pos[p][1], FIELD_MIN_Y + FORMATION_MARGIN)
            self.assertLessEqual(pos[p][1], FIELD_MAX_Y - FORMATION_MARGIN)


class BankBehaviorTest(unittest.TestCase):
    def test_defenders_and_midfielders_head_to_their_bank_spots(self):
        ai, (d1, d2), (m1, m2), striker, ball = _block_scenario()
        presser = striker  # keep the banks intact for the assertion
        ai.active_player = presser
        self.assertGreater(math.hypot(ball.x - 50.0, ball.y - 300.0),
                           MARK_ZONE_DIST)  # outside the marking zone

        ai.execute_defense_behavior(1 / 60)

        pos = ai._block_positions()
        for p in (d1, d2, m1, m2):
            angle = _velocity_angle_towards(p, *pos[p])
            self.assertLess(angle, 0.01)

    def test_marking_still_takes_over_inside_the_threat_zone(self):
        ai, (d1, d2), _, striker, ball = _block_scenario(ball_xy=(150.0, 300.0))
        ai.active_player = striker
        raider = _add_player(ai.opponent_team, "T2P2", 160.0, 220.0, "striker")

        ai.execute_defense_behavior(1 / 60)

        # d1 is nearest the raider: it must be marking (goal-side point),
        # not standing on a bank line.
        mark = ai._mark_position(raider)
        angle = _velocity_angle_towards(d1, *mark)
        self.assertLess(angle, 0.01)


if __name__ == "__main__":
    unittest.main()
