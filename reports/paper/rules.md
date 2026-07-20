# Rules and Possession

## Why possession is centralized

The first prototype let each team controller assign possession to nearby
players. Because controllers ran sequentially, the second controller could
overwrite the first on every frame; the baseline report measured 0% possession
for Team 1.

The current engine resolves possession once, after both teams have issued
commands and all entities have integrated. Controller order can no longer
decide ownership.

Possession is a discrete state: the ball has at most one holder.

## Eligibility

A player may gain a free ball when all of the following are true:

- the ball's 0.3-second loose timer has expired;
- the player is within control distance
  \\(\|\mathbf{x}_p-\mathbf{x}_b\| < r_p+r_b+5\ \mathrm{px}\\);
- the player's action cooldown has expired; and
- during a restart, the player belongs to the entitled team.

If several players are eligible for a free ball, the closest wins it.

## Possession algorithm

```text
ResolvePossession:
    if ball.loose_timer > 0:
        return

    holder = ball.possession
    if holder exists and holder is outside control range:
        clear possession
        holder = none

    takers = all non-holder players who:
        are in control range,
        are off cooldown, and
        satisfy restart entitlement

    if holder is none:
        if takers is non-empty:
            holder = closest taker
            record holder as last toucher
            clear restart entitlement
        return

    opponents = takers from the other team
    if opponents exist and random() < TACKLE_SUCCESS_PROB:
        tackler = closest opponent
        if random() < FOUL_PROB:
            give tackler FOUL_COOLDOWN
            keep the current holder
        else:
            transfer possession to tackler
            record tackler as last toucher
```

Teammates never take the ball from each other. A player who has just kicked
cannot immediately recapture the kick because both loose-ball time and the
player cooldown are active.

## Tackles and fouls

The default tackle success probability is 0.05 per contested frame. When the
tackle succeeds, a conditional foul probability of 0.15 is applied.

A foul is intentionally simplified:

- the existing holder retains possession;
- the fouler receives a 1.5-second action cooldown; and
- there is no card, free-kick placement, wall, or advantage phase.

This mechanism preserves flow while stopping the same player from
immediately retrying the challenge.

## Kickoff

Team 1 takes the opening kickoff. After a goal, the conceding team restarts.

At reset:

1. every player returns to its formation home;
2. positions are clamped at least 20 px inside the team's own half;
3. the non-kicking team stays at least 60 px from halfway, outside the centre
   circle;
4. the most advanced outfield player of the kicking team moves to the centre
   spot with the ball; and
5. before normal controller updates, the taker passes to one of its two
   nearest outfield teammates, selected uniformly.

The pending flag remains set when the taker is still on cooldown, and the
engine retries on the next frame.

## Goals and field exits

A goal is awarded when the ball centre crosses a goal line inside the central
40% goal mouth.

Every touched ball that exits elsewhere becomes a dead-ball restart:

| Exit | Last touch | Restart |
|---|---|---|
| Sideline | Either team | Throw-in to the other team at the crossing point |
| Goal line outside mouth | Defending team | Corner to attackers at the nearest corner |
| Goal line outside mouth | Attacking team | Goal kick 40 px in front of the defending goal |

The engine places the ball, zeros its velocity and records `restart_team`.
Only that team's players may collect it. The ordinary nearest-player behaviour
then sends a teammate to the ball; there is no separate set-piece formation.

If a carrier dribbles out of play, the carrier is recorded as last toucher
before attribution. A ball with no last toucher uses the old physical wall
bounce instead.

## Simplified offside

Offside is currently a target-selection predicate, not a whistle in the rules
engine. For attack direction \\(\sigma\in\{-1,+1\}\\), receiver \\(p\\) is
considered offside when all three conditions hold:

<div class="math">
\[
(x_p-x_c)\sigma > 0
\quad\land\quad
(x_p-x_b)\sigma > 0
\quad\land\quad
(x_p-x_{(2)})\sigma > 0,
\]
</div>

where:

- \\(x_c\\) is halfway;
- \\(x_b\\) is the ball; and
- \\(x_{(2)}\\) is the second-last opponent's x coordinate.

AI pass selection rejects such a target. Human pass targeting does not run
this filter, which is why the documentation describes offside as a policy
rather than a fully enforced law.

## Player separation

Players are discs of radius 10 px. After integration, every overlapping pair
is projected apart along its line of centres:

1. split the overlap equally between both players;
2. clamp both centres to the field;
3. recompute any overlap left because a boundary absorbed movement; and
4. move whichever player still has room.

Coincident centres use a deterministic horizontal separation axis. This
positional projection eliminated the original stack of agents. Severe overlap
under 15 px fell from 98.4% of prototype frames to 0% in the evaluated
baseline; residual geometric overlap under 20 px occurs on 1.6% of baseline
updates.

## Rules-level fairness

The following properties hold in both all-AI and mixed-control modes:

- one possession resolver sees every player;
- human input cannot assign possession;
- the current holder is not displaced by a teammate;
- both sides use the same control range and cooldown eligibility;
- restart entitlement is team-based, not controller-based;
- human pass and shoot actions call the same entity methods as AI actions; and
- tackle and foul probabilities do not depend on control type.

These invariants are directly exercised by `tests/test_fairness.py`,
`tests/test_possession_contest.py`, `tests/test_match_rules.py`, and
`tests/test_control_mode.py`.

## Deliberate simplifications

- Fouls do not create spatially placed free kicks or cards.
- Offside is not an engine-level stoppage.
- Corners and goal kicks do not trigger dedicated set-piece shapes.
- There are no halves, injury time, penalties, or throw animations.
- The 90-second clock represents one complete match, not 90 real minutes.
