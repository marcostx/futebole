"""
Unit tests for defensive man-marking (fix: defenders piling on their own
goal line during an opposing attack).

When the ball gets within MARK_ZONE_DIST of our goal, off-ball defenders
mark nearby opponents goal-side (one marker per man, carrier excluded — the
presser takes them) instead of dropping with the formation until the field
clamp stacks them on the goal line. With the ball far away, the normal
formation shape still applies.
"""

import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src.ai import (AIController, MARK_DIST, MARK_TARGET_RANGE,
                    MARK_ZONE_DIST)
from src.entities import Ball, Player, Team


def _add_player(team, name, x, y, *, goalkeeper=False):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    if goalkeeper:
        p.is_goalkeeper = True
        p.role = "goalkeeper"
    team.add_player(p)
    return p


def _defense_scenario(ball_xy):
    """Team 1 defending its left goal (at 50, 300) against Team 2."""
    team = Team("Team 1", (255, 0, 0))
    opp = Team("Team 2", (0, 0, 255))
    ball = Ball(*ball_xy)
    ai = AIController(team, opp, ball)
    ai.team_state = "defense"
    return ai, ball


def _velocity_angle_towards(entity, target_x, target_y):
    speed = math.hypot(entity.vx, entity.vy)
    dx, dy = target_x - entity.x, target_y - entity.y
    dist = math.hypot(dx, dy)
    if speed == 0 or dist == 0:
        return math.pi
    cos = (entity.vx * dx + entity.vy * dy) / (speed * dist)
    return math.acos(max(-1.0, min(1.0, cos)))


class MarkPositionTest(unittest.TestCase):
    def test_mark_point_is_goal_side_of_the_opponent(self):
        ai, _ = _defense_scenario((200.0, 300.0))
        attacker = _add_player(ai.opponent_team, "T2P1", 200.0, 200.0)

        mx, my = ai._mark_position(attacker)

        own_goal = (50.0, 300.0)
        dist_mark_to_goal = math.hypot(mx - own_goal[0], my - own_goal[1])
        dist_opp_to_goal = math.hypot(attacker.x - own_goal[0],
                                      attacker.y - own_goal[1])
        self.assertAlmostEqual(dist_opp_to_goal - dist_mark_to_goal, MARK_DIST)
        self.assertAlmostEqual(math.hypot(mx - attacker.x, my - attacker.y),
                               MARK_DIST)


class MarkAssignmentTest(unittest.TestCase):
    def test_each_defender_marks_a_distinct_nearby_opponent(self):
        ai, ball = _defense_scenario((150.0, 300.0))
        d1 = _add_player(ai.team, "T1P1", 120.0, 250.0)
        d2 = _add_player(ai.team, "T1P2", 120.0, 350.0)
        carrier = _add_player(ai.opponent_team, "T2P1", 150.0, 300.0)
        ball.possession = carrier
        a1 = _add_player(ai.opponent_team, "T2P2", 160.0, 220.0)
        a2 = _add_player(ai.opponent_team, "T2P3", 160.0, 380.0)
        ai.active_player = d1  # d1 presses, so only d2 marks

        assignments = ai._mark_assignments()

        self.assertNotIn(d1, assignments)
        self.assertIn(assignments[d2], (a1, a2))
        # With both defenders free, each takes a different man.
        ai.active_player = None
        assignments = ai._mark_assignments()
        self.assertEqual(len(assignments), 2)
        self.assertNotEqual(assignments[d1], assignments[d2])

    def test_carrier_and_keeper_are_never_marked(self):
        ai, ball = _defense_scenario((150.0, 300.0))
        d1 = _add_player(ai.team, "T1P1", 120.0, 250.0)
        carrier = _add_player(ai.opponent_team, "T2P1", 150.0, 300.0)
        ball.possession = carrier
        _add_player(ai.opponent_team, "T2GK", 729.0, 300.0, goalkeeper=True)

        assignments = ai._mark_assignments()

        self.assertEqual(assignments, {})  # nobody valid to mark

    def test_far_away_opponents_are_not_marked(self):
        ai, ball = _defense_scenario((150.0, 300.0))
        _add_player(ai.team, "T1P1", 120.0, 250.0)
        far = _add_player(ai.opponent_team, "T2P2", 600.0, 300.0)
        self.assertGreater(math.hypot(far.x - 50.0, far.y - 300.0),
                           MARK_TARGET_RANGE)

        self.assertEqual(ai._mark_assignments(), {})

    def test_our_keeper_never_marks(self):
        ai, ball = _defense_scenario((150.0, 300.0))
        keeper = _add_player(ai.team, "T1GK", 71.0, 300.0, goalkeeper=True)
        _add_player(ai.opponent_team, "T2P2", 160.0, 220.0)

        self.assertNotIn(keeper, ai._mark_assignments())


class DefenseBehaviorTest(unittest.TestCase):
    def _threatened_defense(self):
        """Ball deep in team 1's half with two free defenders and two attackers."""
        ai, ball = _defense_scenario((140.0, 300.0))
        presser = _add_player(ai.team, "T1P5", 200.0, 300.0)
        d1 = _add_player(ai.team, "T1P1", 100.0, 280.0)
        d2 = _add_player(ai.team, "T1P2", 100.0, 320.0)
        carrier = _add_player(ai.opponent_team, "T2P1", 140.0, 300.0)
        ball.possession = carrier
        a1 = _add_player(ai.opponent_team, "T2P2", 170.0, 200.0)
        a2 = _add_player(ai.opponent_team, "T2P3", 170.0, 400.0)
        ai.active_player = presser
        return ai, (d1, d2), (a1, a2)

    def test_defenders_mark_attackers_when_ball_near_goal(self):
        ai, (d1, d2), (a1, a2) = self._threatened_defense()
        self.assertLess(math.hypot(ai.ball.x - 50.0, ai.ball.y - 300.0),
                        MARK_ZONE_DIST)

        ai.execute_defense_behavior(1 / 60)

        # Each free defender heads to the goal-side point of its own man
        # instead of retreating toward the goal line.
        angle1 = _velocity_angle_towards(d1, *ai._mark_position(a1))
        angle2 = _velocity_angle_towards(d2, *ai._mark_position(a2))
        self.assertLess(angle1, 0.01)
        self.assertLess(angle2, 0.01)

    def test_free_deep_defender_converges_on_the_carrier(self):
        # Nobody left to mark and the defender is goal-side of the ball:
        # instead of loitering by the goal line like an extra goalkeeper,
        # it must attack the ball.
        ai, ball = _defense_scenario((160.0, 300.0))
        presser = _add_player(ai.team, "T1P5", 200.0, 300.0)
        deep1 = _add_player(ai.team, "T1P1", 80.0, 250.0)
        deep2 = _add_player(ai.team, "T1P2", 80.0, 350.0)
        carrier = _add_player(ai.opponent_team, "T2P1", 160.0, 300.0)
        ball.possession = carrier  # the only opponent near goal is the carrier
        ai.active_player = presser

        self.assertEqual(ai._mark_assignments(), {})
        ai.execute_defense_behavior(1 / 60)

        for deep in (deep1, deep2):
            angle = _velocity_angle_towards(deep, ball.x, ball.y)
            self.assertLess(angle, 0.01)

    def test_free_defender_upfield_of_ball_holds_formation(self):
        # A free teammate ahead of the ball (not goal-side) keeps shape
        # rather than collapsing backwards onto the carrier.
        ai, ball = _defense_scenario((160.0, 300.0))
        presser = _add_player(ai.team, "T1P5", 200.0, 300.0)
        upfield = _add_player(ai.team, "T1P3", 400.0, 300.0)
        carrier = _add_player(ai.opponent_team, "T2P1", 160.0, 300.0)
        ball.possession = carrier
        ai.active_player = presser

        ai.execute_defense_behavior(1 / 60)

        angle = _velocity_angle_towards(upfield, *ai.formation_position(upfield))
        self.assertLess(angle, 0.01)

    def test_formation_positioning_still_used_when_ball_is_far(self):
        ai, ball = _defense_scenario((600.0, 300.0))  # far from our goal
        presser = _add_player(ai.team, "T1P5", 550.0, 300.0)
        d1 = _add_player(ai.team, "T1P1", 176.0, 225.0)
        carrier = _add_player(ai.opponent_team, "T2P1", 600.0, 300.0)
        ball.possession = carrier
        _add_player(ai.opponent_team, "T2P2", 620.0, 200.0)
        ai.active_player = presser
        self.assertGreater(math.hypot(ball.x - 50.0, ball.y - 300.0),
                           MARK_ZONE_DIST)

        ai.execute_defense_behavior(1 / 60)

        angle = _velocity_angle_towards(d1, *ai.formation_position(d1))
        self.assertLess(angle, 0.01)


if __name__ == "__main__":
    unittest.main()
