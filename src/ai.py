"""
AI Module
Implements the artificial intelligence for controlling soccer players.
"""

import random
import math

# How strongly the whole formation slides toward the ball while holding shape
# (0 = stay at home positions, 1 = move as far as the ball is from center).
SHAPE_SLIDE = 0.5

# How far (px) the block pushes toward the opponent goal when attacking and
# drops back toward its own goal when defending. Keeps shape but gives
# attacking depth (so the ball can reach shooting range) and defensive
# compactness.
ATTACK_PUSH = 130
DEFENSE_DROP = 60

# How close (px) an opponent must be to the ball carrier for the carrier to
# feel pressured and look to offload the ball (pass, or shoot if in range)
# rather than keep dribbling.
PRESSURE_DIST = 30

# Distance (px) to the opponent goal within which the carrier will shoot.
SHOOT_RANGE = 150

# Maximum distance (px) a pass can realistically reach a teammate, given the
# ball's rolling physics. Passes are only attempted to teammates within range.
MAX_PASS_DIST = 130

# Field geometry (matches GameEngine: 800x600 screen, 50px margins).
FIELD_CENTER_X = 400
FIELD_CENTER_Y = 300
FIELD_MIN_X, FIELD_MAX_X = 50, 750
FIELD_MIN_Y, FIELD_MAX_Y = 50, 550


class AIController:
    """Controls the AI behavior of a team."""
    def __init__(self, team, opponent_team, ball):
        self.team = team
        self.opponent_team = opponent_team
        self.ball = ball
        self.field_side = 1 if team.name == "Team 1" else -1  # 1 for left to right, -1 for right to left
        self.active_player = None
        self.support_player = None
        self.team_state = "defense"  # defense, possession, attack
    
    def update(self, dt):
        """Update AI decisions for the team."""
        # Update team state
        self.update_team_state()
        
        # Pick this frame's roles. Exactly one player presses the ball; the
        # rest hold their formation shape. Gaining possession is resolved
        # centrally by the engine.
        if self.team_state == "attack":
            # We have the ball: the carrier acts, the nearest teammate supports.
            self.active_player = self.ball.possession
            others = [p for p in self.team.players if p is not self.active_player]
            self.support_player = (min(others, key=lambda p: p.distance_to(self.ball))
                                   if others else None)
        else:
            # We don't have the ball: our nearest player presses it.
            self.active_player = self.team.nearest_player_to_ball(self.ball)
            self.support_player = None
        
        # Execute behaviors based on team state
        if self.team_state == "defense":
            self.execute_defense_behavior(dt)
        elif self.team_state == "possession":
            self.execute_possession_behavior(dt)
        else:  # attack
            self.execute_attack_behavior(dt)
    
    def formation_position(self, player):
        """Target that holds the player's formation shape, slid toward the ball.
        
        The whole team translates toward wherever the ball is (so the block
        shifts up/down and side to side) while keeping each player's relative
        role position, instead of everyone collapsing onto the ball.
        """
        shift_x = (self.ball.x - FIELD_CENTER_X) * SHAPE_SLIDE
        shift_y = (self.ball.y - FIELD_CENTER_Y) * SHAPE_SLIDE
        
        # Push the block forward when attacking, drop it back when defending
        # (field_side points toward the opponent goal).
        if self.team_state == "attack":
            shift_x += ATTACK_PUSH * self.field_side
        elif self.team_state == "defense":
            shift_x -= DEFENSE_DROP * self.field_side
        
        target_x = max(FIELD_MIN_X, min(player.home_x + shift_x, FIELD_MAX_X))
        target_y = max(FIELD_MIN_Y, min(player.home_y + shift_y, FIELD_MAX_Y))
        return target_x, target_y
    
    def update_team_state(self):
        """Update the team's strategic state."""
        # Check if the ball is possessed by any player
        if self.ball.possession is None:
            # Ball is free, check which team is closer
            our_nearest = self.team.nearest_player_to_ball(self.ball)
            their_nearest = self.opponent_team.nearest_player_to_ball(self.ball)
            
            our_distance = our_nearest.distance_to(self.ball)
            their_distance = their_nearest.distance_to(self.ball)
            
            if our_distance < their_distance:
                self.team_state = "possession"  # We're closer, try to get possession
            else:
                self.team_state = "defense"  # They're closer, defend
        elif self.ball.possession in self.team.players:
            self.team_state = "attack"  # We have the ball, attack
        else:
            self.team_state = "defense"  # They have the ball, defend
    
    def execute_defense_behavior(self, dt):
        """Execute defensive behavior for the team."""
        # Active player chases the ball. Gaining possession is resolved
        # centrally by the game engine (see GameEngine.resolve_possession)
        # so it is a fair, order-independent contest.
        if self.active_player:
            self.active_player.move_towards(self.ball.x, self.ball.y, 
                                           self.active_player.max_speed)
        
        # Other players hold their formation shape (slid toward the ball)
        for player in self.team.players:
            if player != self.active_player:
                target_x, target_y = self.formation_position(player)
                player.move_towards(target_x, target_y, player.max_speed * 0.7)
    
    def execute_possession_behavior(self, dt):
        """Execute possession behavior for the team."""
        # Active player goes for the ball. Gaining possession is resolved
        # centrally by the game engine (see GameEngine.resolve_possession).
        if self.active_player:
            self.active_player.move_towards(self.ball.x, self.ball.y, 
                                           self.active_player.max_speed)

        if not self.active_player:
            self.support_player = None
            return
        
        # Support player moves to a good position for receiving a pass
        if self.support_player:
            # Move to a position ahead of the active player
            target_x = self.active_player.x + 50 * self.field_side
            target_y = self.active_player.y
            
            # Add some randomness
            target_x += random.uniform(-20, 20)
            target_y += random.uniform(-20, 20)
            
            self.support_player.move_towards(target_x, target_y, 
                                            self.support_player.max_speed * 0.8)
        
        # Other players hold their formation shape (slid toward the ball)
        for player in self.team.players:
            if player != self.active_player and player != self.support_player:
                target_x, target_y = self.formation_position(player)
                player.move_towards(target_x, target_y, player.max_speed * 0.6)
    
    def _best_pass_target(self, carrier):
        """Pick the best forward, open, reachable teammate to pass to.
        
        Only teammates within MAX_PASS_DIST and ahead of the carrier (toward the
        opponent goal) are considered, so passes make progress and the ball
        isn't cycled sideways/backwards. Returns None if there is no such option.
        """
        opponent_goal_x = FIELD_MAX_X if self.field_side == 1 else FIELD_MIN_X
        candidates = []
        for p in self.team.players:
            if p is carrier or carrier.distance_to(p) > MAX_PASS_DIST:
                continue
            # Only forward options (closer to the opponent goal than the carrier).
            if (p.x - carrier.x) * self.field_side <= 0:
                continue
            candidates.append(p)
        if not candidates:
            return None
        
        def score(p):
            # Openness: distance to the nearest opponent (bigger is better).
            openness = min((p.distance_to(o) for o in self.opponent_team.players),
                           default=1e9)
            # Prefer teammates closer to the opponent goal.
            forwardness = -abs(opponent_goal_x - p.x)
            return openness + 0.5 * forwardness
        
        return max(candidates, key=score)
    
    def execute_attack_behavior(self, dt):
        """Execute attacking behavior for the team."""
        # Get the player with the ball
        ball_carrier = self.ball.possession
        
        if ball_carrier in self.team.players:
            # We have the ball, decide what to do
            opponent_goal_x = 750 if self.field_side == 1 else 50
            opponent_goal_y = 300
            
            # Check if we're in shooting range
            distance_to_goal = math.sqrt((ball_carrier.x - opponent_goal_x) ** 2 + 
                                         (ball_carrier.y - opponent_goal_y) ** 2)
            
            # Is an opponent pressing the carrier too closely?
            nearest_opponent = self.opponent_team.nearest_player_to_ball(self.ball)
            under_pressure = (nearest_opponent is not None and
                              ball_carrier.distance_to(nearest_opponent) < PRESSURE_DIST)
            
            # Try to shoot or pass, but only when off cooldown. `acted` tracks
            # whether a kick actually fired so we can fall back to movement and
            # avoid the carrier standing still while on cooldown.
            acted = False
            if ball_carrier.can_act():
                if distance_to_goal < SHOOT_RANGE:  # Close enough to shoot
                    # Shoot with a slight random deviation
                    target_x = opponent_goal_x + random.uniform(-20, 20)
                    target_y = opponent_goal_y + random.uniform(-20, 20)
                    acted = ball_carrier.shoot(self.ball, target_x, target_y)
                elif under_pressure:
                    # Opponent too close: offload to a teammate to escape the
                    # press instead of dribbling into them (and losing the ball
                    # in a tug-of-war loop).
                    target = self._best_pass_target(ball_carrier)
                    if target is not None:
                        acted = ball_carrier.pass_ball(self.ball, target)
                elif random.random() < 0.03:  # occasional build-up pass
                    target = self._best_pass_target(ball_carrier)
                    if target is not None:
                        acted = ball_carrier.pass_ball(self.ball, target)
            
            if not acted:
                # No kick this frame (out of range/cooldown, or pressured with
                # no reachable pass): dribble towards the goal, steering around
                # a close opponent.
                target_x = ball_carrier.x + 20 * self.field_side
                target_y = ball_carrier.y
                if nearest_opponent and ball_carrier.distance_to(nearest_opponent) < 30:
                    target_y += -20 if ball_carrier.y < nearest_opponent.y else 20
                
                ball_carrier.move_towards(target_x, target_y, ball_carrier.max_speed * 0.8)
        
        # The nearest teammate offers a short forward passing option (within
        # passing range so the ball can advance); the rest hold formation shape.
        for player in self.team.players:
            if player is ball_carrier:
                continue
            if player is self.support_player:
                sx = max(FIELD_MIN_X, min(ball_carrier.x + 60 * self.field_side, FIELD_MAX_X))
                sy = max(FIELD_MIN_Y, min(ball_carrier.y, FIELD_MAX_Y))
                player.move_towards(sx, sy, player.max_speed * 0.9)
            else:
                target_x, target_y = self.formation_position(player)
                player.move_towards(target_x, target_y, player.max_speed * 0.7)
