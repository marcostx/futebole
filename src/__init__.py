"""
Soccer Simulation Package
A simple 2D soccer simulation game with AI-controlled teams.
"""

# Import core modules to make them available when importing the package
from src.game_engine import GameEngine
from src.entities import Ball, Player, Team
from src.ai import AIController
from src.ui import UI
from src.utils import (
    get_distance, get_angle, get_point_in_circle, 
    is_point_in_rect, normalize_vector, limit_magnitude,
    vector_dot_product, vector_reflection, add_noise
)

__version__ = '0.1.0'
__author__ = 'Soccer Simulation Team'