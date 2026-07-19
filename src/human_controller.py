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

from src.input import Action

# Distance (px) of the steering target ahead of the player in the input
# direction. ``Player.move_towards`` normalises the direction, so the exact
# value only needs to be positive: it sets a target point, not a speed.
STEER_AHEAD = 20


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
        """Pick the controlled player, run the AI (excluding it), then steer it."""
        self._update_selection()
        selected = self.selected_player
        # The AI positions the rest of the team but never touches the human's
        # player; it stays in the roster so the team's state stays correct.
        self.ai.controlled_player = selected
        self.ai.update(dt)
        if selected is not None:
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

    # --- Steering --------------------------------------------------------

    def _input_move(self):
        """This frame's (dx, dy) movement vector from the input layer."""
        frame = self.engine.player_input
        return frame.move if frame is not None else (0.0, 0.0)

    def _steer(self, player, dt):
        """Drive the selected player from the input vector.

        With no directional input the player is left uncommanded so the
        engine's friction decelerates it to a natural stop.
        """
        dx, dy = self._input_move()
        if dx == 0.0 and dy == 0.0:
            return
        player.move_towards(player.x + dx * STEER_AHEAD,
                            player.y + dy * STEER_AHEAD,
                            player.max_speed, dt)
