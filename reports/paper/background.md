# Background and Design Context

Simulated soccer has long been used to study multi-agent coordination in a
continuous, dynamic, adversarial environment. RoboCup's 2D Simulation League
provides a standardized server on which teams build strategy, formations,
opponent models, and set plays.

Futebole targets a different layer. Instead of treating the simulator as a
fixed substrate, it makes the substrate itself small and inspectable:

- the state transition from a parameter to an action is directly traceable;
- physics, possession, rules, and tactics live in ordinary Python modules;
- headless matches can be instrumented without replacing the engine; and
- a full match runs fast enough for paired multi-seed experiments.

The project began with a deliberately minimal prototype. Its first observed
match collapsed into a static scrum: players stacked on one point, Team 1
recorded no possession because of controller ordering, 2,481 ineffective shot
calls accumulated, and the score stayed 0–0. Development proceeded by turning
each observed failure into an explicit mechanism and test:

1. attach the ball to its carrier and add kick cooldowns;
2. centralize possession arbitration;
3. introduce roles, formation homes, and player separation;
4. make physics and stochastic AI gates timestep-aware;
5. add restarts, goalkeepers, passing lanes, shooting geometry, defensive
   shape, and rest defence; and
6. add semantic input and mixed human/AI control without bypassing the central
   rules.

## Relationship to RoboCup

Futebole borrows several conceptual decompositions from simulated-soccer
research:

- a discrete-time world model;
- formation positions as spatial priors;
- a distinguished active player;
- role-aware off-ball positioning;
- set-piece restart state; and
- team-level tactical modes.

It does not attempt RoboCup server compatibility. In particular, Futebole AI
has perfect global perception and no sensor noise, while RoboCup agents
operate through a noisy server protocol.

## Steering behaviours

Player motion follows the steering-behaviour pattern: controllers continuously
recompute targets, and entities blend velocity toward the requested direction.
Tactics therefore choose *where to steer* while the entity layer owns
acceleration, stamina scaling, integration, and friction.

This separation is important for mixed control. Keyboard input and AI both
produce movement intent; neither directly updates position.

## Simulation methodology

The evaluation uses two standard ideas from stochastic simulation:

### Common random numbers

Every configuration runs the same 20 seeds. Pairing like-for-like stochastic
streams reduces noise in comparisons, especially before trajectories diverge.

### Distribution-free paired inference

Paired sign-flip permutation tests compare each configuration with the
baseline without assuming normally distributed match metrics.

The combination fits engine tuning: it measures a parameter's effect on the
same simulator rather than claiming superiority over another system.

## Design position

Futebole is best viewed as:

- a playable small-sided football simulation;
- a transparent testbed for game-AI mechanics;
- a regression target for emergent match behaviour; and
- a teaching-sized example of centralized rules with decentralized
  controller intent.

It is not currently:

- a real-football prediction model;
- an 11-a-side tactical simulator;
- a RoboCup client;
- a physics-accurate ball model; or
- a calibrated human-versus-AI game.

The distinction keeps the paper's empirical claims aligned with what was
actually measured.
