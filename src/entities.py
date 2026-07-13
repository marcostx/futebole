"""
Entities Module
Contains classes for game entities like players, ball, and teams.
"""

import pygame
import math

# Minimum time (seconds) between a player's kick actions (shots/passes).
# Without this, the AI fires an action every frame, draining stamina to zero
# and reducing kick power to nothing.
ACTION_COOLDOWN = 0.5

# Floor for the stamina-based power factor so a tired player still kicks the
# ball with meaningful force instead of it barely moving. Power scales
# linearly with stamina between this floor (exhausted) and 1.0 (fresh).
# Kept mild: heavy fatigue penalties made matches slow and chanceless.
MIN_POWER_FACTOR = 0.8

# Gradual stamina effects on movement. A fully exhausted player still moves
# at this fraction of their pace (never immobile), scaling linearly up to
# full speed at full stamina. Mild on purpose (see MIN_POWER_FACTOR).
MIN_SPEED_FACTOR = 0.85
# Moving faster than this fraction of max_speed is sprinting and drains
# stamina (scaled by how hard the player is running); below the recovery
# threshold the player is resting and regains stamina. The slow drain keeps
# stamina flavor without dragging the match pace down.
SPRINT_THRESHOLD = 0.75
RECOVERY_THRESHOLD = 0.5
SPRINT_DRAIN_PER_SEC = 2.5
STAMINA_RECOVERY_PER_SEC = 5.0

# Stamina cost per kick. Small relative to running: fatigue should come
# from sprinting over a match, not from a handful of passes.
SHOT_STAMINA_COST = 10
PASS_STAMINA_COST = 5

# Fraction of the ball's velocity retained after one second of rolling.
# Applied in a frame-rate independent way so a kicked ball travels a realistic
# distance instead of stopping after ~60px (the old per-frame 0.95 friction).
BALL_FRICTION_PER_SEC = 0.05

# Seconds after a kick during which the ball is "in flight" and cannot be
# controlled by anyone. Lets shots reach the goal and passes reach a teammate
# instead of being recaptured on the very next frame.
LOOSE_BALL_TIME = 0.3

# Fraction of an entity's velocity retained after one second, applied in a
# frame-rate independent way. 0.046 ≈ the previous per-frame 0.95 at 60 fps
# (0.95 ** 60 ≈ 0.046), so behavior is unchanged at 60 fps but no longer
# depends on the frame rate.
ENTITY_FRICTION_PER_SEC = 0.046

# Maximum ball speed (px/s). Caps kicks/deflections so the ball never travels
# unrealistically fast (and tunnels through players/walls). Sized so a
# full-power long shot can still cover ~300px before rolling friction kills
# it (reach ~= speed / 3, from the rolling decay rate).
BALL_MAX_SPEED = 900

# Fraction of speed retained when the ball bounces off a wall (restitution).
BALL_RESTITUTION = 0.8

# Passes are powered to die near the receiver's feet: the rolling decay rate
# (derived from BALL_FRICTION_PER_SEC) converts pass distance into the kick
# speed needed to cover it, with a margin so the ball arrives with some pace.
# Bounded below so tap passes still zip, and above by the ball's max speed.
PASS_POWER_MARGIN = 1.1
PASS_POWER_MIN = 200

# Shots are powered by distance too, so long-range efforts actually reach
# the goal with pace instead of dying on the way (margin > passes: shots
# should arrive fast, not land at the keeper's feet).
SHOT_POWER_MARGIN = 1.25
MAX_SHOT_POWER = 900

# Acceleration: each movement command blends the velocity toward the
# desired vector instead of snapping to it, giving players momentum (they
# take a few frames to reach speed and to turn around). The constant is the
# blend fraction per 60Hz frame; commands scale it by their real dt so the
# effective acceleration is frame-rate independent.
MOVE_ACCEL_BLEND = 0.25
ACCEL_REFERENCE_FPS = 60.0


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
        
        # Apply friction, scaled by dt so it is frame-rate independent
        decay = ENTITY_FRICTION_PER_SEC ** dt
        self.vx *= decay
        self.vy *= decay
        
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
        self.loose_timer = 0.0  # Seconds the ball stays uncontrollable in flight
        # Last player to control the ball; kicks always come from the
        # possessor, so this attributes out-of-bounds exits (throw-in,
        # corner, goal kick) to the right team.
        self.last_toucher = None
    
    def cap_speed(self):
        """Clamp the ball's speed to BALL_MAX_SPEED."""
        speed = math.hypot(self.vx, self.vy)
        if speed > BALL_MAX_SPEED:
            scale = BALL_MAX_SPEED / speed
            self.vx *= scale
            self.vy *= scale
    
    def update(self, dt):
        """Roll the ball with frame-rate independent friction and a speed cap."""
        # Cap speed first so this frame's movement never exceeds the max
        self.cap_speed()
        
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Rolling friction scaled by dt so behavior is independent of frame rate
        decay = BALL_FRICTION_PER_SEC ** dt
        self.vx *= decay
        self.vy *= decay
        
        # Snap tiny velocities (px/s) to zero
        if abs(self.vx) < 1:
            self.vx = 0
        if abs(self.vy) < 1:
            self.vy = 0
        
        # Count down the in-flight window
        if self.loose_timer > 0:
            self.loose_timer = max(0.0, self.loose_timer - dt)
    
    def kick(self, direction_x, direction_y, power):
        """Kick the ball in a given direction with specified power."""
        distance = math.sqrt(direction_x ** 2 + direction_y ** 2)
        
        if distance > 0:
            # Normalize and scale by power
            self.vx = (direction_x / distance) * power
            self.vy = (direction_y / distance) * power
        
        # Release possession and mark the ball as in flight
        self.possession = None
        self.loose_timer = LOOSE_BALL_TIME

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
        self.shoot_power = 500
        self.is_goalkeeper = False
        self.role = "field"  # field, defender, midfielder, striker
        # Home/base position for this player's role in the team formation.
        # Off-ball players hold their shape relative to this point.
        self.home_x = x
        self.home_y = y
        # Direction the player is facing; used to place a dribbled ball
        # just ahead of the player. Defaults to pointing right.
        self.facing_x = 1.0
        self.facing_y = 0.0
        # Time (seconds) until this player may kick again.
        self.action_cooldown = 0.0
    
    def update(self, dt):
        """Update player position and attributes."""
        # This frame's effort is the velocity that actually moves the player
        # below; capture it before Entity.update applies friction, otherwise
        # sprint drain is undercounted (and frame-rate dependent, since
        # larger dt decays the measured speed further).
        effort_vx, effort_vy = self.vx, self.vy
        speed = math.hypot(effort_vx, effort_vy)
        
        super().update(dt)
        
        # Update facing direction from current movement
        if speed > 1:
            self.facing_x = effort_vx / speed
            self.facing_y = effort_vy / speed
        
        # Tick down the action cooldown
        if self.action_cooldown > 0:
            self.action_cooldown = max(0.0, self.action_cooldown - dt)
        
        # Stamina: sprinting drains it (scaled by effort), resting recovers
        # it, jogging in between is sustainable. Self-stabilizing: a tired
        # player is slower (see speed_factor), which drops them back under
        # the sprint threshold instead of draining to zero.
        speed_ratio = speed / self.max_speed
        if speed_ratio > SPRINT_THRESHOLD:
            self.current_stamina = max(
                0.0, self.current_stamina - SPRINT_DRAIN_PER_SEC * speed_ratio * dt)
        elif speed_ratio < RECOVERY_THRESHOLD:
            self.current_stamina = min(
                self.stamina,
                self.current_stamina + STAMINA_RECOVERY_PER_SEC * dt)
    
    def can_act(self):
        """Whether the player is off cooldown and may shoot or pass."""
        return self.action_cooldown <= 0
    
    def stamina_factor(self):
        """0..1 fitness scale: 1.0 fresh, dropping linearly as stamina drains."""
        return max(0.0, min(1.0, self.current_stamina / self.stamina))
    
    def speed_factor(self):
        """Gradual speed multiplier: full pace fresh, MIN_SPEED_FACTOR exhausted."""
        return MIN_SPEED_FACTOR + (1.0 - MIN_SPEED_FACTOR) * self.stamina_factor()
    
    def power_factor(self):
        """Gradual kick-power multiplier: 1.0 fresh, MIN_POWER_FACTOR exhausted."""
        return MIN_POWER_FACTOR + (1.0 - MIN_POWER_FACTOR) * self.stamina_factor()
    
    def move_towards(self, target_x, target_y, speed, dt=1.0 / 60):
        """Accelerate toward a target at the requested speed, scaled by fatigue.
        
        Movement has momentum: each command blends the velocity a fraction
        of the way toward the desired vector (the AI re-issues commands
        every frame, so repeated calls converge on full speed) instead of
        snapping, so starts, stops and turns take a few frames. The blend
        is scaled by `dt` so acceleration is frame-rate independent.
        """
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)
        if distance == 0:
            return
        effective = speed * self.speed_factor()
        desired_vx = (dx / distance) * effective
        desired_vy = (dy / distance) * effective
        alpha = 1.0 - (1.0 - MOVE_ACCEL_BLEND) ** (dt * ACCEL_REFERENCE_FPS)
        self.vx += (desired_vx - self.vx) * alpha
        self.vy += (desired_vy - self.vy) * alpha
    
    def carry_ball(self, ball):
        """Keep the ball glued just ahead of this player while dribbling.
        
        Called every frame while the player has possession so the ball
        travels with the carrier instead of being left behind.
        """
        if ball.possession is not self:
            return
        offset = self.radius + ball.radius
        ball.x = self.x + self.facing_x * offset
        ball.y = self.y + self.facing_y * offset
        # Match the ball's velocity to the carrier's so a subsequent
        # release/kick starts from a sensible motion state.
        ball.vx = self.vx
        ball.vy = self.vy
    
    def shoot(self, ball, target_x, target_y):
        """Shoot the ball towards a target position.
        
        Power scales with the distance to the target (bounded by
        MAX_SHOT_POWER) so long-range efforts arrive at the goal with pace
        instead of dying short; close shots keep the base shoot_power zip.
        """
        # Must have the ball and be off cooldown
        if ball.possession == self and self.can_act():
            direction_x = target_x - ball.x
            direction_y = target_y - ball.y
            
            shot_dist = math.hypot(direction_x, direction_y)
            decay_rate = -math.log(BALL_FRICTION_PER_SEC)
            power = max(self.shoot_power,
                        min(shot_dist * decay_rate * SHOT_POWER_MARGIN,
                            MAX_SHOT_POWER))
            
            # Kick power degrades gradually with fatigue (floored, never zero)
            power_factor = self.power_factor()
            self.current_stamina = max(0, self.current_stamina - SHOT_STAMINA_COST)
            
            # Kick the ball
            ball.kick(direction_x, direction_y, power * power_factor)
            self.action_cooldown = ACTION_COOLDOWN
            return True
        return False
    
    def pass_ball(self, ball, target_player):
        """Pass the ball to a teammate, turning to face them first."""
        # Must have the ball and be off cooldown
        if ball.possession == self and self.can_act():
            to_target_x = target_player.x - self.x
            to_target_y = target_player.y - self.y
            pass_dist = math.hypot(to_target_x, to_target_y)
            if pass_dist == 0:
                # Degenerate zero-distance pass: refuse it rather than
                # kicking with no direction, which would drop the ball loose.
                return False
            
            # Quick direction switch: turn toward the receiver and bring the
            # carried ball to that side, so the carrier can play the ball
            # backward/sideways naturally while dribbling another way.
            self.facing_x = to_target_x / pass_dist
            self.facing_y = to_target_y / pass_dist
            self.carry_ball(ball)
            
            # Size the kick to the pass distance so the ball dies near the
            # receiver's feet: short passes stay soft, long balls are driven.
            decay_rate = -math.log(BALL_FRICTION_PER_SEC)
            power = max(PASS_POWER_MIN,
                        min(pass_dist * decay_rate * PASS_POWER_MARGIN,
                            BALL_MAX_SPEED))
            
            # Kick power degrades gradually with fatigue (floored, never zero)
            power_factor = self.power_factor()
            self.current_stamina = max(0, self.current_stamina - PASS_STAMINA_COST)
            
            # Kick along the carrier->receiver direction. Using the ball's
            # own position instead could flip the direction for a receiver
            # closer than the carry offset (the repositioned ball would sit
            # just past them).
            ball.kick(to_target_x, to_target_y, power * power_factor)
            self.action_cooldown = ACTION_COOLDOWN
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
        # Match statistics (shown on the HUD).
        self.shots = 0
        self.possession_time = 0.0  # seconds in possession
    
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