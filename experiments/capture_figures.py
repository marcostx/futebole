"""
Capture publication figures from a seeded headless match.

Runs the real GameEngine with a virtual clock and saves a screenshot the
first time each targeted game situation occurs (kickoff lineup, defensive
block, man-marking, rest defence, attack with support runner, restart, and
post-goal kickoff). Frames go to paper/figures/.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import random

import pygame

from src.game_engine import GameEngine

FPS = 60
DT_MS = int(1000 / FPS)
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "paper", "figures")
SEED = 7


def save(engine, name, captured):
    if name in captured:
        return
    engine.render()
    path = os.path.join(OUT_DIR, f"{name}.png")
    pygame.image.save(engine.screen, path)
    captured.add(name)
    print(f"captured {name} at t={engine.game_time:.1f}s "
          f"score={engine.team1_score}-{engine.team2_score}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    random.seed(SEED)
    virtual = {"t": 0}
    pygame.time.get_ticks = lambda: virtual["t"]
    pygame.init()

    engine = GameEngine()
    captured = set()

    # Kickoff lineup before any update ticks.
    save(engine, "kickoff", captured)

    prev_score = (0, 0)
    goal_frames_left = 0

    while engine.game_time < engine.match_duration:
        virtual["t"] += DT_MS
        engine.update()

        score = (engine.team1_score, engine.team2_score)
        if score != prev_score:
            # Render the post-goal kickoff lineup a few frames later.
            goal_frames_left = 2
            prev_score = score
        elif goal_frames_left > 0:
            goal_frames_left -= 1
            if goal_frames_left == 0:
                save(engine, "post_goal_kickoff", captured)

        t1_ai, t2_ai = engine.team1_ai, engine.team2_ai
        ball = engine.ball

        # Defensive block: a team defending in two banks with the ball far
        # from its goal (no marking threat).
        for ai in (t1_ai, t2_ai):
            own_goal_x, own_goal_y = ai._own_goal_center()
            threat = math.hypot(ball.x - own_goal_x, ball.y - own_goal_y) < 300
            if (ai.team_state == "defense" and not threat
                    and engine.game_time > 5):
                save(engine, "defensive_block", captured)

        # Man-marking: defense with the ball inside the threat zone.
        for ai in (t1_ai, t2_ai):
            own_goal_x, own_goal_y = ai._own_goal_center()
            threat = math.hypot(ball.x - own_goal_x, ball.y - own_goal_y) < 220
            if ai.team_state == "defense" and threat and ball.possession is not None:
                save(engine, "man_marking", captured)

        # Attack with a designated support runner ahead of the carrier.
        for ai in (t1_ai, t2_ai):
            if (ai.team_state == "attack" and ai.support_player is not None
                    and ball.possession is not None
                    and not ball.possession.is_goalkeeper):
                carrier = ball.possession
                run_gap = (ai.support_player.x - carrier.x) * ai.field_side
                if run_gap > 80 and engine.game_time > 8:
                    save(engine, "attack_support", captured)

        # Rest defence: attacking defenders have reached the cover-line targets
        # behind the ball. Requiring proximity avoids capturing the first frame
        # of a possession transition before the line has settled.
        for ai in (t1_ai, t2_ai):
            if ai.team_state != "attack" or engine.game_time <= 8:
                continue
            rest_targets = ai._rest_defense_positions()
            if (rest_targets
                    and max(math.hypot(player.x - target_x,
                                       player.y - target_y)
                            for player, (target_x, target_y)
                            in rest_targets.items()) < 45):
                save(engine, "rest_defense", captured)

        # Restart: a dead ball awaiting the entitled team.
        if engine.restart_team is not None:
            fy, fh = engine.field_y, engine.field_height
            if ball.y <= fy or ball.y >= fy + fh:
                save(engine, "throw_in", captured)
            else:
                save(engine, "goal_line_restart", captured)

        # Midmatch open-play frame around the middle of the match.
        if 44.5 < engine.game_time < 45.5:
            save(engine, "midmatch", captured)

    print(f"final score {engine.team1_score}-{engine.team2_score}")
    print("captured:", sorted(captured))


if __name__ == "__main__":
    main()
