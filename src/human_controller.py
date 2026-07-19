"""
Human Controller Module
Drives the human-controlled team (Tier 5). The human directly steers a single
*selected* player from the input layer's movement vector; every other teammate
is positioned by the team's existing AIController.

To give the human exclusive control of the selected player, that player is
temporarily pulled out of the team roster while the AI runs, so the AI never
selects, moves, or acts with it. It is restored immediately afterwards (before
the engine integrates positions) and then steered from the current input frame.

Scope note: this task is movement-only. On-ball actions (pass/shoot/sprint) and
dynamic selection/switching land in later Tier 5 tasks; for now the selected
player is a sensible fixed default and simply moves under the input vector.
"""

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
        """Set the player the human directly controls."""
        self.selected_player = player

    def update(self, dt):
        """Position teammates via the AI, then steer the selected player.

        The selected player is hidden from the AI for the duration of the AI
        update so the AI never moves or acts with it; the human owns it.
        """
        selected = self.selected_player
        self._run_ai_without(selected, dt)
        if selected is not None:
            self._steer(selected, dt)

    def _run_ai_without(self, player, dt):
        """Run the team AI with `player` temporarily removed from the roster."""
        players = self.team.players
        if player is not None and player in players:
            index = players.index(player)
            players.remove(player)
            try:
                self.ai.update(dt)
            finally:
                players.insert(index, player)  # restore original order
        else:
            self.ai.update(dt)

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
