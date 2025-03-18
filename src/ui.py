"""
UI Module
Manages the user interface rendering for the soccer game.
"""

import pygame
import math

class UI:
    """Manages the user interface for the soccer game."""
    def __init__(self, screen, width, height):
        self.screen = screen
        self.width = width
        self.height = height
        self.font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)
    
    def draw_field(self, x, y, width, height):
        """Draw the soccer field."""
        # Draw field background
        pygame.draw.rect(self.screen, (34, 139, 34), (x, y, width, height))
        
        # Draw field border
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, width, height), 2)
        
        # Draw midfield line
        pygame.draw.line(self.screen, (255, 255, 255), 
                         (x + width // 2, y), 
                         (x + width // 2, y + height), 2)
        
        # Draw center circle
        pygame.draw.circle(self.screen, (255, 255, 255), 
                           (x + width // 2, y + height // 2), 
                           50, 2)
        
        # Draw center spot
        pygame.draw.circle(self.screen, (255, 255, 255), 
                           (x + width // 2, y + height // 2), 
                           3)
    
    def draw_goals(self, x, y, width, height):
        """Draw the soccer goals."""
        # Left goal
        pygame.draw.rect(self.screen, (255, 255, 255), 
                         (x - 10, y + height * 0.3, 10, height * 0.4), 2)
                         
        # Right goal
        pygame.draw.rect(self.screen, (255, 255, 255), 
                         (x + width, y + height * 0.3, 10, height * 0.4), 2)
    
    def draw_player(self, player):
        """Draw a player on the screen."""
        # Draw player circle
        pygame.draw.circle(self.screen, player.color, 
                           (int(player.x), int(player.y)), 
                           player.radius)
        
        # Draw player name
        name_text = self.small_font.render(player.name, True, (255, 255, 255))
        self.screen.blit(name_text, (player.x - name_text.get_width() // 2, 
                                     player.y - 25))
        
        # Draw direction indicator (shows where player is moving)
        if player.vx != 0 or player.vy != 0:
            speed = math.sqrt(player.vx ** 2 + player.vy ** 2)
            if speed > 5:  # Only show direction if moving significantly
                norm_vx = player.vx / speed
                norm_vy = player.vy / speed
                pygame.draw.line(self.screen, (255, 255, 255), 
                                (player.x, player.y), 
                                (player.x + norm_vx * 15, player.y + norm_vy * 15), 2)
    
    def draw_ball(self, ball):
        """Draw the ball on the screen."""
        pygame.draw.circle(self.screen, (255, 255, 255), 
                          (int(ball.x), int(ball.y)), 
                          ball.radius)
        
        # Draw a small black pattern on the ball to make it look like a soccer ball
        pygame.draw.circle(self.screen, (0, 0, 0), 
                          (int(ball.x), int(ball.y)), 
                          ball.radius - 2, 1)
    
    def draw_scoreboard(self, team1_score, team2_score, game_time, match_duration):
        """Draw the scoreboard showing score and time."""
        # Create scoreboard background
        pygame.draw.rect(self.screen, (0, 0, 0), (0, 0, self.width, 40))
        
        # Draw scores
        score_text = self.font.render(f"Team 1: {team1_score} - Team 2: {team2_score}", 
                                     True, (255, 255, 255))
        self.screen.blit(score_text, (self.width // 2 - score_text.get_width() // 2, 5))
        
        # Draw game time
        minutes = int(game_time) // 60
        seconds = int(game_time) % 60
        time_text = self.font.render(f"Time: {minutes:02d}:{seconds:02d} / {match_duration//60:02d}:00", 
                                    True, (255, 255, 255))
        self.screen.blit(time_text, (10, 5))
        
        # Draw game state info (could be expanded)
        if game_time >= match_duration:
            state_text = self.font.render("Game Over", True, (255, 0, 0))
            self.screen.blit(state_text, (self.width - state_text.get_width() - 10, 5))