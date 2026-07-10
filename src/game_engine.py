"""
Game Engine Module
Manages the overall game state, physics, and interactions between entities.
"""

import pygame
import random
from src.entities import Ball, Player, Team
from src.ai import AIController
from src.ui import UI

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
    
    def create_players(self):
        """Create players for both teams."""
        # Team 1 players (5 players)
        self.team1.add_player(Player("T1P1", self.field_x + self.field_width * 0.2, 
                                     self.field_y + self.field_height * 0.2, self.team1.color))
        self.team1.add_player(Player("T1P2", self.field_x + self.field_width * 0.2, 
                                     self.field_y + self.field_height * 0.5, self.team1.color))
        self.team1.add_player(Player("T1P3", self.field_x + self.field_width * 0.2, 
                                     self.field_y + self.field_height * 0.8, self.team1.color))
        self.team1.add_player(Player("T1P4", self.field_x + self.field_width * 0.4, 
                                     self.field_y + self.field_height * 0.3, self.team1.color))
        self.team1.add_player(Player("T1P5", self.field_x + self.field_width * 0.4, 
                                     self.field_y + self.field_height * 0.7, self.team1.color))
        
        # Team 2 players (5 players)
        self.team2.add_player(Player("T2P1", self.field_x + self.field_width * 0.8, 
                                     self.field_y + self.field_height * 0.2, self.team2.color))
        self.team2.add_player(Player("T2P2", self.field_x + self.field_width * 0.8, 
                                     self.field_y + self.field_height * 0.5, self.team2.color))
        self.team2.add_player(Player("T2P3", self.field_x + self.field_width * 0.8, 
                                     self.field_y + self.field_height * 0.8, self.team2.color))
        self.team2.add_player(Player("T2P4", self.field_x + self.field_width * 0.6, 
                                     self.field_y + self.field_height * 0.3, self.team2.color))
        self.team2.add_player(Player("T2P5", self.field_x + self.field_width * 0.6, 
                                     self.field_y + self.field_height * 0.7, self.team2.color))
    
    def reset_positions(self):
        """Reset positions of all players and the ball."""
        # Reset ball position
        self.ball.x = self.field_x + self.field_width // 2
        self.ball.y = self.field_y + self.field_height // 2
        self.ball.vx = 0
        self.ball.vy = 0
        
        # Reset team 1 positions (left side)
        for i, player in enumerate(self.team1.players):
            player.x = self.field_x + self.field_width * 0.2 + (i % 2) * 0.2 * self.field_width
            player.y = self.field_y + (i / 4 + 0.2) * self.field_height
        
        # Reset team 2 positions (right side)
        for i, player in enumerate(self.team2.players):
            player.x = self.field_x + self.field_width * 0.8 - (i % 2) * 0.2 * self.field_width
            player.y = self.field_y + (i / 4 + 0.2) * self.field_height
    
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
            
            # Simple collision detection with field boundaries
            player.x = max(self.field_x, min(player.x, self.field_x + self.field_width))
            player.y = max(self.field_y, min(player.y, self.field_y + self.field_height))
        
        # Keep the ball glued to its carrier so it travels with the dribbler
        if self.ball.possession is not None:
            self.ball.possession.carry_ball(self.ball)
        
        # Ball collision with field boundaries
        if self.ball.x < self.field_x:
            # Check if ball crossed the left goal line
            if (self.field_y + self.field_height * 0.3 <= self.ball.y <= 
                self.field_y + self.field_height * 0.7):
                self.team2_score += 1
                self.reset_positions()
            else:
                self.ball.x = self.field_x
                self.ball.vx *= -0.8  # Bounce with energy loss
        
        if self.ball.x > self.field_x + self.field_width:
            # Check if ball crossed the right goal line
            if (self.field_y + self.field_height * 0.3 <= self.ball.y <= 
                self.field_y + self.field_height * 0.7):
                self.team1_score += 1
                self.reset_positions()
            else:
                self.ball.x = self.field_x + self.field_width
                self.ball.vx *= -0.8  # Bounce with energy loss
        
        if self.ball.y < self.field_y:
            self.ball.y = self.field_y
            self.ball.vy *= -0.8  # Bounce with energy loss
        
        if self.ball.y > self.field_y + self.field_height:
            self.ball.y = self.field_y + self.field_height
            self.ball.vy *= -0.8  # Bounce with energy loss
    
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