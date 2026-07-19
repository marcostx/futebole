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
    
    # Keeper marking, carrier, and selection highlight colors
    GK_RING_COLOR = (255, 215, 0)  # gold ring around goalkeepers
    CARRIER_RING_COLOR = (255, 255, 255)  # white halo on the ball carrier
    SELECT_MARKER_COLOR = (0, 255, 255)  # cyan chevron over the human's player
    
    def draw_player(self, player, has_ball=False, selected=False):
        """Draw a player: selection marker, team circle, keeper ring, halo."""
        center = (int(player.x), int(player.y))
        
        # Selection marker: a chevron above the human-controlled player, kept
        # distinct from the possession halo (white) and the keeper ring (gold).
        if selected:
            self.draw_selection_marker(player)
        
        # Possession halo: a white ring slightly larger than the player so
        # it's obvious at a glance who is on the ball.
        if has_ball:
            pygame.draw.circle(self.screen, self.CARRIER_RING_COLOR,
                               center, player.radius + 5, 2)
        
        # Draw player circle
        pygame.draw.circle(self.screen, player.color, center, player.radius)
        
        # Goalkeepers get a gold ring so each team's keeper stands out.
        if player.is_goalkeeper:
            pygame.draw.circle(self.screen, self.GK_RING_COLOR,
                               center, player.radius, 3)
        
        # Draw player name (keepers labelled as such)
        label = f"{player.name} (GK)" if player.is_goalkeeper else player.name
        name_text = self.small_font.render(label, True, (255, 255, 255))
        self.screen.blit(name_text, (player.x - name_text.get_width() // 2, 
                                     player.y - 25))
        
        # Stamina bar under the player: green when fresh, red when gassed.
        fitness = player.stamina_factor()
        bar_w, bar_h = 20, 3
        bar_x = int(player.x - bar_w / 2)
        bar_y = int(player.y + player.radius + 4)
        fill_color = (int(220 * (1 - fitness)), int(200 * fitness), 40)
        pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(self.screen, fill_color,
                         (bar_x, bar_y, int(bar_w * fitness), bar_h))
        
        # Draw direction indicator (shows where player is moving)
        if player.vx != 0 or player.vy != 0:
            speed = math.sqrt(player.vx ** 2 + player.vy ** 2)
            if speed > 5:  # Only show direction if moving significantly
                norm_vx = player.vx / speed
                norm_vy = player.vy / speed
                pygame.draw.line(self.screen, (255, 255, 255), 
                                (player.x, player.y), 
                                (player.x + norm_vx * 15, player.y + norm_vy * 15), 2)
    
    def draw_selection_marker(self, player):
        """Draw a downward cyan chevron above the human-controlled player.
        
        Sits above the name label so it never clashes with the possession
        halo (white) or the goalkeeper ring (gold).
        """
        x = int(player.x)
        base_y = int(player.y - player.radius - 30)
        tip_y = int(player.y - player.radius - 18)
        points = [(x - 7, base_y), (x + 7, base_y), (x, tip_y)]
        pygame.draw.polygon(self.screen, self.SELECT_MARKER_COLOR, points)
        pygame.draw.polygon(self.screen, (0, 0, 0), points, 1)  # outline
    
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
    
    @staticmethod
    def possession_percentages(team1, team2):
        """(team1 %, team2 %) of the time either team held the ball."""
        total = team1.possession_time + team2.possession_time
        if total <= 0:
            return 0, 0
        pct1 = round(team1.possession_time / total * 100)
        return pct1, 100 - pct1
    
    def draw_hud_stats(self, team1, team2):
        """Bottom HUD bar with possession % and shots for both teams."""
        bar_height = 34
        bar_y = self.height - bar_height
        pygame.draw.rect(self.screen, (0, 0, 0),
                         (0, bar_y, self.width, bar_height))
        
        pct1, pct2 = self.possession_percentages(team1, team2)
        possession_text = self.small_font.render(
            f"Possession  {team1.name} {pct1}% - {pct2}% {team2.name}",
            True, (255, 255, 255))
        self.screen.blit(possession_text, (10, bar_y + 8))
        
        shots_text = self.small_font.render(
            f"Shots  {team1.name} {team1.shots} - {team2.shots} {team2.name}",
            True, (255, 255, 255))
        self.screen.blit(shots_text,
                         (self.width - shots_text.get_width() - 10, bar_y + 8))