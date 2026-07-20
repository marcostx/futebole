# Architecture and Control

## Runtime modules

The simulation is deliberately small enough that every command can be traced
from input or AI decision to a state transition.

| Module | Responsibility |
|---|---|
| `main.py` | Pygame lifecycle, event loop, pause/reset/quit controls, 60 Hz pacing |
| `src/game_engine.py` | World ownership, controller routing, update order, possession, scoring, and restarts |
| `src/entities.py` | `Ball`, `Player`, and `Team` state plus movement and kick mechanics |
| `src/ai.py` | Team state, formation, defending, carrier decisions, passing, shooting, and goalkeeper policy |
| `src/input.py` | Raw keys to semantic movement/actions |
| `src/human_controller.py` | Human selection, action handling, steering, and AI exclusion |
| `src/ui.py` | Field, entities, selection marker, controls, clock, score, possession, and shots |

The engine owns the world state. Controllers may request movement or kicks,
but they do not integrate positions, decide possession, award goals, or place
restarts.

```text
pygame events ──> input.py ──> InputFrame ───────────────┐
                                                         v
main.py ──> GameEngine ──> HumanController (optional) ──> entities
                    │             │                         ^
                    │             └─ excludes selection ─┐  │
                    ├────────────────────────────────────>│  │
                    └────────────> AIController × 2 ─────┘  │
                    │                                        │
                    ├─ integrate / arbitrate / apply rules ──┘
                    └──────────────────────────────────────> UI
```

## Execution modes

`GameEngine` always creates one `AIController` per team.

| Construction | Team 1 | Team 2 | Used by |
|---|---|---|---|
| `GameEngine()` | AI | AI | `monitor_match.py`, experiments, most mechanics tests |
| `GameEngine(human_team="team1")` | Human-selected player + AI teammates | AI | interactive `main.py` |
| `GameEngine(human_team="team2")` | AI | Human-selected player + AI teammates | supported alternate setup |

When a team is human-designated, `HumanController.update()` performs three
operations:

1. choose the selected outfield player for the current phase;
2. assign that player to `AIController.controlled_player` and update the AI,
   which moves every other teammate; and
3. apply human actions and steering to the selected player.

Keeping the selected player in the roster is important. The AI still sees the
correct possessor and team state, so teammates support a human carrier rather
than behaving as if the ball were loose.

## Frame pipeline

`GameEngine.update()` uses one central pipeline for both control modes:

```text
1. Return immediately when paused.
2. Measure Δt and advance the 90-second match clock.
3. Attempt a pending kickoff pass.
4. Route each team through its AI or mixed human/AI controller.
5. Integrate the ball.
6. Integrate and field-clamp all 12 players.
7. Resolve possession once for everyone.
8. Accumulate held-ball possession time.
9. Separate overlapping player discs.
10. Attach the ball to its carrier.
11. Resolve goals, restarts, or the legacy untouched-ball bounce.
```

The ordering is part of the rules:

- Kickoff happens before controllers can act, preventing a restart from being
  pre-empted.
- Possession is resolved after every controller and integration step. No team
  gets a last-writer advantage.
- Separation precedes carrying the ball so a displaced carrier brings the ball
  to its final position.
- Boundary handling observes the final ball position and last toucher.

## Time model

The interactive loop is capped at 60 frames per second, but the engine uses
the measured timestep `dt`. Movement, friction, stamina, and probabilistic AI
gates scale with `dt`; they do not assume that every runtime frame is exactly
1/60 second.

The headless harness replaces `pygame.time.get_ticks()` with a virtual clock
advanced by `int(1000 / 60) = 16` ms per update. This integer-millisecond
representation produces 5,625 updates in a 90-second match (an effective
62.5 updates/s), and the measured `dt = 0.016` seconds is passed through the
same engine pipeline without waiting for wall-clock time.

## Human input model

`src/input.py` converts physical keys into an immutable `InputFrame`:

- `move`: a normalized eight-direction vector from held movement keys;
- `actions`: edge-triggered pass, shoot, and switch intents; and
- `held`: continuous modifiers, currently sprint.

Opposing directions cancel, and diagonal vectors are normalized, so diagonal
movement is not faster than axial movement.

| Intent | Default binding | Semantics |
|---|---|---|
| Move | W/A/S/D or arrows | Continuous normalized direction |
| Sprint | either Shift key | Held modifier |
| Pass | J | One-frame action |
| Shoot | K | One-frame action |
| Switch defender | Tab | One-frame action |
| Pause / reset / quit | Space / R / Escape | System actions handled by `main.py` |

The bindings are data (`KeyBindings`), not conditionals inside the controller,
which keeps the layer rebindable and testable without a display.

## Player selection

Selection is phase-aware:

- **In possession:** control follows the carrier. When a pass receiver gains
  possession, the human automatically takes control of that player. If the
  goalkeeper holds the ball, the goalkeeper is selected too.
- **Out of possession:** the nearest outfield player to the ball is selected.
  Each Tab press advances through the distance-ordered outfield list and wraps
  at the end.
- **Goalkeepers:** excluded from defensive auto-selection and Tab cycling, but
  controllable while they are the carrier.

The selected player is shown by a cyan chevron. A white ring independently
marks the ball carrier, and a gold ring marks each goalkeeper.

## Human actions

Movement steers toward a point 20 px along the input direction. Normal speed
uses the player's `max_speed`; sprint requests 1.3 times that value. The
shared stamina model still scales the achieved speed and drains high-speed
movement.

On the ball:

- **Shoot** reuses the AI's blocker-aware corner target.
- **Pass** chooses the nearest non-goalkeeper teammate in a ±72° facing cone
  (dot product at least 0.3), then falls back to the nearest teammate.
- If pass and shoot arrive together, shoot takes precedence.
- Both actions require possession and `Player.can_act()`.

Human pass targeting is intentionally direct but less sophisticated than AI
targeting: it does not apply lane or offside vetoes.

## Fairness boundary

Human control changes decision origin, not physical or rules authority:

- controllers cannot directly assign ball possession;
- one central `resolve_possession()` considers both teams;
- human and AI kicks use the same `Player.pass_ball()` and `Player.shoot()`;
- action cooldowns, stamina costs, power floors, loose-ball time, tackles,
  fouls, and restart entitlement are shared; and
- `controlled_player` prevents double commands without removing the player
  from team-state calculations.

When the selected carrier is the goalkeeper, the normal AI goalkeeper policy
is suspended until the ball is released. With no input, that selected keeper
therefore waits rather than distributing automatically.

This is rules-level fairness, not proof of competitive balance. The AI has
lane-aware and offside-aware pass assistance, while the human uses a facing
cone. Human-versus-AI difficulty has not yet been calibrated.
