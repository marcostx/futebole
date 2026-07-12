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

# A passing lane is considered blocked if an opponent is within this distance
# (px) of the carrier->receiver segment.
LANE_BLOCK_RADIUS = 25

# Opponents whose projection onto the lane falls before this fraction of the
# segment are ignored by the lane check: they are beside the carrier (that is
# the "pressure" situation, handled separately), not actually in the lane.
LANE_START_T = 0.15

# An unpressured carrier only passes when the receiver is at least this much
# (px) more open than the carrier — i.e. the pass clearly improves the
# team's position rather than cycling the ball for its own sake.
OPEN_ADVANTAGE = 5

# Field geometry (matches GameEngine: 800x600 screen, 50px margins).
FIELD_CENTER_X = 400
FIELD_CENTER_Y = 300
FIELD_MIN_X, FIELD_MAX_X = 50, 750
FIELD_MIN_Y, FIELD_MAX_Y = 50, 550

# Dribble targets stay at least this far (px) inside the field so a carrier
# near a boundary cuts back into play instead of conducting the carried ball
# (glued ~15px ahead of them) over the line, conceding a restart.
DRIBBLE_MARGIN = 25

# Man-marking. When the opposing attack gets this close (px) to our goal
# center, off-ball defenders mark nearby opponents instead of dropping with
# the formation (which used to park them on their own goal line).
MARK_ZONE_DIST = 300
# Only opponents this close (px) to our goal are worth marking.
MARK_TARGET_RANGE = 320
# A marker stands this far (px) from its man, on the goal side.
MARK_DIST = 22

# Formation/support targets stay this far (px) inside the field so off-ball
# players hold shape near a boundary instead of being clamped onto the line
# (the attack push / defense drop used to pile them on the goal lines).
FORMATION_MARGIN = 35

# Goal mouth extents, derived from the field bounds exactly like
# GameEngine.goal_mouth (30%-70% of field height).
GOAL_MOUTH_TOP = FIELD_MIN_Y + (FIELD_MAX_Y - FIELD_MIN_Y) * 0.3
GOAL_MOUTH_BOTTOM = FIELD_MIN_Y + (FIELD_MAX_Y - FIELD_MIN_Y) * 0.7

# Goalkeeper tuning. The keeper rushes a ball this close (px) to its own goal
# center when the ball is loose or held by an opponent; otherwise it holds
# its line, tracking the ball's height within the goal mouth.
GK_RUSH_DIST = 100
# Vertical margin (px) the keeper keeps inside the posts while tracking.
GK_MOUTH_MARGIN = 10
# How far upfield (px) the keeper boots a clearance when no pass is open.
GK_CLEAR_DIST = 350

# Shooting. Corner shots aim this far (px) inside the posts.
SHOT_CORNER_MARGIN = 15
# Minimum angular width (rad) the goal mouth must subtend from the shooter
# for a shot to be worth taking (~20°); tighter angles are passed up in
# favor of a pass or of dribbling toward the center to open the angle.
MIN_SHOT_ANGLE = 0.35
# Aim noise (px on the target y): base spread at point blank, growing by the
# scale term at maximum shooting range, so long shots are less precise.
SHOT_NOISE_BASE = 5
SHOT_NOISE_SCALE = 15
# Shots aim this far (px) beyond the goal line so the kick always has a
# forward component: a target exactly on the line degenerates into a
# vertical (unscoreable) kick when the ball sits on the line itself.
SHOT_DEPTH = 10


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
        # centrally by the engine. The goalkeeper never presses or supports:
        # it has its own dedicated behavior below.
        if self.team_state == "attack":
            # We have the ball: the carrier acts, the nearest teammate supports.
            self.active_player = self.ball.possession
            others = [p for p in self.team.players
                      if p is not self.active_player and not p.is_goalkeeper]
            self.support_player = (min(others, key=lambda p: p.distance_to(self.ball))
                                   if others else None)
        else:
            # We don't have the ball: our nearest outfield player presses it.
            self.active_player = self._nearest_outfield_to_ball(self.team)
            self.support_player = None
        
        # Execute behaviors based on team state
        if self.team_state == "defense":
            self.execute_defense_behavior(dt)
        elif self.team_state == "possession":
            self.execute_possession_behavior(dt)
        else:  # attack
            self.execute_attack_behavior(dt)
        
        # The goalkeeper's dedicated behavior overrides whatever formation
        # movement the state behaviors assigned to it.
        keeper = self._goalkeeper()
        if keeper is not None:
            self._update_goalkeeper(keeper, dt)
    
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
        
        target_x = max(FIELD_MIN_X + FORMATION_MARGIN,
                       min(player.home_x + shift_x, FIELD_MAX_X - FORMATION_MARGIN))
        target_y = max(FIELD_MIN_Y + FORMATION_MARGIN,
                       min(player.home_y + shift_y, FIELD_MAX_Y - FORMATION_MARGIN))
        return target_x, target_y
    
    def _nearest_outfield_to_ball(self, team):
        """The team's outfield player nearest the ball (keeper as a last resort)."""
        candidates = [p for p in team.players if not p.is_goalkeeper] or team.players
        return (min(candidates, key=lambda p: p.distance_to(self.ball))
                if candidates else None)
    
    def update_team_state(self):
        """Update the team's strategic state."""
        # Check if the ball is possessed by any player
        if self.ball.possession is None:
            # Ball is free: compare the players who would actually chase it
            # (nearest outfielder on each side; keepers only rush balls near
            # their own goal, independently of the team state).
            our_nearest = self._nearest_outfield_to_ball(self.team)
            their_nearest = self._nearest_outfield_to_ball(self.opponent_team)
            
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
    
    def _mark_assignments(self):
        """Pair off-ball defenders with opponents to mark, nearest first.
        
        Markers are our outfield players except the presser; targets are
        opponent outfielders near our goal, except their ball carrier (the
        presser handles them). Greedy nearest-pair matching, one marker per
        target, so two defenders never mark the same man.
        """
        own_goal_x, own_goal_y = self._own_goal_center()
        markers = [p for p in self.team.players
                   if p is not self.active_player and not p.is_goalkeeper]
        targets = [o for o in self.opponent_team.players
                   if o is not self.ball.possession and not o.is_goalkeeper
                   and math.hypot(o.x - own_goal_x,
                                  o.y - own_goal_y) < MARK_TARGET_RANGE]
        
        pairs = sorted(((m.distance_to(t), m, t)
                        for m in markers for t in targets),
                       key=lambda pair: pair[0])
        assignments = {}
        taken = set()
        for _, marker, target in pairs:
            if marker in assignments or target in taken:
                continue
            assignments[marker] = target
            taken.add(target)
        return assignments
    
    def _mark_position(self, opponent):
        """Point MARK_DIST goal-side of the opponent (between them and our goal)."""
        own_goal_x, own_goal_y = self._own_goal_center()
        dx = own_goal_x - opponent.x
        dy = own_goal_y - opponent.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return opponent.x, opponent.y
        return (opponent.x + dx / dist * MARK_DIST,
                opponent.y + dy / dist * MARK_DIST)
    
    def _goal_side_of_ball(self, player):
        """Whether the player is between the ball and our own goal."""
        return (player.x - self.ball.x) * self.field_side < 0
    
    def execute_defense_behavior(self, dt):
        """Execute defensive behavior for the team."""
        # Active player chases the ball. Gaining possession is resolved
        # centrally by the game engine (see GameEngine.resolve_possession)
        # so it is a fair, order-independent contest.
        if self.active_player:
            self.active_player.move_towards(self.ball.x, self.ball.y, 
                                           self.active_player.max_speed)
        
        # Attack near our goal: off-ball defenders man-mark opponents on the
        # goal side instead of dropping with the formation until the field
        # clamp piles them onto their own goal line.
        own_goal_x, own_goal_y = self._own_goal_center()
        threat = (math.hypot(self.ball.x - own_goal_x,
                             self.ball.y - own_goal_y) < MARK_ZONE_DIST)
        assignments = self._mark_assignments() if threat else {}
        
        for player in self.team.players:
            if player is self.active_player:
                continue
            mark = assignments.get(player)
            if mark is not None:
                mark_x, mark_y = self._mark_position(mark)
                player.move_towards(mark_x, mark_y, player.max_speed * 0.85)
            elif threat and not player.is_goalkeeper and self._goal_side_of_ball(player):
                # Free defender loitering behind the ball with nobody to
                # mark: converge on the carrier to help win the ball instead
                # of standing on the goal line like an extra goalkeeper.
                player.move_towards(self.ball.x, self.ball.y,
                                    player.max_speed * 0.9)
            else:
                # Everyone else holds the formation shape (slid to the ball).
                target_x, target_y = self.formation_position(player)
                player.move_towards(target_x, target_y, player.max_speed * 0.7)
    
    def execute_possession_behavior(self, dt):
        """Chase a loose ball we're closest to: one presser, others hold shape."""
        # Active player goes for the ball. Gaining possession is resolved
        # centrally by the game engine (see GameEngine.resolve_possession).
        if self.active_player:
            self.active_player.move_towards(self.ball.x, self.ball.y, 
                                           self.active_player.max_speed)
        
        # Other players hold their formation shape (slid toward the ball)
        for player in self.team.players:
            if player != self.active_player:
                target_x, target_y = self.formation_position(player)
                player.move_towards(target_x, target_y, player.max_speed * 0.6)
    
    def _goalkeeper(self):
        """This team's goalkeeper, or None if the roster has none."""
        for p in self.team.players:
            if p.is_goalkeeper:
                return p
        return None
    
    def _own_goal_center(self):
        """(x, y) of the center of this team's own goal mouth."""
        own_goal_x = FIELD_MIN_X if self.field_side == 1 else FIELD_MAX_X
        return own_goal_x, FIELD_CENTER_Y
    
    def _update_goalkeeper(self, keeper, dt):
        """Dedicated goalkeeper behavior: distribute, rush threats, hold the line.
        
        Runs after the team-state behaviors and overrides whatever formation
        movement they assigned to the keeper.
        """
        if self.ball.possession is keeper:
            self._goalkeeper_distribute(keeper)
            return
        
        # Rush a ball that is close to our goal and not safely ours (loose or
        # held by an opponent), to smother the threat.
        own_goal_x, own_goal_y = self._own_goal_center()
        ball_is_ours = self.ball.possession in self.team.players
        threat_dist = math.hypot(self.ball.x - own_goal_x, self.ball.y - own_goal_y)
        if not ball_is_ours and threat_dist < GK_RUSH_DIST:
            keeper.move_towards(self.ball.x, self.ball.y, keeper.max_speed)
            return
        
        # Otherwise hold the goal line: stay at the home x (just off the line)
        # and track the ball's height, clamped inside the goal mouth.
        target_y = max(GOAL_MOUTH_TOP + GK_MOUTH_MARGIN,
                       min(self.ball.y, GOAL_MOUTH_BOTTOM - GK_MOUTH_MARGIN))
        keeper.move_towards(keeper.home_x, target_y, keeper.max_speed * 0.9)
    
    def _goalkeeper_distribute(self, keeper):
        """With the ball: pass to an open teammate, else boot it upfield."""
        if not keeper.can_act():
            # On cooldown: stand still instead of dribbling out of the box.
            keeper.vx = keeper.vy = 0
            return
        target = self._best_pass_target(keeper)
        if target is not None:
            keeper.pass_ball(self.ball, target)
            return
        # No open short option: clear long toward the halfway line.
        clear_x = keeper.x + GK_CLEAR_DIST * self.field_side
        keeper.shoot(self.ball, clear_x, FIELD_CENTER_Y)
    
    def _opponent_goal_x(self):
        """X of the goal line this team attacks."""
        return FIELD_MAX_X if self.field_side == 1 else FIELD_MIN_X
    
    def _shot_angle(self, shooter):
        """Angular width (rad) of the opponent goal mouth seen from the shooter.
        
        Wide in front of the goal, narrow from sharp positions near the goal
        line — a direct measure of how much of the goal is available.
        """
        goal_x = self._opponent_goal_x()
        angle_top = math.atan2(GOAL_MOUTH_TOP - shooter.y, goal_x - shooter.x)
        angle_bottom = math.atan2(GOAL_MOUTH_BOTTOM - shooter.y, goal_x - shooter.x)
        return abs(angle_bottom - angle_top)
    
    def _goal_blocker(self):
        """The opponent nearest the center of the goal we attack.
        
        In practice their goalkeeper, but falls back to any covering defender
        (or None) so corner picking works against keeper-less rosters too.
        """
        goal_x = self._opponent_goal_x()
        return min(self.opponent_team.players,
                   key=lambda o: math.hypot(o.x - goal_x, o.y - FIELD_CENTER_Y),
                   default=None)
    
    def _pick_shot_target(self, shooter):
        """(x, y) to shoot at: just inside the corner away from the keeper.
        
        Picks the corner of the goal mouth farther from the blocking opponent
        (their keeper); with no defenders it takes the near corner (shortest
        travel). Aim noise on y grows with distance, so close shots are
        precise and long ones can drift wide.
        """
        goal_x = self._opponent_goal_x()
        corners = (GOAL_MOUTH_TOP + SHOT_CORNER_MARGIN,
                   GOAL_MOUTH_BOTTOM - SHOT_CORNER_MARGIN)
        
        blocker = self._goal_blocker()
        if blocker is not None:
            target_y = max(corners,
                           key=lambda cy: math.hypot(goal_x - blocker.x,
                                                     cy - blocker.y))
        else:
            target_y = min(corners, key=lambda cy: abs(cy - shooter.y))
        
        dist = math.hypot(goal_x - shooter.x, target_y - shooter.y)
        noise = SHOT_NOISE_BASE + SHOT_NOISE_SCALE * min(1.0, dist / SHOOT_RANGE)
        # Aim past the goal line so the shot always drives into the net.
        target_x = goal_x + SHOT_DEPTH * self.field_side
        return target_x, target_y + random.uniform(-noise, noise)
    
    def _second_last_opponent_x(self):
        """X of the opponents' second-last player (the offside line).
        
        The last defender is usually their goalkeeper, so the second-last
        marks the effective defensive line, as in the real offside rule.
        Returns None with fewer than two opponents (no offside possible).
        """
        xs = sorted((o.x for o in self.opponent_team.players),
                    reverse=self.field_side == 1)
        return xs[1] if len(xs) >= 2 else None
    
    def _is_offside_position(self, player):
        """Simplified offside: in the opponent half, ahead of the ball, and
        ahead of the opponents' second-last player."""
        if (player.x - FIELD_CENTER_X) * self.field_side <= 0:
            return False  # own half: never offside
        if (player.x - self.ball.x) * self.field_side <= 0:
            return False  # level with or behind the ball
        line_x = self._second_last_opponent_x()
        if line_x is None:
            return False
        return (player.x - line_x) * self.field_side > 0
    
    def _openness(self, player):
        """Distance (px) from a player to the nearest opponent."""
        return min((player.distance_to(o) for o in self.opponent_team.players),
                   default=1e9)
    
    def _lane_is_open(self, carrier, receiver):
        """Whether the straight pass lane carrier->receiver is free of opponents.
        
        An opponent blocks the lane if it is within LANE_BLOCK_RADIUS of the
        segment. Opponents projecting onto the very start of the segment are
        ignored: an opponent beside the carrier is the "pressure" situation,
        which is handled by the offload logic, not a blocked lane.
        """
        seg_x = receiver.x - carrier.x
        seg_y = receiver.y - carrier.y
        seg_len_sq = seg_x ** 2 + seg_y ** 2
        if seg_len_sq == 0:
            return True
        
        for opp in self.opponent_team.players:
            # Projection parameter of the opponent onto the segment, in [0, 1]
            t = ((opp.x - carrier.x) * seg_x + (opp.y - carrier.y) * seg_y) / seg_len_sq
            if t < LANE_START_T or t > 1:
                continue
            closest_x = carrier.x + t * seg_x
            closest_y = carrier.y + t * seg_y
            if math.hypot(opp.x - closest_x, opp.y - closest_y) < LANE_BLOCK_RADIUS:
                return False
        return True
    
    def _pass_candidates(self, carrier, forward):
        """Open-laned, reachable, onside teammates ahead of (or behind) the carrier."""
        candidates = []
        for p in self.team.players:
            if p is carrier or carrier.distance_to(p) > MAX_PASS_DIST:
                continue
            # Split forward options (closer to the opponent goal than the
            # carrier) from backward/lateral ones.
            is_forward = (p.x - carrier.x) * self.field_side > 0
            if is_forward != forward:
                continue
            # Never pass to a teammate in an offside position.
            if self._is_offside_position(p):
                continue
            # Only options whose passing lane isn't blocked by an opponent.
            if not self._lane_is_open(carrier, p):
                continue
            candidates.append(p)
        return candidates
    
    def _best_pass_target(self, carrier, allow_backward=False):
        """Pick the best open-laned, reachable teammate to pass to.
        
        Forward options (toward the opponent goal) are always preferred so
        passes make progress. With `allow_backward` (used when the carrier
        is under pressure and needs an outlet), nobody open in front falls
        back to a backward/lateral pass to recycle possession instead of
        dribbling into the presser. Returns None if no lane is open.
        """
        opponent_goal_x = FIELD_MAX_X if self.field_side == 1 else FIELD_MIN_X
        candidates = self._pass_candidates(carrier, forward=True)
        if not candidates and allow_backward:
            candidates = self._pass_candidates(carrier, forward=False)
        if not candidates:
            return None
        
        def score(p):
            # Openness: distance to the nearest opponent (bigger is better).
            openness = self._openness(p)
            # Prefer teammates closer to the opponent goal.
            forwardness = -abs(opponent_goal_x - p.x)
            return openness + 0.5 * forwardness
        
        return max(candidates, key=score)
    
    def execute_attack_behavior(self, dt):
        """Execute attacking behavior for the team."""
        # Get the player with the ball
        ball_carrier = self.ball.possession
        
        # A keeper with the ball distributes via its dedicated behavior
        # (_goalkeeper_distribute), not the outfield carrier logic.
        if ball_carrier in self.team.players and not ball_carrier.is_goalkeeper:
            # We have the ball, decide what to do
            opponent_goal_x = FIELD_MAX_X if self.field_side == 1 else FIELD_MIN_X
            opponent_goal_y = FIELD_CENTER_Y
            
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
            in_shot_range = distance_to_goal < SHOOT_RANGE
            good_angle = self._shot_angle(ball_carrier) >= MIN_SHOT_ANGLE
            acted = False
            if ball_carrier.can_act():
                if in_shot_range and good_angle:
                    # Enough of the goal is visible: shoot at the corner away
                    # from the keeper, with distance-scaled aim noise.
                    target_x, target_y = self._pick_shot_target(ball_carrier)
                    acted = ball_carrier.shoot(self.ball, target_x, target_y)
                elif under_pressure:
                    # Opponent too close: offload to a teammate to escape the
                    # press instead of dribbling into them (and losing the ball
                    # in a tug-of-war loop). A backward outlet is allowed when
                    # nobody is open in front.
                    target = self._best_pass_target(ball_carrier,
                                                    allow_backward=True)
                    if target is not None:
                        acted = ball_carrier.pass_ball(self.ball, target)
                else:
                    # Build-up: pass only when it clearly improves the team's
                    # position — the receiver must be meaningfully more open
                    # than the carrier (lane and range already vetted).
                    target = self._best_pass_target(ball_carrier)
                    if (target is not None and
                            self._openness(target) >
                            self._openness(ball_carrier) + OPEN_ADVANTAGE):
                        acted = ball_carrier.pass_ball(self.ball, target)
            
            if not acted:
                # No kick this frame (out of range/cooldown/tight angle, or
                # pressured with no reachable pass): dribble towards the goal,
                # steering around a close opponent.
                target_x = ball_carrier.x + 20 * self.field_side
                target_y = ball_carrier.y
                if in_shot_range and not good_angle:
                    # Sharp position by the goal line: cut toward the middle
                    # of the goal mouth to open the shooting angle instead of
                    # driving into the corner.
                    dy = opponent_goal_y - ball_carrier.y
                    target_y += max(-20.0, min(20.0, dy))
                if (nearest_opponent and
                        ball_carrier.distance_to(nearest_opponent) < PRESSURE_DIST):
                    target_y += -20 if ball_carrier.y < nearest_opponent.y else 20
                
                # Keep the dribble target inside the field so a carrier near
                # a boundary cuts back into play instead of conducting the
                # ball out (which concedes a restart to the other team).
                target_x = max(FIELD_MIN_X + DRIBBLE_MARGIN,
                               min(target_x, FIELD_MAX_X - DRIBBLE_MARGIN))
                target_y = max(FIELD_MIN_Y + DRIBBLE_MARGIN,
                               min(target_y, FIELD_MAX_Y - DRIBBLE_MARGIN))
                
                ball_carrier.move_towards(target_x, target_y, ball_carrier.max_speed * 0.8)
        
        # The nearest teammate offers a short forward passing option (within
        # passing range so the ball can advance); the rest hold formation shape.
        for player in self.team.players:
            if player is ball_carrier:
                continue
            if player is self.support_player:
                sx = max(FIELD_MIN_X + FORMATION_MARGIN,
                         min(ball_carrier.x + 60 * self.field_side,
                             FIELD_MAX_X - FORMATION_MARGIN))
                sy = max(FIELD_MIN_Y + FORMATION_MARGIN,
                         min(ball_carrier.y, FIELD_MAX_Y - FORMATION_MARGIN))
                player.move_towards(sx, sy, player.max_speed * 0.9)
            else:
                target_x, target_y = self.formation_position(player)
                player.move_towards(target_x, target_y, player.max_speed * 0.7)
