# Futebole Technical Paper

**An Agent-Based 2D Soccer Simulation Engine with Role-Aware Tactics and
Mixed Human/AI Control**

Marcos Teixeira · Futebole v0.1.0 · Updated July 2026

[View the LaTeX source](https://github.com/marcostx/futebole/blob/main/paper/main.tex)

## Abstract

Futebole is an open, lightweight two-dimensional soccer simulation with two
execution modes:

- reproducible all-AI matches between teams of six agents—five outfield
  players and a goalkeeper; and
- interactive mixed-control matches in which a human steers one selected
  player while the team AI coordinates the remaining five.

The engine combines:

1. timestep-aware point-mass physics with exponential rolling
   friction, capped kick speeds, momentum, and distance-scaled kick power;
2. an order-independent probabilistic possession contest with tackles, fouls,
   dead-ball restarts, and a simplified offside policy;
3. role-aware team behaviour: a three-state team machine, elastic formations,
   a two-bank defensive block, goal-side marking, rest defence, lane-aware
   passing, angle-gated shooting, and a dedicated goalkeeper; and
4. a semantic input layer with phase-aware player selection, sprint, pass, and
   shoot actions, while retaining the same physics and central rules used by
   the AI.

The autonomous mode was evaluated through 220 seeded headless matches across
eleven parameter configurations. Common random numbers and paired sign-flip
permutation tests isolate each parameter's effect. The main findings are:

- disabling long-range shooting reduces scoring from 7.05 to 0.85 goals per
  match;
- eager pressure offloading and highly elastic formations each reduce scoring
  by roughly three goals per match; and
- tackle probability acts as a direct, monotonic control on turnover volume.

A 90-second match with 16 ms virtual updates simulates in approximately
0.76 seconds on one laptop-class CPU core, about 118 times faster than real
time.

## Scope of the evidence

The experiment suite constructs `GameEngine(human_team=None)`, so every
reported result characterises AI self-play. Human control was added later
without changing that all-AI controller path; the full sweep was rerun after
integration and reproduced the production, flow, and shape results. The
derived definitions of pass completion, held-possession deviation, and
geometric overlap were corrected, and runtime was refreshed on the current
host. The human mode is covered by deterministic tests for input semantics,
selection, AI exclusion, actions, visual markers, and rules invariants, but it
has not yet received a user study or human-versus-AI balance calibration.

## Contributions

- A formal description of the physics, movement, stamina, kick, possession,
  restart, and collision models.
- Explicit algorithms for possession arbitration, carrier decisions, pass
  targeting, formation movement, and player separation.
- A mixed-control architecture that cleanly separates human commands from
  tactical AI while sharing the same rules engine.
- A reproducible self-comparison methodology for tuning stochastic simulation
  parameters.
- An empirical sensitivity analysis of five tactical and physical parameters.

## Reading guide

- [Architecture and Control](architecture.md) describes modules, execution
  modes, the frame pipeline, and human/AI coordination.
- [Physics and Entities](physics.md) defines movement, friction, kicks, stamina,
  and the core constants.
- [Rules and Possession](rules.md) specifies ball control, tackles, fouls,
  restarts, offside, and collision handling.
- [Team Behaviour](team-behaviour.md) covers formations, defending, attacking,
  passing, shooting, support, and goalkeeper logic.
- [Experimental Methodology](methodology.md) explains the headless harness,
  metrics, configurations, and statistical test.
- [Results](results.md) reports the parameter sweep and its practical
  implications.
- [Discussion and Future Work](discussion.md) separates demonstrated behaviour
  from known simplifications and open work.
