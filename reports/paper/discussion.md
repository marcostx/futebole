# Discussion and Future Work

## What self-comparison establishes

Because both teams share each configuration, a contrast measures the effect of
a mechanism on the match ecosystem—tempo, circulation, spacing, and
production—not competitive advantage.

This is useful during engine development. Disabling long shots for both teams,
for example, cannot change their relative strength, but it reveals that the
current defensive stack makes the long-shot channel essential to scoring.
Asymmetric win-rate evaluation would miss that ecosystem-level dependency.

Shared seeds reduce variance early in paired matches. The benefit decays over
time: once one configuration consumes a different random branch, later tackle,
offload, and shot draws no longer represent the same event sequence.

## External validity

The measured magnitudes are stylized rather than calibrated to professional
football:

- six players per side;
- one 90-second period;
- roughly seven combined goals;
- 98% pass completion; and
- perfect, global perception for AI agents.

High completion exposes a modeling gap. Opponents only block a lane at kick
time; they do not read the ball flight and intercept dynamically. The lane
veto therefore removes almost every risky AI pass before it is attempted.

The engine is best interpreted as an inspectable agent-based football system
for mechanics and behaviour experiments, not a calibrated prediction model.

## Fairness and control asymmetry

Mirrored AI teams have:

- identical roster and parameters;
- mirrored formation geometry;
- the same global perception;
- controller commands issued before integration; and
- one central possession contest.

Configuration-level mean held-possession deviation ranges from 2.1 to
3.9 percentage points.

Mixed-control mode preserves physical and rules-level fairness:

- human input cannot set possession;
- all actions use shared entity methods;
- both control types pay the same stamina costs;
- cooldowns and loose-ball windows are shared; and
- tackles, fouls, and restarts are controller-agnostic.

Decision support is not symmetric. AI passing filters lanes and offside
positions; human passing uses a facing cone and nearest-player fallback.
Rules-level fairness should not be confused with equal assistance or equal
playing strength.

## Human-mode evidence

Automated tests cover:

- input normalization and edge-triggered actions;
- valid control-mode construction;
- selection following possession;
- closest-player auto-selection and Tab cycling;
- defensive goalkeeper exclusion and on-ball goalkeeper selection;
- selected-player exclusion from AI commands;
- pass, shoot, and sprint behavior;
- the cyan selection marker and controls legend; and
- central possession and restart fairness.

The 220-match study does not cover:

- human win rate;
- player learning curve;
- input latency or responsiveness;
- subjective difficulty;
- accessibility; or
- whether targeting assistance feels fair.

Those require mixed-control simulations or user studies, not inference from
AI self-play.

## Known simplifications

### Match structure

- The complete match is 90 seconds with no halves or added time.
- `end_game()` pauses the engine; there is no winner presentation.
- There are no tournaments, substitutions, injuries, or penalties.

### Laws

- Offside is an AI target veto, not a whistle.
- Fouls retain possession and cooldown the tackler; no cards or free-kick
  placement exist.
- Corners, goal kicks, and throw-ins have entitlement but no specialized
  set-piece animation or team shape.

### Ball and contact

- The ball is a point-mass-like disc with no spin, curve, height, or aerial
  phase.
- Exponential velocity decay is timestep-corrected, but drift is integrated
  before decay, so sampled positions are not exactly timestep-invariant.
- Tackles are probabilistic proximity contests rather than physical challenge
  animations.
- A single 0.3-second loose timer models every pass and shot flight.

### Team intelligence

- Perception is perfect and global.
- State changes are immediate; there is no explicit counter-attack or recovery
  transition.
- Only one support runner is coordinated.
- Pass receivers do not adapt their run to ball flight.
- Defenders do not reactively intercept after a pass is kicked.
- The shot-angle difference is not wrapped to the smaller angular interval,
  so mirrored left-goal and right-goal evaluations can differ.
- The goalkeeper has three simple modes and no box-specific catch model.

### Human control

- Defensive selection and Tab cycling exclude the goalkeeper; an on-ball
  goalkeeper is selected automatically and waits for human input.
- Pass targeting is simpler than AI targeting.
- Human offside is not enforced.
- Difficulty and assistance levels are not configurable.

## Threats to inference

Goal counts are low integers and paired differences can be heavy-tailed. The
sign-flip test assumes sign symmetry under the null. Conclusions should
emphasize effects that are:

1. large in practical terms;
2. monotonic across both directions of a sweep; and
3. statistically strong.

The long-shot, eager-offload, high-elasticity, and turnover findings satisfy
those criteria. Smaller p-values do not make the system representative of real
football.

## Future work

### Tactical model

- explicit counter-attack and recovery states;
- width preservation, wing progression, and crosses;
- multiple coordinated off-ball runs;
- structured buildup from goalkeeper possession and goal kicks;
- pressing triggers and cover shadows;
- penalty-box occupation and set-piece shapes;
- score- and clock-aware tempo; and
- richer roles on the path toward 11-a-side.

### Mixed control

- human-versus-AI playtesting and difficulty calibration;
- lane-aware optional pass assistance;
- engine-level offside shared by both modes;
- configurable defensive goalkeeper selection and auto-distribution;
- rebinding UI and accessibility settings; and
- separate telemetry for human decisions and AI teammate support.

### Evaluation

- reactive pass interception;
- current-version mixed-control match studies;
- calibration against real small-sided football distributions;
- repeated sweeps as regression checks after tactical changes; and
- strategy recommendation or opponent adaptation on top of the current
  inspectable substrate.

## Conclusion

Futebole combines timestep-aware movement, distance-scaled kicks, stamina,
central possession arbitration, rule-based restarts, role-aware team tactics,
and mixed human/AI control in one compact engine.

The parameter sweep demonstrates that its mechanisms interact in measurable
ways: long shots prevent defensive gridlock, early offloading can reduce
penetration, excessive formation attraction creates congestion, and tackle
probability controls turnover volatility.

The current evidence is deliberately bounded. It is strong evidence about the
all-AI simulation at the evaluated revision, supported by deterministic tests
for mixed-control invariants. It is not yet evidence of real-football
calibration or human-versus-AI balance.
