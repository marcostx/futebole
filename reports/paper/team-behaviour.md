# Team Behaviour

This chapter describes `AIController`. In all-AI mode it drives every player.
On a human-designated team it drives every player except
`controlled_player`; the selected player remains visible to all team-state and
support calculations.

## Team state machine

Each controller classifies the frame into one of three states:

| State | Condition |
|---|---|
| `attack` | A teammate holds the ball |
| `defense` | An opponent holds the ball |
| `possession` | Ball is free and this team's nearest outfielder is closer than the opponent's nearest |

For a free ball the state falls back to `defense` when the opposing side is
closer.

The state determines temporary roles:

- **active player:** carrier in attack; nearest available outfielder to the
  ball in defense or a free-ball chase;
- **support player:** nearest non-goalkeeper, non-defender teammate to the
  carrier; and
- **shape players:** everyone else, positioned by formation, defensive block,
  marking, or rest-defence rules.

The goalkeeper never becomes an outfield presser or support runner.

## Elastic formation

For ball position \\(\mathbf{b}\\), field centre \\(\mathbf{c}\\), player home
\\(\mathbf{h}_i\\), and attack direction \\(\sigma\\), the neutral shape target
is

<div class="math">
\[
\mathbf{T}_i =
\Pi_{\mathcal{F}}\left[
  \mathbf{h}_i
  + \kappa_{\mathrm{slide}}(\mathbf{b}-\mathbf{c})
  + \delta\sigma\hat{\mathbf{e}}_x
\right].
\]
</div>

Defaults:

- slide gain \\(\kappa_{\mathrm{slide}}=0.5\\);
- attack push \\(\delta=+130\ \mathrm{px}\\);
- defense drop \\(\delta=-60\ \mathrm{px}\\);
- no phase shift in free-ball possession; and
- a 35 px interior clamp.

The formation moves toward the ball without collapsing all home positions
onto it. Mirroring x coordinates gives both teams the same geometry in
opposite directions.

## Defensive organisation

### Two-bank block

When the ball is more than 300 px from the defended goal, defenders and
midfielders form two banks.

For normalized horizontal threat distance
\\(t=\min(1,d_x(\mathbf{b},\mathrm{goal})/F_W)\\):

<div class="math">
\[
D(t)=D_{\min}+(D_{\max}-D_{\min})t,
\]
</div>

<div class="math">
\[
G(t)=G_{\min}+(G_{\max}-G_{\min})t.
\]
</div>

The defensive line depth \\(D\\) spans 80–240 px and the inter-bank gap
\\(G\\) spans 60–120 px. Banks are spaced laterally by 100 px and follow the
ball's y coordinate with gain 0.6. Slots are assigned in home-y order so
players do not swap sides.

![Two-bank defensive block](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/defensive_block.png)

### Goal-side marking

Inside the 300 px threat zone, available markers are greedily paired to
nearby opponents. A marker targets a point 22 px from the opponent toward the
defended goal:

<div class="math">
\[
\mathbf{m}
=
\mathbf{o}
+ 22
\frac{\mathbf{g}-\mathbf{o}}
     {\|\mathbf{g}-\mathbf{o}\|}.
\]
</div>

The carrier is excluded from the mark list because the active defender
presses it. An unassigned defender who is goal-side of the ball converges on
the carrier instead of becoming a second goalkeeper.

![Goal-side man marking](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/man_marking.png)

### Rest defence

During an attack, both defenders hold a cover line behind the ball instead of
joining the forward push:

<div class="math">
\[
D_{\mathrm{rest}}
=
\operatorname{clip}
\left(
  d_x(\mathbf{b},\mathrm{own\ goal})-130,\ 130,\ 330
\right)\ \mathrm{px}.
\]
</div>

The line follows the ball laterally with gain 0.4. This reduces unopposed
counter-attacks after a turnover.

![Rest-defence cover line](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/rest_defense.png)

## Carrier policy

An AI carrier evaluates actions in priority order:

```text
1. If inside 150 px and shot angle ≥ 0.35 rad:
       shoot toward the blocker-aware corner target.
2. Else if inside 320 px and the dt-scaled 0.02 long-shot gate fires:
       take a long shot.
3. Else if an opponent is within 30 px and the dt-scaled 0.06 gate fires:
       pass to the best target, allowing a backward outlet.
4. Else in build-up:
       pass only if the best receiver is at least 5 px more open.
5. Otherwise:
       dribble goalward, widen a tight angle, and evade the nearest presser.
```

Every failed branch falls through to the next one; dribbling is the default.

## Pass selection

### Candidate range

- short passes: up to 130 px in any allowed direction;
- driven long passes: up to 260 px for forward targets;
- ordinary long target openness: at least 60 px from the nearest opponent;
- long target already in shooting range: relaxed to 30 px.

Candidates in an offside position are rejected.

### Openness and score

Receiver openness is its nearest-opponent distance:

<div class="math">
\[
\omega(p)
=
\min_{o\in\mathrm{opponents}}
\|\mathbf{x}_p-\mathbf{x}_o\|.
\]
</div>

Candidates maximize

<div class="math">
\[
J(r)
=
\omega(r)
- \frac{1}{2}|x_{\mathrm{goal}}-x_r|,
\]
</div>

balancing freedom from pressure with progress toward goal.

### Lane veto

For carrier \\(\mathbf{p}\\), receiver \\(\mathbf{q}\\), and opponent
\\(\mathbf{o}\\), project the opponent onto the pass segment:

<div class="math">
\[
t^*
=
\frac{
  (\mathbf{o}-\mathbf{p})\cdot(\mathbf{q}-\mathbf{p})
}{
  \|\mathbf{q}-\mathbf{p}\|^2
},
\]
</div>

<div class="math">
\[
d^*
=
\left\|
  \mathbf{o}
  - \left(\mathbf{p}+t^*(\mathbf{q}-\mathbf{p})\right)
\right\|.
\]
</div>

The lane is blocked when \\(t^*\in[0.15,1]\\) and \\(d^*<25\ \mathrm{px}\\).
The first 15% is ignored because an opponent beside the carrier is handled by
the pressure-offload gate.

Human passing does not use this candidate pipeline; it uses the facing-cone
heuristic described in [Architecture and Control](architecture.md).

## Shooting

The implementation estimates the angular width of the goal mouth as seen from
the carrier:

<div class="math">
\[
\theta(\mathbf{x})
=
\left|
\operatorname{atan2}(y_{\mathrm{top}}-y,\ x_g-x)
-
\operatorname{atan2}(y_{\mathrm{bottom}}-y,\ x_g-x)
\right|.
\]
</div>

This is the raw absolute `atan2` difference. It is not wrapped onto the
smaller angular interval, so mirrored positions facing the left and right
goals can produce different values; the current equation documents that
implementation rather than an ideal symmetric angle.

Inside the 150 px close-shot range, the carrier shoots only when
\\(\theta\ge0.35\\) rad (about 20°). From a tighter angle it dribbles inward.

The target is the goal corner farther from the opponent nearest goal centre,
usually the keeper. It is inset 15 px from the post and placed 10 px beyond
the goal line. Uniform vertical noise grows with distance:

<div class="math">
\[
y_{\mathrm{aim}}
= y_{\mathrm{corner}}+\mathrm{U}(-\nu,\nu),
\]
</div>

<div class="math">
\[
\nu
=
5
+ 15
\min\left(2.2,\frac{d}{R_{\mathrm{shot}}}\right)
\ \mathrm{px}.
\]
</div>

Human shooting calls the same target function, so aiming assistance is shared.

## Support runs

The support runner targets a point 150 px ahead of the carrier at the carrier's
y coordinate. The target is clamped at least 12 px behind the current offside
line to avoid a runner oscillating in and out of the AI candidate set.

Other attacking outfield players move toward elastic shape at 85% tempo.
Defensive off-ball movement uses 95% tempo, while active chases and support
runs use full requested tempo.

![Attack support run](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/attack_support.png)

## Goalkeeper

The keeper has a separate three-mode policy:

1. **Distribute:** with possession, pass to the best open teammate; if no
   target exists, clear 350 px upfield.
2. **Rush:** attack a loose or opponent-held ball within 100 px of the own
   goal centre.
3. **Hold line:** remain at home depth and track the ball's y coordinate,
   clamped 10 px inside the posts.

While holding the ball on action cooldown, the goalkeeper waits rather than
dribbling out. Keeper clearances use the shot mechanic for power but are not
counted as attempts in the HUD.

## Behaviours in context

The publication frames below were captured from seed 7 in all-AI mode. In
interactive mode the renderer additionally shows a cyan selection chevron and
the controls legend.

![Kickoff formation](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/kickoff.png)

After a goal, the conceding team is placed into the same restart geometry:

![Post-goal kickoff](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/post_goal_kickoff.png)

![Goal-line restart](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/goal_line_restart.png)

![Open play at 0:44](https://raw.githubusercontent.com/marcostx/futebole/main/paper/figures/midmatch.png)

## Principal tactical parameters

| Constant | Meaning | Default |
|---|---|---:|
| `SHAPE_SLIDE` | Formation slide gain | 0.5 |
| `ATTACK_PUSH` | Shape advance in attack | 130 px |
| `DEFENSE_DROP` | Shape retreat in defense | 60 px |
| `SHOOT_RANGE` | Deterministic shooting range | 150 px |
| `LONG_SHOT_RANGE` | Outer long-shot range | 320 px |
| `LONG_SHOT_PROB` | Long-shot probability at 60 Hz | 0.02 |
| `PRESSURE_DIST` | Radius for pressured-carrier logic | 30 px |
| `PRESSURE_PASS_PROB` | Offload probability at 60 Hz | 0.06 |
| `MIN_SHOT_ANGLE` | Required close-shot angle | 0.35 rad |
| `LANE_BLOCK_RADIUS` | Pass-corridor veto radius | 25 px |
| `MARK_ZONE_DIST` | Switch from block to marking | 300 px |
| `MARK_DIST` | Goal-side marking offset | 22 px |
| `GK_RUSH_DIST` | Keeper rush radius | 100 px |
