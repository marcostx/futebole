"""
Game Engine Module
Manages the overall game state, physics, and interactions between entities.
"""

import math
import pygame
import random
from src.entities import Ball, Player, Team
from src.ai import AIController
from src.ui import UI

# Per-frame probability that a contesting opponent wins the ball from the
# current holder while within control range. Tunable.
TACKLE_SUCCESS_PROB = 0.05


class GameEngine:
    def __init__(self):
        """Initialize the game engine with all necessary components."""
        # Screen dimensions
        self.WIDTH = 800
        self.HEIGHT = 600
        
        # Create the screen
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Soccer Simulation")
        
        # Create UI
        self.ui = UI(self.screen, self.WIDTH, self.HEIGHT)
        
        # Create game objects
        self.init_game_objects()
        
        # Game state
        self.paused = False
        self.game_time = 0  # in seconds
        self.match_duration = 90  # 90 seconds match
        self.last_update_time = pygame.time.get_ticks()
        
        # Team scores
        self.team1_score = 0
        self.team2_score = 0
        
        # AI controllers
        self.team1_ai = AIController(self.team1, self.team2, self.ball)
        self.team2_ai = AIController(self.team2, self.team1, self.ball)
    
    def init_game_objects(self):
        """Initialize all game objects: ball, players, teams."""
        # Create field dimensions
        self.field_width = self.WIDTH - 100
        self.field_height = self.HEIGHT - 100
        self.field_x = 50
        self.field_y = 50
        
        # Create ball
        self.ball = Ball(self.field_x + self.field_width // 2, 
                         self.field_y + self.field_height // 2)
        
        # Create teams
        self.team1 = Team("Team 1", (255, 0, 0))  # Red team
        self.team2 = Team("Team 2", (0, 0, 255))  # Blue team
        
        # Add players to teams
        self.create_players()
        
        # Set initial positions
        self.reset_positions()
    
    # 2-2-1 formation for Team 1 (attacks right). Fractions of the field;
    # Team 2 mirrors the x fraction (1 - fx) since it attacks left.
    FORMATION = [
        ("defender", 0.18, 0.35),
        ("defender", 0.18, 0.65),
        ("midfielder", 0.40, 0.30),
        ("midfielder", 0.40, 0.70),
        ("striker", 0.62, 0.50),
    ]
    
    def create_players(self):
        """Create both teams' players with roles and formation home positions."""
        for idx, (role, fx, fy) in enumerate(self.FORMATION, start=1):
            self._add_formation_player(self.team1, f"T1P{idx}", role, fx, fy)
            self._add_formation_player(self.team2, f"T2P{idx}", role, 1 - fx, fy)
    
    def _add_formation_player(self, team, name, role, fx, fy):
        """Create a player at a formation slot and record its home position."""
        home_x = self.field_x + self.field_width * fx
        home_y = self.field_y + self.field_height * fy
        player = Player(name, home_x, home_y, team.color)
        player.role = role
        player.home_x = home_x
        player.home_y = home_y
        team.add_player(player)
    
    def reset_positions(self):
        """Reset positions of all players and the ball."""
        # Reset ball position
        self.ball.x = self.field_x + self.field_width // 2
        self.ball.y = self.field_y + self.field_height // 2
        self.ball.vx = 0
        self.ball.vy = 0
        # Clear possession so the carry logic doesn't snap the ball back to a
        # stale possessor after a goal/reset (kickoff is a free ball).
        self.ball.possession = None
        self.ball.loose_timer = 0.0
        
        # Send every player back to its formation home position.
        for player in self.team1.players + self.team2.players:
            player.x = player.home_x
            player.y = player.home_y
            player.vx = 0
            player.vy = 0
    
    def _same_team(self, player_a, player_b):
        """Whether two players belong to the same team."""
        return (player_a in self.team1.players) == (player_b in self.team1.players)
    
    def resolve_possession(self):
        """Decide ball control with a single, order-independent contest.
        
        Replaces the old per-AI "last writer wins" grabs that unfairly gave
        possession to whichever team's controller ran last each frame.
        
        Rules:
        - A player can only gain the ball while off cooldown and in range, so
          a player who just kicked (on cooldown) cannot instantly reclaim it.
        - A free ball goes to the closest eligible player.
        - The current holder keeps the ball unless a contesting opponent wins
          a probabilistic tackle; teammates never steal from each other.
        """
        ball = self.ball
        
        # While the ball is in flight (just kicked) nobody can control it, so
        # shots can reach the goal and passes can reach a teammate.
        if ball.loose_timer > 0:
            return
        
        holder = ball.possession
        all_players = self.team1.players + self.team2.players
        
        # If the recorded holder has drifted out of control range, treat the
        # ball as free. Otherwise a stale possessor would get the ball
        # teleported back to them by carry_ball().
        if holder is not None and not holder.can_control_ball(ball):
            ball.possession = None
            holder = None
        
        # Players able to take control right now: in range and off cooldown.
        takers = [p for p in all_players
                  if p is not holder and p.can_control_ball(ball) and p.can_act()]
        
        if holder is None:
            if takers:
                ball.possession = min(takers, key=lambda p: p.distance_to(ball))
            return
        
        # Holder keeps the ball unless an opponent wins a tackle this frame.
        opponents = [p for p in takers if not self._same_team(p, holder)]
        if opponents and random.random() < TACKLE_SUCCESS_PROB:
            ball.possession = min(opponents, key=lambda p: p.distance_to(ball))
    
    def _clamp_to_field(self, player):
        """Clamp a player's center point to the field boundaries.
        
        Note this clamps the center (x, y); since players are drawn as circles
        of radius `player.radius`, up to that radius may extend past the edge.
        """
        player.x = max(self.field_x, min(player.x, self.field_x + self.field_width))
        player.y = max(self.field_y, min(player.y, self.field_y + self.field_height))
    
    def _separation_axis(self, a, b):
        """Unit vector from a to b and their distance; (1,0,0) if coincident."""
        dx = b.x - a.x
        dy = b.y - a.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return 1.0, 0.0, 0.0
        return dx / dist, dy / dist, dist
    
    def separate_players(self):
        """Push apart any overlapping players (circle-based collision).
        
        Each overlapping pair is split apart along the line joining their
        centers. If clamping one player at a boundary eats part of the push,
        the remaining overlap is redistributed to whichever player can still
        move, so a single call fully resolves the overlap when there is room.
        """
        players = self.team1.players + self.team2.players
        for i in range(len(players)):
            a = players[i]
            for j in range(i + 1, len(players)):
                self._resolve_overlap(a, players[j])
    
    def _resolve_overlap(self, a, b):
        """Separate a single pair of players if they overlap."""
        min_dist = a.radius + b.radius
        nx, ny, dist = self._separation_axis(a, b)
        overlap = min_dist - dist
        if overlap <= 0:
            return
        
        # First split the overlap evenly between the two players.
        a.x -= nx * overlap / 2
        a.y -= ny * overlap / 2
        b.x += nx * overlap / 2
        b.y += ny * overlap / 2
        self._clamp_to_field(a)
        self._clamp_to_field(b)
        
        # Redistribute any overlap left after clamping to the player that can
        # still move (push b fully away first, then a with whatever remains).
        for mover, sign in ((b, 1), (a, -1)):
            nx, ny, dist = self._separation_axis(a, b)
            overlap = min_dist - dist
            if overlap <= 1e-9:
                break
            mover.x += sign * nx * overlap
            mover.y += sign * ny * overlap
            self._clamp_to_field(mover)
    
    def update(self):
        """Update game state."""
        if self.paused:
            return
            
        # Calculate time delta
        current_time = pygame.time.get_ticks()
        dt = (current_time - self.last_update_time) / 1000.0  # Convert to seconds
        self.last_update_time = current_time
        
        # Update game time
        self.game_time += dt
        if self.game_time >= self.match_duration:
            self.end_game()
        
        # Update AI decisions
        self.team1_ai.update(dt)
        self.team2_ai.update(dt)
        
        # Update ball
        self.ball.update(dt)
        
        # Update players
        for player in self.team1.players + self.team2.players:
            player.update(dt)
            self._clamp_to_field(player)
        
        # Resolve who controls the ball via a fair, order-independent contest
        self.resolve_possession()
        
        # Push apart any overlapping players so they don't stack up
        self.separate_players()
        
        # Keep the ball glued to its carrier so it travels with the dribbler
        if self.ball.possession is not None:
            self.ball.possession.carry_ball(self.ball)
        
        # Ball vs field edges: goals and wall bounces
        self.handle_ball_boundaries()
    
    def goal_mouth(self):
        """(top_y, bottom_y) of the goal opening on either goal line."""
        return (self.field_y + self.field_height * 0.3,
                self.field_y + self.field_height * 0.7)
    
    def handle_ball_boundaries(self):
        """Resolve the ball against the field edges.
        
        Scores a goal when the ball's center crosses a goal line within the
        goal mouth, otherwise bounces the ball off the wall. Returns "team1",
        "team2", or None depending on whether a goal was scored.
        """
        ball = self.ball
        goal_top, goal_bottom = self.goal_mouth()
        scorer = None
        
        if ball.x < self.field_x:
            # Left goal is Team 1's own net; Team 2 attacks it.
            if goal_top <= ball.y <= goal_bottom:
                self.team2_score += 1
                scorer = "team2"
            else:
                ball.x = self.field_x
                ball.vx *= -0.8  # Bounce with energy loss
        elif ball.x > self.field_x + self.field_width:
            # Right goal is Team 2's own net; Team 1 attacks it.
            if goal_top <= ball.y <= goal_bottom:
                self.team1_score += 1
                scorer = "team1"
            else:
                ball.x = self.field_x + self.field_width
                ball.vx *= -0.8  # Bounce with energy loss
        
        if scorer is not None:
            self.reset_positions()
            return scorer
        
        if ball.y < self.field_y:
            ball.y = self.field_y
            ball.vy *= -0.8  # Bounce with energy loss
        elif ball.y > self.field_y + self.field_height:
            ball.y = self.field_y + self.field_height
            ball.vy *= -0.8  # Bounce with energy loss
        
        return None
    
    def render(self):
        """Render the current game state."""
        # Clear the screen
        self.screen.fill((0, 0, 0))
        
        # Draw field
        self.ui.draw_field(self.field_x, self.field_y, self.field_width, self.field_height)
        
        # Draw goals
        self.ui.draw_goals(self.field_x, self.field_y, self.field_width, self.field_height)
        
        # Draw players
        for player in self.team1.players + self.team2.players:
            self.ui.draw_player(player)
        
        # Draw ball
        self.ui.draw_ball(self.ball)
        
        # Draw UI elements (score, time)
        self.ui.draw_scoreboard(self.team1_score, self.team2_score, self.game_time, self.match_duration)
        
        # Update the display
        pygame.display.flip()
    
    def toggle_pause(self):
        """Toggle the pause state of the game."""
        self.paused = not self.paused
        if not self.paused:
            self.last_update_time = pygame.time.get_ticks()
    
    def reset_game(self):
        """Reset the game state."""
        self.team1_score = 0
        self.team2_score = 0
        self.game_time = 0
        self.reset_positions()
        self.last_update_time = pygame.time.get_ticks()
    
    def end_game(self):
        """End the game and determine the winner."""
        self.paused = True
        # Winner determination logic could be added here