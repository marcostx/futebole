"""
Headless match monitor for the soccer simulation.

Runs the real GameEngine loop with a virtual clock (so a full 90s match
completes instantly), instruments shots/passes/possession, records
statistics and saves periodic screenshots for later inspection.
"""

import argparse
import math
import os
import random
import statistics

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.game_engine import GameEngine
from src.entities import Player

FPS = 60
DT_MS = int(1000 / FPS)
PLAYER_OVERLAP_DISTANCE = 20.0  # two 10 px-radius player discs
PLAYER_OVERLAP_TOLERANCE = 1e-6  # do not count floating-point contact
SCREENSHOT_FRACTIONS = (0.05, 0.25, 0.5, 0.75, 0.95)


def _install_virtual_clock():
    """Patch pygame.time.get_ticks so the match runs on a fixed virtual
    timestep instead of wall-clock time. Returns the mutable clock state."""
    virtual_ms = {"t": 0}
    pygame.time.get_ticks = lambda: virtual_ms["t"]
    return virtual_ms


def _instrument_players(stats):
    """Wrap Player.shoot / Player.pass_ball to count shots and passes."""
    orig_shoot = Player.shoot
    orig_pass = Player.pass_ball

    def _shoot(self, ball, tx, ty):
        ok = orig_shoot(self, ball, tx, ty)
        if ok:
            stats["shots"] += 1
        return ok

    def _pass(self, ball, target):
        ok = orig_pass(self, ball, target)
        if ok:
            stats["passes"] += 1
            stats["_pending_pass_target"] = target
        return ok

    Player.shoot = _shoot
    Player.pass_ball = _pass


def run_match(output_dir="match_frames", seed=None):
    """Simulate one full match headlessly and collect statistics."""
    if seed is not None:
        random.seed(seed)
    virtual_ms = _install_virtual_clock()
    pygame.init()

    stats = {
        "shots": 0,
        "passes": 0,
        "pass_completed": 0,
        "possession_frames_t1": 0,
        "possession_frames_t2": 0,
        "free_ball_frames": 0,
        "goals": [],  # (time, scorer_team)
    }
    _instrument_players(stats)

    engine = GameEngine()

    ball_speeds = []
    team_spread_samples = []  # avg pairwise distance within team1
    min_pair_dist_samples = []  # closest two players (any) => clustering / overlap
    frames = 0
    prev_score = (0, 0)

    os.makedirs(output_dir, exist_ok=True)

    # Drive the loop by match time so it stops exactly when the match ends,
    # avoiding extra frozen frames that would skew the metrics.
    total_frames = int(engine.match_duration * 1000 / DT_MS)
    screenshot_frames = {int(total_frames * f) for f in SCREENSHOT_FRACTIONS}

    i = 0
    while engine.game_time < engine.match_duration:
        virtual_ms["t"] += DT_MS
        engine.update()
        frames += 1

        ball = engine.ball
        ball_speeds.append(math.hypot(ball.vx, ball.vy))

        poss = ball.possession
        if poss is None:
            stats["free_ball_frames"] += 1
        elif poss in engine.team1.players:
            stats["possession_frames_t1"] += 1
        else:
            stats["possession_frames_t2"] += 1

        # Resolve a pass on the first player to gain possession after the kick.
        pending_target = stats.get("_pending_pass_target")
        if pending_target is not None and poss is not None:
            if poss is pending_target:
                stats["pass_completed"] += 1
            del stats["_pending_pass_target"]

        score = (engine.team1_score, engine.team2_score)
        if score != prev_score:
            scorer = "Team 1" if score[0] > prev_score[0] else "Team 2"
            stats["goals"].append((round(engine.game_time, 1), scorer))
            prev_score = score

        all_players = engine.team1.players + engine.team2.players
        t1 = engine.team1.players
        pair_d = [t1[a].distance_to(t1[b])
                  for a in range(len(t1)) for b in range(a + 1, len(t1))]
        if pair_d:
            team_spread_samples.append(statistics.mean(pair_d))
        all_pair = [all_players[a].distance_to(all_players[b])
                    for a in range(len(all_players)) for b in range(a + 1, len(all_players))]
        if all_pair:
            min_pair_dist_samples.append(min(all_pair))

        if i in screenshot_frames:
            engine.render()
            pygame.image.save(engine.screen, f"{output_dir}/t_{int(engine.game_time)}s.png")

        i += 1

    return {
        "engine": engine,
        "stats": stats,
        "frames": frames,
        "ball_speeds": ball_speeds,
        "team_spread_samples": team_spread_samples,
        "min_pair_dist_samples": min_pair_dist_samples,
    }


def print_report(result):
    """Print the match monitor report from a run_match() result."""
    engine = result["engine"]
    stats = result["stats"]
    ball_speeds = result["ball_speeds"]
    team_spread_samples = result["team_spread_samples"]
    min_pair_dist_samples = result["min_pair_dist_samples"]

    moving = [s for s in ball_speeds if s > 1]
    print("=" * 60)
    print("MATCH MONITOR REPORT")
    print("=" * 60)
    print(f"Simulated frames: {result['frames']}  (~{engine.game_time:.1f}s match, {FPS} fps)")
    print(f"Final score: Team 1 {engine.team1_score} - {engine.team2_score} Team 2")
    print(f"Goals: {stats['goals']}")
    print(f"Total goals: {len(stats['goals'])}  -> "
          f"{len(stats['goals'])/max(engine.game_time,1)*60:.1f} goals/simulated-minute")
    print("-" * 60)
    print(f"Shots taken: {stats['shots']}")
    print(f"Passes attempted: {stats['passes']}  completed(approx): {stats['pass_completed']}")
    print("-" * 60)
    tot = stats["possession_frames_t1"] + stats["possession_frames_t2"] + stats["free_ball_frames"]
    print(f"Possession  T1: {stats['possession_frames_t1']/tot*100:5.1f}%  "
          f"T2: {stats['possession_frames_t2']/tot*100:5.1f}%  "
          f"Free ball: {stats['free_ball_frames']/tot*100:5.1f}%")
    print("-" * 60)
    print(f"Ball speed  max: {max(ball_speeds):.1f}  "
          f"mean(moving): {statistics.mean(moving) if moving else 0:.1f}")
    print(f"Frames ball essentially still (<1 px/s): "
          f"{sum(1 for s in ball_speeds if s<=1)/len(ball_speeds)*100:.1f}%")
    print("-" * 60)
    print(f"Team1 avg intra-team spread: {statistics.mean(team_spread_samples):.1f} px")
    print(f"Closest any-two players (mean of per-frame min): "
          f"{statistics.mean(min_pair_dist_samples):.1f} px")
    overlap_pct = (
        sum(1 for d in min_pair_dist_samples
            if d < PLAYER_OVERLAP_DISTANCE - PLAYER_OVERLAP_TOLERANCE)
        / len(min_pair_dist_samples) * 100)
    print(f"Frames with two players overlapping (<{PLAYER_OVERLAP_DISTANCE:g}px): "
          f"{overlap_pct:.1f}%")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, help="random seed for replayable matches")
    parser.add_argument("--output-dir", default="match_frames",
                        help="directory for captured screenshots")
    args = parser.parse_args()
    print_report(run_match(args.output_dir, seed=args.seed))


if __name__ == "__main__":
    main()
