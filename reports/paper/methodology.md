# Experimental Methodology

## Evaluation question

The experiment does not compare Futebole with another simulator and does not
measure which side is stronger. It asks:

> How does changing one engine parameter alter the ecosystem of an otherwise
> symmetric self-play match?

Both teams use the same parameter values in every match. Each configuration is
compared with the repository baseline, not with the opposing team.

## Headless harness

`experiments/run_experiments.py` runs the real engine with:

- SDL video and audio set to dummy drivers;
- `GameEngine()` with no human-designated team;
- a virtual `pygame.time.get_ticks()` clock;
- one deterministic random seed per match; and
- instrumentation around existing entity methods.

The virtual clock advances by
`int(1000 / 60) = 16` milliseconds per update. Because engine time is derived
from integer milliseconds, a 90-second match contains 5,625 updates—an
effective 62.5 updates/s, despite the harness's nominal `FPS = 60` label.
Physics and dt-corrected AI gates receive the actual 0.016-second timestep.

The loop exits when `engine.game_time` reaches the 90-second
`match_duration`. It does not render and does not include frozen frames after
the match ends.

## Reproducibility

Python's global pseudorandom number generator is seeded once per match. Every
stochastic event consumes that stream:

- tackle success;
- foul decisions;
- pressured offloads;
- long-shot gates;
- shot noise; and
- kickoff receiver choice.

A configuration/seed pair is therefore reproducible for a fixed code revision.

The sweep uses seeds 1 through 20 for every configuration. Reusing seeds is a
common-random-numbers design: the same initial random stream is shared until a
changed parameter causes execution paths to diverge.

## Instrumentation

The harness wraps `Player.pass_ball()` to count attempted passes and tracks
whether the intended receiver becomes the next possessor. It samples engine
state after each update.

| Metric | Definition |
|---|---|
| Goals | Combined score of both teams |
| Shots | Team shot counters; goalkeeper clearances excluded |
| Passes | Successful `pass_ball()` calls |
| Pass completion | Intended receivers that next gain possession / passes |
| Possession deviation | Absolute deviation of Team 1's held-ball share from 50% |
| Turnovers | Updates where the holding team changes |
| Free-ball share | Updates with no possessor |
| Restarts | Throw-ins, corners, and goal kicks awarded |
| Moving ball speed | Mean speed on updates above 1 px/s |
| Stillness | Share of updates at or below 1 px/s |
| Team spread | Mean pairwise distance among Team 1 players |
| Overlap | Share of updates whose closest pair is under 20 px by more than a 1e-6 floating-point tolerance |

The first non-null possessor after a pass decides completion: the attempt
counts only when that player is the intended receiver.

## Parameter sweep

Five parameters are varied one at a time around the baseline:

| Configuration | Parameter | Value | Baseline |
|---|---|---:|---:|
| baseline | — | — | — |
| tackle-low | `TACKLE_SUCCESS_PROB` | 0.01 | 0.05 |
| tackle-high | `TACKLE_SUCCESS_PROB` | 0.15 | 0.05 |
| press-pass-low | `PRESSURE_PASS_PROB` | 0.01 | 0.06 |
| press-pass-high | `PRESSURE_PASS_PROB` | 0.20 | 0.06 |
| long-shot-off | `LONG_SHOT_PROB` | 0.00 | 0.02 |
| long-shot-high | `LONG_SHOT_PROB` | 0.10 | 0.02 |
| shoot-short | `SHOOT_RANGE` | 100 px | 150 px |
| shoot-long | `SHOOT_RANGE` | 220 px | 150 px |
| shape-rigid | `SHAPE_SLIDE` | 0.2 | 0.5 |
| shape-elastic | `SHAPE_SLIDE` | 0.8 | 0.5 |

Eleven configurations × 20 shared seeds produce 220 matches.

The driver snapshots every overridden module constant, restores all defaults
before applying a configuration, and restores the baseline after the sweep.

## Paired sign-flip test

For metric \\(m\\), configuration \\(c\\), baseline \\(b\\), and seed \\(i\\),
the paired difference is

<div class="math">
\[
d_i = m_{c,i}-m_{b,i}.
\]
</div>

The statistic is \\(|\bar{d}|\\). Under the null, each observed difference is
randomly multiplied by \\(-1\\) or \\(+1\\). With 20,000 random sign
assignments:

<div class="math">
\[
p
=
\frac{
  1
  + \#\left\{
    \pi:
    \left|\overline{\epsilon^\pi d}\right|
    \ge |\bar{d}|
  \right\}
}{
  1 + 20{,}000
},
\qquad
\epsilon_i^\pi\in\{-1,+1\}.
\]
</div>

The analysis reports mean paired effects and two-sided p-values:

- `*`: \\(p<0.05\\);
- `**`: \\(p<0.01\\).

There are 60 reported contrasts. A Bonferroni threshold would be
\\(0.05/60\approx0.0008\\). The long-shot removal, eager-offload, and
turnover effects survive that stricter posture. The high-elasticity scoring
effect remains significant at \\(p<0.01\\), but its
\\(p\approx0.0015\\) does not cross the Bonferroni threshold.

## Generated artifacts

The reproducibility chain is:

```text
experiments/run_experiments.py
    └─> experiments/results.csv
          └─> experiments/aggregate.py
                ├─> paper/generated/summary_main.tex
                ├─> paper/generated/summary_flow.tex
                ├─> paper/generated/pvalues.tex
                └─> paper/generated/*.dat

experiments/capture_figures.py
    └─> paper/figures/*.png
```

`aggregate.py` groups rows by configuration, computes means and sample
standard deviations, runs paired sign-flip tests, and writes the LaTeX table
rows and plotting data consumed by the publication.

## Scope after human control

The experiment suite always uses `GameEngine()` and therefore remains all-AI.
The current interactive entry point uses `GameEngine(human_team="team1")`, but
that branch is not entered by the sweep. The complete 220-match experiment was
rerun after mixed-control integration and reproduced the goal, shot,
pass-volume, turnover, ball-flow, and shape results. This revision also
corrects the derived definitions of next-possessor pass completion,
held-possession deviation, and geometric overlap; runtime was refreshed on the
current host. The results establish behaviour of the simulation substrate and
autonomous policy; they do not measure human performance, usability, or
difficulty balance.
