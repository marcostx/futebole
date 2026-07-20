"""
Parameter-sweep experiment harness for the soccer simulation.

Runs seeded, headless full matches under different engine/AI parameter
configurations (both teams always share the same parameters, so every
comparison is a self-comparison of the simulation engine) and records
per-match statistics to a CSV for later aggregation.

Usage:
    python experiments/run_experiments.py            # full sweep
    python experiments/run_experiments.py --quick    # 1 seed x 2 configs (timing)
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import csv
import math
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

import src.ai as ai_mod
import src.game_engine as ge_mod
from src.entities import Player
from src.game_engine import GameEngine

FPS = 60
DT_MS = int(1000 / FPS)
PLAYER_OVERLAP_DISTANCE = 20.0  # two 10 px-radius player discs
PLAYER_OVERLAP_TOLERANCE = 1e-6  # do not count floating-point contact

SEEDS = list(range(1, 21))  # 20 seeded matches per configuration

# Each configuration overrides module-level constants; "ai" refers to
# src.ai and "ge" to src.game_engine. The baseline uses repository defaults.
CONFIGS = [
    ("baseline", {}),
    # Possession-contest sweep: how easily a tackle wins the ball.
    ("tackle-low", {("ge", "TACKLE_SUCCESS_PROB"): 0.01}),
    ("tackle-high", {("ge", "TACKLE_SUCCESS_PROB"): 0.15}),
    # Pressure-passing sweep: how often a pressured carrier offloads.
    ("press-pass-low", {("ai", "PRESSURE_PASS_PROB"): 0.01}),
    ("press-pass-high", {("ai", "PRESSURE_PASS_PROB"): 0.20}),
    # Long-shot sweep: propensity to strike from distance.
    ("long-shot-off", {("ai", "LONG_SHOT_PROB"): 0.0}),
    ("long-shot-high", {("ai", "LONG_SHOT_PROB"): 0.10}),
    # Shooting-range sweep: distance threshold to attempt a shot.
    ("shoot-short", {("ai", "SHOOT_RANGE"): 100}),
    ("shoot-long", {("ai", "SHOOT_RANGE"): 220}),
    # Formation-elasticity sweep: how far the block slides with the ball.
    ("shape-rigid", {("ai", "SHAPE_SLIDE"): 0.2}),
    ("shape-elastic", {("ai", "SHAPE_SLIDE"): 0.8}),
]

MODULES = {"ai": ai_mod, "ge": ge_mod}

OUT_CSV = os.path.join(os.path.dirname(__file__), "results.csv")

FIELDS = [
    "config", "seed", "score1", "score2", "goals",
    "shots1", "shots2", "shots",
    "passes", "pass_completed",
    "poss1_pct", "poss2_pct", "free_pct",
    "turnovers", "restarts", "throw_ins", "corners", "goal_kicks",
    "ball_mean_speed_moving", "ball_max_speed", "ball_still_pct",
    "t1_spread_mean", "min_pair_mean", "overlap_pct",
    "frames", "wall_seconds",
]


def snapshot_defaults():
    """Capture the default values of every constant any config overrides."""
    defaults = {}
    for _, overrides in CONFIGS:
        for (mod, name) in overrides:
            defaults[(mod, name)] = getattr(MODULES[mod], name)
    return defaults


def apply_config(overrides, defaults):
    """Reset all swept constants to defaults, then apply this config."""
    for (mod, name), value in defaults.items():
        setattr(MODULES[mod], name, value)
    for (mod, name), value in overrides.items():
        setattr(MODULES[mod], name, value)


class KickCounter:
    """Wraps Player.shoot / Player.pass_ball to count passes per match."""

    def __init__(self):
        self.orig_pass = Player.pass_ball
        self.stats = None
        counter = self

        def _pass(player, ball, target):
            ok = counter.orig_pass(player, ball, target)
            if ok and counter.stats is not None:
                counter.stats["passes"] += 1
                counter.stats["pending_target"] = target
            return ok

        Player.pass_ball = _pass

    def bind(self, stats):
        self.stats = stats


def run_match(seed):
    """Simulate one full seeded match headlessly; return a metrics dict."""
    random.seed(seed)
    virtual = {"t": 0}
    pygame.time.get_ticks = lambda: virtual["t"]

    t0 = time.perf_counter()
    engine = GameEngine()

    stats = {"passes": 0, "pass_completed": 0}
    KICK_COUNTER.bind(stats)

    poss_frames = {"t1": 0, "t2": 0, "free": 0}
    ball_speeds = []
    spread_samples = []
    min_pair_samples = []
    turnovers = 0
    restart_counts = {"throw_in": 0, "corner": 0, "goal_kick": 0}
    last_holder_team = None
    prev_restart_team = None
    frames = 0

    fx, fy = engine.field_x, engine.field_y
    fw, fh = engine.field_width, engine.field_height

    while engine.game_time < engine.match_duration:
        virtual["t"] += DT_MS
        engine.update()
        frames += 1

        ball = engine.ball
        ball_speeds.append(math.hypot(ball.vx, ball.vy))

        holder = ball.possession
        if holder is None:
            poss_frames["free"] += 1
        else:
            team = "t1" if holder in engine.team1.players else "t2"
            poss_frames[team] += 1
            if last_holder_team is not None and team != last_holder_team:
                turnovers += 1
            last_holder_team = team

        # The first player to control the ball after a pass decides its result.
        # A later recapture by the intended target must not turn an intercepted
        # pass into a completion.
        pending_target = stats.get("pending_target")
        if pending_target is not None and holder is not None:
            if holder is pending_target:
                stats["pass_completed"] += 1
            stats["pending_target"] = None

        # Classify a newly awarded restart by the dead-ball position.
        if engine.restart_team is not None and prev_restart_team is None:
            # Corners lie on both a goal line and a sideline, so test the goal
            # line first. Goal kicks sit inside the field, away from both.
            if ball.x <= fx or ball.x >= fx + fw:
                restart_counts["corner"] += 1
            elif ball.y <= fy or ball.y >= fy + fh:
                restart_counts["throw_in"] += 1
            else:
                restart_counts["goal_kick"] += 1
        prev_restart_team = engine.restart_team

        players = engine.team1.players + engine.team2.players
        t1 = engine.team1.players
        spread_samples.append(statistics.mean(
            t1[a].distance_to(t1[b])
            for a in range(len(t1)) for b in range(a + 1, len(t1))))
        min_pair_samples.append(min(
            players[a].distance_to(players[b])
            for a in range(len(players)) for b in range(a + 1, len(players))))

    wall = time.perf_counter() - t0
    moving = [s for s in ball_speeds if s > 1]
    total_poss = sum(poss_frames.values())

    return {
        "seed": seed,
        "score1": engine.team1_score,
        "score2": engine.team2_score,
        "goals": engine.team1_score + engine.team2_score,
        "shots1": engine.team1.shots,
        "shots2": engine.team2.shots,
        "shots": engine.team1.shots + engine.team2.shots,
        "passes": stats["passes"],
        "pass_completed": stats["pass_completed"],
        "poss1_pct": round(poss_frames["t1"] / total_poss * 100, 2),
        "poss2_pct": round(poss_frames["t2"] / total_poss * 100, 2),
        "free_pct": round(poss_frames["free"] / total_poss * 100, 2),
        "turnovers": turnovers,
        "restarts": sum(restart_counts.values()),
        "throw_ins": restart_counts["throw_in"],
        "corners": restart_counts["corner"],
        "goal_kicks": restart_counts["goal_kick"],
        "ball_mean_speed_moving": round(statistics.mean(moving), 2) if moving else 0.0,
        "ball_max_speed": round(max(ball_speeds), 2),
        "ball_still_pct": round(
            sum(1 for s in ball_speeds if s <= 1) / len(ball_speeds) * 100, 2),
        "t1_spread_mean": round(statistics.mean(spread_samples), 2),
        "min_pair_mean": round(statistics.mean(min_pair_samples), 2),
        "overlap_pct": round(
            sum(1 for d in min_pair_samples
                if d < PLAYER_OVERLAP_DISTANCE - PLAYER_OVERLAP_TOLERANCE)
            / len(min_pair_samples) * 100, 2),
        "frames": frames,
        "wall_seconds": round(wall, 3),
    }


def main():
    quick = "--quick" in sys.argv
    configs = CONFIGS[:2] if quick else CONFIGS
    seeds = SEEDS[:1] if quick else SEEDS

    pygame.init()
    defaults = snapshot_defaults()

    total = len(configs) * len(seeds)
    done = 0
    rows = []
    for name, overrides in configs:
        apply_config(overrides, defaults)
        for seed in seeds:
            row = {"config": name}
            row.update(run_match(seed))
            rows.append(row)
            done += 1
            print(f"[{done}/{total}] {name} seed={seed} "
                  f"score={row['score1']}-{row['score2']} "
                  f"shots={row['shots']} passes={row['passes']} "
                  f"({row['wall_seconds']}s)", flush=True)
    apply_config({}, defaults)

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_CSV}")


KICK_COUNTER = KickCounter()

if __name__ == "__main__":
    main()
