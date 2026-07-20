# Physics and Entities

## World geometry

The Pygame window is 800 × 600 px. A 50 px margin on every side leaves a
700 × 500 px playable rectangle. Each goal mouth spans the central 40% of the
goal line.

Each team has six players in a mirrored 2-2-1+GK formation:

| Slot | Role | Home x | Home y |
|---|---|---:|---:|
| P1 | defender | 0.18 | 0.35 |
| P2 | defender | 0.18 | 0.65 |
| P3 | midfielder | 0.40 | 0.30 |
| P4 | midfielder | 0.40 | 0.70 |
| P5 | striker | 0.62 | 0.50 |
| P6 | goalkeeper | 0.03 | 0.50 |

Coordinates are fractions of the field for Team 1, which attacks right.
Team 2 mirrors each x coordinate as \\(1-f_x\\).

## Entity state

The world is represented by three core classes from `src/entities.py`.

### `Ball`

- position and velocity;
- radius 5 px;
- current possessor or `None`;
- last toucher for restart attribution; and
- `loose_timer`, which prevents immediate recapture after a kick.

### `Player`

- position, velocity, radius 10 px, and maximum speed 100 px/s;
- role, home position, team colour, and goalkeeper flag;
- facing direction used by carrying, passing, and human aim;
- stamina, shot power, and action cooldown; and
- methods for movement, carrying, passing, shooting, and ball control.

### `Team`

- ordered player roster;
- score-adjacent telemetry: shot count and possession time; and
- display identity.

The authoritative formation is `GameEngine.FORMATION`. The legacy
`Team.formation = "4-4-2"` string is not used by the simulation.

## Discrete-time integration

The engine integrates position and then applies exponential velocity decay:

<div class="math">
\[
\mathbf{x}_{t+\Delta t}
  = \mathbf{x}_t + \mathbf{v}_t\Delta t,
\qquad
\mathbf{v}_{t+\Delta t}
  = \mathbf{v}_t\mu^{\Delta t}.
\]
</div>

Here \\(\mu\\) is the fraction of velocity retained after one second:

- players: \\(\mu_e = 0.046\\);
- ball: \\(\mu_b = 0.05\\).

The exponent makes velocity attenuation over a fixed elapsed time independent
of frame rate. Position is advanced before decay, so sampled trajectories
still retain timestep error and are not exactly invariant across frame rates.
For the ball, the equivalent continuous drag rate is

<div class="math">
\[
\lambda = -\ln \mu_b \approx 3.00\ \mathrm{s}^{-1}.
\]
</div>

A ball starting at speed \\(v_0\\) therefore has ideal infinite-horizon travel
distance

<div class="math">
\[
d_\infty = \int_0^\infty v_0e^{-\lambda t}\,dt
          = \frac{v_0}{\lambda}.
\]
</div>

The kick model inverts this relationship to choose a launch speed for an
intended distance.

Ball speed is capped at 900 px/s. An untouched ball that reaches a wall uses
restitution \\(e=0.8\\); once a last toucher exists, field exits are rules
events rather than bounces.

## Movement and momentum

`Player.move_towards()` computes a stamina-adjusted desired velocity toward a
target and blends the current velocity toward it:

<div class="math">
\[
\mathbf{v}
\leftarrow
\mathbf{v}
+ \left(\mathbf{v}^{*}-\mathbf{v}\right)\alpha(\Delta t),
\qquad
\alpha(\Delta t)
= 1-(1-\beta)^{\Delta t f_0},
\]
</div>

where \\(\beta=0.25\\) is the blend per reference frame and
\\(f_0=60\ \mathrm{Hz}\\). Repeated commands converge geometrically, producing
short acceleration, braking, and turning transients rather than teleporting
onto a new velocity.

AI probabilities use the same frame-rate correction:

<div class="math">
\[
p(\Delta t)
= 1-\left(1-p_{60}\right)^{\Delta t f_0}.
\]
</div>

This conversion is applied to stochastic offloads and long shots. The central
tackle probability remains an explicitly per-frame contest parameter in the
current engine.

## Carrying and loose-ball time

While possessed, the ball is placed one player radius plus one ball radius
ahead of the carrier along the facing direction. It inherits the carrier's
velocity. This produces visible dribbling and gives the next kick a sensible
origin.

A kick:

1. points the carrier toward its target;
2. assigns the ball a velocity;
3. releases possession;
4. records the kicker as last toucher;
5. starts 0.3 seconds of uncontrollable loose-ball time; and
6. starts a 0.5-second player action cooldown.

Loose-ball time prevents the kicker from reclaiming a shot or pass on the next
frame.

## Kick power

For unit target direction \\(\hat{\mathbf{u}}\\), kick power \\(P\\), and
stamina power factor \\(\phi\\):

<div class="math">
\[
\mathbf{v}_{\mathrm{ball}} = P\phi\hat{\mathbf{u}}.
\]
</div>

Passes are sized to arrive with modest residual pace:

<div class="math">
\[
P_{\mathrm{pass}}(d)
=
\min\left(
  \max(d\lambda\gamma_p,\ P_{\min}),
  V_{\max}
\right),
\]
</div>

with \\(\gamma_p=1.1\\), \\(P_{\min}=200\ \mathrm{px/s}\\), and
\\(V_{\max}=900\ \mathrm{px/s}\\).

Shots use a larger reach margin and base power:

<div class="math">
\[
P_{\mathrm{shot}}(d)
=
\max\left(
  P_0,
  \min(d\lambda\gamma_s,\ P_{\max})
\right),
\]
</div>

with \\(\gamma_s=1.25\\), \\(P_0=500\ \mathrm{px/s}\\), and
\\(P_{\max}=900\ \mathrm{px/s}\\).

## Stamina

Every player starts with \\(S=100\\) stamina. For speed ratio
\\(\rho=\|\mathbf{v}\|/v_{\max}\\):

<div class="math">
\[
\dot{s} =
\begin{cases}
-c_{\mathrm{sprint}}\rho,
  & \rho > \rho_{\mathrm{sprint}}, \\
+c_{\mathrm{rec}},
  & \rho \lt \rho_{\mathrm{rec}}, \\
0,
  & \text{otherwise}.
\end{cases}
\]
</div>

Defaults:

- sprint threshold \\(\rho_{\mathrm{sprint}}=0.75\\);
- recovery threshold \\(\rho_{\mathrm{rec}}=0.5\\);
- sprint drain \\(c_{\mathrm{sprint}}=2.5\ \mathrm{s}^{-1}\\);
- recovery \\(c_{\mathrm{rec}}=5\ \mathrm{s}^{-1}\\);
- pass cost 5; and
- shot cost 10.

Fatigue applies linear factors with floors:

<div class="math">
\[
\psi(s)
= \psi_{\min} + (1-\psi_{\min})\frac{s}{S},
\qquad
\phi(s)
= \phi_{\min} + (1-\phi_{\min})\frac{s}{S},
\]
</div>

where \\(\psi_{\min}=0.85\\) is the speed floor and
\\(\phi_{\min}=0.8\\) the kick-power floor. Exhaustion changes outcomes but
does not make a player non-functional.

## Principal physical parameters

| Constant | Meaning | Default |
|---|---|---:|
| `BALL_FRICTION_PER_SEC` | Ball velocity retained after one second | 0.05 |
| `ENTITY_FRICTION_PER_SEC` | Player velocity retained after one second | 0.046 |
| `BALL_MAX_SPEED` | Ball speed cap | 900 px/s |
| `BALL_RESTITUTION` | Untouched-ball wall restitution | 0.8 |
| `LOOSE_BALL_TIME` | Uncontrollable time after a kick | 0.30 s |
| `ACTION_COOLDOWN` | Kicker cooldown | 0.50 s |
| `MOVE_ACCEL_BLEND` | Movement blend at 60 Hz | 0.25 |
| `PASS_STAMINA_COST` | Stamina charged per pass | 5 |
| `SHOT_STAMINA_COST` | Stamina charged per shot | 10 |
| `MIN_SPEED_FACTOR` | Exhausted-player speed floor | 0.85 |
| `MIN_POWER_FACTOR` | Exhausted-player kick floor | 0.80 |
