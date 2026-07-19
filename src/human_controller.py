"""
Human Controller Module
Drives the human-controlled team (Tier 5). The human directly steers a single
*selected* player from the input layer's movement vector; every other teammate
is positioned by the team's existing AIController.

The selected player is excluded from the AI via ``AIController.controlled_player``:
the AI never selects, moves, or acts with it, yet it stays in the team roster so
possession/team-state logic remains correct (teammates support the attack when
the human carries the ball).

Selection: while the human team is in possession the controlled player is the
ball carrier (so the human always plays the on-ball player, and control hands
off to a pass receiver once they collect it); while defending it is
auto-selected as the outfield player closest to the ball, and the switch action
cycles outward to the next-closest.
"""

import math

from src.input import Action

# Distance (px) of the steering target ahead of the player in the input
# direction. ``Player.move_towards`` normalises the direction, so the exact
# value only needs to be positive: it sets a target point, not a speed.
STEER_AHEAD = 20

# Sprint (held) multiplies the steering speed above the normal pace; the
# stamina model drains faster at the higher speed, so no extra cost is needed.
SPRINT_MULTIPLIER = 1.3

# A pass targets teammates within this cone of the aim direction: dot >= 0.3
# is roughly a 145-degree-wide cone (+/-72 degrees) around where the human aims.
PASS_CONE_DOT = 0.3


class HumanController:
    """Controls the human team: one human-steered player, AI for the rest."""

    def __init__(self, team, ai_controller, engine):
        self.team = team
        self.ai = ai_controller
        self.engine = engine
        self.selected_player = self._default_selection()
        # Offset into the distance-ordered defenders: 0 = closest to the ball
        # (the auto-selection); the switch action increments it to cycle outward.
        self.switch_offset = 0

    def _default_selection(self):
        """Initial player to control: the striker, else any outfield player."""
        outfield = [p for p in self.team.players if not p.is_goalkeeper]
        if not outfield:
            return None
        for player in outfield:
            if player.role == "striker":
                return player
        return outfield[0]

    def select(self, player):
        """Set the player the human controls (resets the switch cycle)."""
        self.selected_player = player
        self.switch_offset = 0

    def update(self, dt):
        """Pick the controlled player, run the AI (excluding it), then act/steer."""
        self._update_selection()
        selected = self.selected_player
        # The AI positions the rest of the team but never touches the human's
        # player; it stays in the roster so the team's state stays correct.
        self.ai.controlled_player = selected
        self.ai.update(dt)
        if selected is not None:
            self._handle_actions(selected)
            self._steer(selected, dt)

    # --- Player selection ------------------------------------------------

    def _is_defending(self):
        """True when the human team is not in possession of the ball."""
        return self.engine.ball.possession not in self.team.players

    def _outfield_by_distance(self):
        """Outfield players (keeper excluded) ordered nearest-first to the ball.

        The first element is exactly ``AIController._nearest_outfield_to_ball``'s
        result; the rest give the switch cycle its outward order.
        """
        ball = self.engine.ball
        outfield = [p for p in self.team.players if not p.is_goalkeeper]
        return sorted(outfield, key=lambda p: p.distance_to(ball))

    def _switch_pressed(self):
        """Whether the switch-player action fired this frame (edge-triggered).

        Debounce comes from the input layer: SWITCH_PLAYER is present only on
        the frame its key goes down, so one press advances exactly one player.
        """
        frame = self.engine.player_input
        return frame is not None and Action.SWITCH_PLAYER in frame.actions

    def _update_selection(self):
        """Follow the ball on attack; auto-select/cycle defenders on defense.

        While in possession the controlled player is the ball carrier, so the
        human always plays the on-ball player (control naturally hands off to a
        pass receiver once they collect it). While defending, the controlled
        player is the outfield player at ``switch_offset`` in the
        distance-ordered list (offset 0 = closest); a switch press advances the
        offset, wrapping around. Regaining possession resets the cycle.
        """
        if not self._is_defending():
            self.selected_player = self.engine.ball.possession
            self.switch_offset = 0
            return
        if self._switch_pressed():
            self.switch_offset += 1
        candidates = self._outfield_by_distance()
        if candidates:
            self.selected_player = candidates[self.switch_offset % len(candidates)]

    # --- On-ball actions -------------------------------------------------

    def _handle_actions(self, player):
        """Pass or shoot for the on-ball player from this frame's presses.

        Both are gated by ``Player.can_act()`` (the post-kick cooldown) and
        require the player to actually hold the ball. Shoot takes precedence
        over pass when both are pressed in the same frame.
        """
        frame = self.engine.player_input
        if frame is None:
            return
        ball = self.engine.ball
        if ball.possession is not player or not player.can_act():
            return
        if Action.SHOOT in frame.actions:
            target_x, target_y = self.ai._pick_shot_target(player)
            if player.shoot(ball, target_x, target_y):
                self.team.shots += 1
        elif Action.PASS in frame.actions:
            target = self._pass_target(player, self._aim_direction(player))
            if target is not None:
                player.pass_ball(ball, target)

    def _aim_direction(self, player):
        """Aim direction for a pass: this frame's input, else the facing."""
        dx, dy = self._input_move()
        if dx != 0.0 or dy != 0.0:
            return dx, dy
        return player.facing_x, player.facing_y

    def _pass_target(self, carrier, direction):
        """Best outfield teammate to pass to in the aim direction (facing cone).

        Prefers the nearest teammate within a cone of the aim direction; if none
        is in the cone, falls back to the nearest teammate overall so a pass
        always finds someone.
        """
        dx, dy = direction
        mates = [p for p in self.team.players
                 if p is not carrier and not p.is_goalkeeper]
        if not mates:
            return None
        if dx != 0.0 or dy != 0.0:
            in_cone = []
            for mate in mates:
                mx, my = mate.x - carrier.x, mate.y - carrier.y
                dist = math.hypot(mx, my)
                if dist > 0 and (mx / dist * dx + my / dist * dy) >= PASS_CONE_DOT:
                    in_cone.append(mate)
            if in_cone:
                return min(in_cone, key=carrier.distance_to)
        return min(mates, key=carrier.distance_to)

    def _sprinting(self):
        """Whether the sprint modifier is held this frame."""
        frame = self.engine.player_input
        return frame is not None and Action.SPRINT in frame.held

    # --- Steering --------------------------------------------------------

    def _input_move(self):
        """This frame's (dx, dy) movement vector from the input layer."""
        frame = self.engine.player_input
        return frame.move if frame is not None else (0.0, 0.0)

    def _steer(self, player, dt):
        """Drive the selected player from the input vector.

        Sprint (held) raises the target speed; with no directional input the
        player is left uncommanded so friction decelerates it to a stop.
        """
        dx, dy = self._input_move()
        if dx == 0.0 and dy == 0.0:
            return
        speed = player.max_speed
        if self._sprinting():
            speed *= SPRINT_MULTIPLIER
        player.move_towards(player.x + dx * STEER_AHEAD,
                            player.y + dy * STEER_AHEAD,
                            speed, dt)
