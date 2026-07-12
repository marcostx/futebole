"""
Unit tests for decision-based passing (Tier 3 #3).

Covers the open-lane check (opponents blocking the carrier->receiver segment),
lane-aware pass-target selection, and the positional build-up decision (an
unpressured carrier only passes when the receiver is meaningfully more open).
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: F401

from src.ai import AIController, LANE_BLOCK_RADIUS, OPEN_ADVANTAGE, PRESSURE_DIST
from src.entities import Ball, Player, Team


def _make_teams(*, carrier_xy=(300.0, 300.0)):
    """Team 1 carrier with the ball; opponents parked far away by default."""
    team = Team("Team 1", (255, 0, 0))
    carrier = Player("T1P1", carrier_xy[0], carrier_xy[1], team.color)
    carrier.home_x, carrier.home_y = carrier.x, carrier.y
    team.add_player(carrier)

    opp = Team("Team 2", (0, 0, 255))

    ball = Ball(carrier.x, carrier.y)
    ball.possession = carrier

    ai = AIController(team, opp, ball)
    ai.team_state = "attack"
    ai.active_player = carrier
    return ai, carrier, ball


def _add_player(team, name, x, y):
    p = Player(name, x, y, team.color)
    p.home_x, p.home_y = x, y
    team.add_player(p)
    return p


class LaneIsOpenTest(unittest.TestCase):
    def test_open_when_no_opponents(self):
        ai, carrier, _ = _make_teams()
        mate = _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        self.assertTrue(ai._lane_is_open(carrier, mate))

    def test_blocked_by_opponent_on_the_lane(self):
        ai, carrier, _ = _make_teams()
        mate = _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        # Opponent sitting right on the midpoint of the lane.
        _add_player(ai.opponent_team, "T2P1", carrier.x + 50, carrier.y)
        self.assertFalse(ai._lane_is_open(carrier, mate))

    def test_open_when_opponent_is_laterally_clear(self):
        ai, carrier, _ = _make_teams()
        mate = _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        # Mid-lane along x but well outside the block radius along y.
        _add_player(ai.opponent_team, "T2P1",
                    carrier.x + 50, carrier.y + LANE_BLOCK_RADIUS + 20)
        self.assertTrue(ai._lane_is_open(carrier, mate))

    def test_opponent_beside_carrier_does_not_block(self):
        # A presser right next to the carrier is the pressure situation, not a
        # blocked lane: its projection falls before LANE_START_T.
        ai, carrier, _ = _make_teams()
        mate = _add_player(ai.team, "T1P2", carrier.x + 120, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 5, carrier.y)
        self.assertTrue(ai._lane_is_open(carrier, mate))

    def test_opponent_beyond_receiver_does_not_block(self):
        ai, carrier, _ = _make_teams()
        mate = _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 200, carrier.y)
        self.assertTrue(ai._lane_is_open(carrier, mate))


class LaneAwareTargetSelectionTest(unittest.TestCase):
    def test_blocked_lane_candidate_is_excluded(self):
        ai, carrier, _ = _make_teams()
        # More forward option, but its lane is blocked...
        _add_player(ai.team, "T1P2", carrier.x + 120, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 60, carrier.y)
        # ...and a less forward option with a clear lane.
        open_mate = _add_player(ai.team, "T1P3", carrier.x + 60, carrier.y + 90)

        self.assertIs(ai._best_pass_target(carrier), open_mate)

    def test_returns_none_when_all_lanes_blocked(self):
        ai, carrier, _ = _make_teams()
        mate = _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 50, carrier.y)
        self.assertIsNone(ai._best_pass_target(carrier))


class BackPassTest(unittest.TestCase):
    def test_back_pass_when_nobody_open_in_front(self):
        ai, carrier, _ = _make_teams()
        # Forward mate with a blocked lane...
        _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 50, carrier.y)
        # ...and an open backward mate to recycle possession to.
        back_mate = _add_player(ai.team, "T1P3", carrier.x - 80, carrier.y + 30)

        self.assertIs(ai._best_pass_target(carrier, allow_backward=True),
                      back_mate)

    def test_backward_outlet_requires_opt_in(self):
        # The default (build-up) stays forward-only so possession isn't
        # endlessly cycled backwards outside of pressure situations.
        ai, carrier, _ = _make_teams()
        _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 50, carrier.y)
        _add_player(ai.team, "T1P3", carrier.x - 80, carrier.y + 30)

        self.assertIsNone(ai._best_pass_target(carrier))

    def test_forward_target_preferred_over_more_open_backward_mate(self):
        ai, carrier, _ = _make_teams()
        forward = _add_player(ai.team, "T1P2", carrier.x + 80, carrier.y)
        _add_player(ai.team, "T1P3", carrier.x - 80, carrier.y)
        # One opponent near the forward mate (but off the lane) makes the
        # backward mate strictly more open; forward must still win.
        _add_player(ai.opponent_team, "T2P1",
                    carrier.x + 80, carrier.y + LANE_BLOCK_RADIUS + 30)

        self.assertIs(ai._best_pass_target(carrier, allow_backward=True),
                      forward)

    def test_none_when_all_lanes_blocked_in_both_directions(self):
        ai, carrier, _ = _make_teams()
        _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 50, carrier.y)
        _add_player(ai.team, "T1P3", carrier.x - 100, carrier.y)
        _add_player(ai.opponent_team, "T2P2", carrier.x - 50, carrier.y)

        self.assertIsNone(ai._best_pass_target(carrier, allow_backward=True))

    def test_pressured_carrier_passes_back_when_front_is_blocked(self):
        ai, carrier, ball = _make_teams()
        _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 50, carrier.y)  # lane block
        _add_player(ai.team, "T1P3", carrier.x - 80, carrier.y)
        presser = _add_player(ai.opponent_team, "T2P2",
                              carrier.x + 10, carrier.y)
        self.assertLess(carrier.distance_to(presser), PRESSURE_DIST)

        ai.execute_attack_behavior(1 / 60)

        # Offloaded backwards (-x for Team 1) instead of dribbling into
        # the presser with no forward option.
        self.assertIsNone(ball.possession)
        self.assertGreater(ball.loose_timer, 0.0)
        self.assertLess(ball.vx, 0.0)


class PressuredLaneFilterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_pressured_carrier_keeps_ball_when_only_lane_is_blocked(self):
        # Under pressure with a forward teammate whose lane is blocked: the
        # pressure path still respects the lane filter and does not pass.
        ai, carrier, ball = _make_teams()
        _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        _add_player(ai.opponent_team, "T2P1", carrier.x + 50, carrier.y)  # blocks lane
        presser = _add_player(ai.opponent_team, "T2P2",
                              carrier.x + 10, carrier.y)
        self.assertLess(carrier.distance_to(presser), PRESSURE_DIST)
        self.assertIsNone(ai._best_pass_target(carrier))

        ai.execute_attack_behavior(1 / 60)

        self.assertIs(ball.possession, carrier)
        self.assertGreater(abs(carrier.vx) + abs(carrier.vy), 0.0)


class BuildUpDecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_unpressured_carrier_passes_to_clearly_more_open_mate(self):
        ai, carrier, ball = _make_teams()
        # Mark the carrier (outside PRESSURE_DIST but close enough to reduce
        # its openness) and give it a wide-open forward teammate.
        marker_dist = PRESSURE_DIST + 20
        _add_player(ai.opponent_team, "T2P1", carrier.x, carrier.y + marker_dist)
        mate = _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        self.assertGreater(ai._openness(mate),
                           ai._openness(carrier) + OPEN_ADVANTAGE)

        ai.execute_attack_behavior(1 / 60)

        # Build-up pass fired: ball released and in flight.
        self.assertIsNone(ball.possession)
        self.assertGreater(ball.loose_timer, 0.0)

    def test_unpressured_carrier_keeps_ball_when_no_open_advantage(self):
        ai, carrier, ball = _make_teams()
        # One distant opponent: carrier and mate are both wide open, so the
        # pass would not improve the team's position.
        _add_player(ai.opponent_team, "T2P1", 700.0, 300.0)
        mate = _add_player(ai.team, "T1P2", carrier.x + 100, carrier.y)
        self.assertLessEqual(ai._openness(mate),
                             ai._openness(carrier) + OPEN_ADVANTAGE)

        ai.execute_attack_behavior(1 / 60)

        # No pass: still in possession and dribbling.
        self.assertIs(ball.possession, carrier)
        self.assertGreater(abs(carrier.vx) + abs(carrier.vy), 0.0)


if __name__ == "__main__":
    unittest.main()
