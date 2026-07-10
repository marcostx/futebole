"""
AI Module
Implements the artificial intelligence for controlling soccer players.
"""

import random
import math
from src.utils import get_distance

class AIController:
    """Controls the AI behavior of a team."""
    def __init__(self, team, opponent_team, ball):
        self.team = team
        self.opponent_team = opponent_team
        self.ball = ball
        self.field_side = 1 if team.name == "Team 1" else -1  # 1 for left to right, -1 for right to left
        self.decision_cooldown = 0
        self.active_player = None
        self.support_player = None
        self.team_state = "defense"  # defense, possession, attack
    
    def update(self, dt):
        """Update AI decisions for the team."""
        # Update decision cooldown
        if self.decision_cooldown > 0:
            self.decision_cooldown -= dt
        
        # Update team state
        self.update_team_state()
        
        # Determine which team is closer to the ball
        our_nearest = self.team.nearest_player_to_ball(self.ball)
        their_nearest = self.opponent_team.nearest_player_to_ball(self.ball)
        
        if our_nearest is None:
            self.active_player = None
            self.support_player = None
        elif their_nearest is None or our_nearest.distance_to(self.ball) < their_nearest.distance_to(self.ball):
            # Our team is closer, set the nearest player as active
            if not self.active_player or self.decision_cooldown <= 0:
                self.active_player = our_nearest
                self.decision_cooldown = 0.5  # Make decisions every 0.5 seconds
                
                # Find support player (second nearest to ball)
                support_candidates = [p for p in self.team.players if p != self.active_player]
                if support_candidates:
                    self.support_player = min(support_candidates, 
                                              key=lambda p: p.distance_to(self.ball))
        else:
            # Opponent team is closer, set active player to None
            self.active_player = None
            self.support_player = None
        
        # Execute behaviors based on team state
        if self.team_state == "defense":
            self.execute_defense_behavior(dt)
        elif self.team_state == "possession":
            self.execute_possession_behavior(dt)
        else:  # attack
            self.execute_attack_behavior(dt)
    
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
        # Active player chases the ball
        if self.active_player:
            self.active_player.move_towards(self.ball.x, self.ball.y, 
                                           self.active_player.max_speed)
            
            # Try to take possession of the ball
            if self.active_player.can_control_ball(self.ball):
                self.ball.possession = self.active_player
                self.team_state = "attack"
        
        # Other players move to defensive positions
        for player in self.team.players:
            if player != self.active_player:
                # Move to a defensive position between the ball and our goal
                goal_x = 50 if self.field_side == 1 else 750
                goal_y = 300
                
                # Calculate position between ball and goal
                target_x = (self.ball.x + goal_x) / 2
                target_y = (self.ball.y + goal_y) / 2
                
                # Add more randomness and ensure minimum distance to avoid clustering
                target_x += random.uniform(-5, 5)
                target_y += random.uniform(-5, 5)
                
                player.move_towards(target_x, target_y, player.max_speed * 0.7)
    
    def execute_possession_behavior(self, dt):
        """Execute possession behavior for the team."""
        # Active player goes for the ball
        if self.active_player:
            self.active_player.move_towards(self.ball.x, self.ball.y, 
                                           self.active_player.max_speed)
            
            # Try to take possession of the ball
            if self.active_player.can_control_ball(self.ball):
                self.ball.possession = self.active_player
                self.team_state = "attack"

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
        
        # Other players move to strategic positions
        for player in self.team.players:
            if player != self.active_player and player != self.support_player:
                # Move to a position that provides width and depth
                base_x = self.active_player.x + 80 * self.field_side
                base_y = 300
                
                # Add some randomness for distribution
                target_x = base_x + random.uniform(-40, 40)
                target_y = base_y + random.uniform(-100, 100)
                
                player.move_towards(target_x, target_y, player.max_speed * 0.6)
    
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
            
            # Try to shoot or pass, but only when off cooldown. `acted` tracks
            # whether a kick actually fired so we can fall back to movement and
            # avoid the carrier standing still while on cooldown.
            acted = False
            if ball_carrier.can_act():
                if distance_to_goal < 150:  # Close enough to shoot
                    # Shoot with a slight random deviation
                    target_x = opponent_goal_x + random.uniform(-20, 20)
                    target_y = opponent_goal_y + random.uniform(-20, 20)
                    acted = ball_carrier.shoot(self.ball, target_x, target_y)
                else:
                    # Check if we can pass to a teammate
                    potential_receivers = [p for p in self.team.players if p != ball_carrier]
                    
                    if potential_receivers and random.random() < 0.03:  # 3% chance to pass per frame
                        # Find the best receiver based on positioning
                        best_receiver = min(potential_receivers, 
                                            key=lambda p: (
                                                get_distance(p.x, p.y, opponent_goal_x, opponent_goal_y) -
                                                get_distance(p.x, p.y, ball_carrier.x, ball_carrier.y) * 0.5
                                            ))
                        
                        # Pass to the best receiver
                        acted = ball_carrier.pass_ball(self.ball, best_receiver)
            
            if not acted:
                # No kick this frame (out of range, chose not to pass, or on
                # cooldown): dribble towards the goal so the carrier keeps moving.
                target_x = ball_carrier.x + 20 * self.field_side
                target_y = ball_carrier.y
                
                # Avoid opponents
                nearest_opponent = self.opponent_team.nearest_player_to_ball(self.ball)
                if nearest_opponent:
                    if get_distance(ball_carrier.x, ball_carrier.y, 
                                   nearest_opponent.x, nearest_opponent.y) < 30:
                        # Adjust direction to avoid opponent
                        if ball_carrier.y < nearest_opponent.y:
                            target_y -= 20
                        else:
                            target_y += 20
                
                ball_carrier.move_towards(target_x, target_y, ball_carrier.max_speed * 0.8)
        
        # Other players move to strategic attacking positions
        for player in self.team.players:
            if player != ball_carrier:
                # Move to a position that provides support
                if self.field_side == 1:  # Left to right
                    target_x = min(700, ball_carrier.x + random.uniform(30, 100))
                else:  # Right to left
                    target_x = max(100, ball_carrier.x - random.uniform(30, 100))
                
                target_y = 300 + random.uniform(-120, 120)
                
                player.move_towards(target_x, target_y, player.max_speed * 0.7)
