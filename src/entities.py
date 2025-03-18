"""
Entities Module
Contains classes for game entities like players, ball, and teams.
"""

import pygame
import math

class Entity:
    """Base class for all game entities."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0  # Velocity x
        self.vy = 0  # Velocity y
    
    def distance_to(self, other):
        """Calculate Euclidean distance to another entity."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def move_towards(self, target_x, target_y, speed):
        """Move entity towards a target position at a given speed."""
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        
        if distance > 0:
            # Normalize and scale by speed
            self.vx = (dx / distance) * speed
            self.vy = (dy / distance) * speed
    
    def update(self, dt):
        """Update entity position based on velocity."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Apply friction
        self.vx *= 0.95
        self.vy *= 0.95
        
        # Set very small velocities to zero
        if abs(self.vx) < 0.1:
            self.vx = 0
        if abs(self.vy) < 0.1:
            self.vy = 0

class Ball(Entity):
    """Represents the soccer ball."""
    def __init__(self, x, y):
        super().__init__(x, y)
        self.radius = 5
        self.possession = None  # Which player has possession of the ball
    
    def kick(self, direction_x, direction_y, power):
        """Kick the ball in a given direction with specified power."""
        distance = math.sqrt(direction_x ** 2 + direction_y ** 2)
        
        if distance > 0:
            # Normalize and scale by power
            self.vx = (direction_x / distance) * power
            self.vy = (direction_y / distance) * power
        
        # Release possession
        self.possession = None

class Player(Entity):
    """Represents a soccer player."""
    def __init__(self, name, x, y, color):
        super().__init__(x, y)
        self.name = name
        self.color = color
        self.radius = 10
        self.max_speed = 100
        self.stamina = 100  # Max stamina
        self.current_stamina = 100
        self.shoot_power = 200
        self.pass_power = 150
        self.is_goalkeeper = False
        self.role = "field"  # field, defender, midfielder, striker
    
    def update(self, dt):
        """Update player position and attributes."""
        super().update(dt)
        
        # Recover stamina
        if self.current_stamina < self.stamina:
            self.current_stamina += 5 * dt  # Recover 5 stamina per second
            self.current_stamina = min(self.current_stamina, self.stamina)
    
    def shoot(self, ball, target_x, target_y):
        """Shoot the ball towards a target position."""
        # Check if the player has the ball
        if ball.possession == self:
            direction_x = target_x - ball.x
            direction_y = target_y - ball.y
            
            # Use stamina for shooting
            power_factor = min(1.0, self.current_stamina / 30)
            self.current_stamina = max(0, self.current_stamina - 30)
            
            # Kick the ball
            ball.kick(direction_x, direction_y, self.shoot_power * power_factor)
            return True
        return False
    
    def pass_ball(self, ball, target_player):
        """Pass the ball to a teammate."""
        # Check if the player has the ball
        if ball.possession == self:
            direction_x = target_player.x - ball.x
            direction_y = target_player.y - ball.y
            
            # Use stamina for passing
            power_factor = min(1.0, self.current_stamina / 20)
            self.current_stamina = max(0, self.current_stamina - 20)
            
            # Kick the ball
            ball.kick(direction_x, direction_y, self.pass_power * power_factor)
            return True
        return False
    
    def can_control_ball(self, ball):
        """Check if the player can control the ball."""
        return self.distance_to(ball) < self.radius + ball.radius + 5

class Team:
    """Represents a team of players."""
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.players = []
        self.score = 0
        self.formation = "4-4-2"  # Default formation
    
    def add_player(self, player):
        """Add a player to the team."""
        self.players.append(player)
    
    def nearest_player_to_ball(self, ball):
        """Find the nearest player to the ball."""
        nearest_player = None
        min_distance = float('inf')
        
        for player in self.players:
            distance = player.distance_to(ball)
            if distance < min_distance:
                min_distance = distance
                nearest_player = player
        
        return nearest_player
    
    def get_player_by_name(self, name):
        """Get a player by name."""
        for player in self.players:
            if player.name == name:
                return player
        return None