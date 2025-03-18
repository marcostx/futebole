"""
Utils Module
Contains utility functions for the soccer game.
"""

import math
import random

def get_distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def get_angle(x1, y1, x2, y2):
    """Calculate angle between two points in radians."""
    return math.atan2(y2 - y1, x2 - x1)

def get_point_in_circle(center_x, center_y, radius):
    """Get a random point inside a circle."""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius)
    x = center_x + distance * math.cos(angle)
    y = center_y + distance * math.sin(angle)
    return x, y

def is_point_in_rect(x, y, rect_x, rect_y, rect_width, rect_height):
    """Check if a point is inside a rectangle."""
    return (rect_x <= x <= rect_x + rect_width and 
            rect_y <= y <= rect_y + rect_height)

def normalize_vector(x, y):
    """Normalize a vector to have length 1."""
    length = math.sqrt(x * x + y * y)
    if length > 0:
        return x / length, y / length
    return 0, 0

def limit_magnitude(x, y, max_magnitude):
    """Limit the magnitude of a vector."""
    magnitude = math.sqrt(x * x + y * y)
    if magnitude > max_magnitude and magnitude > 0:
        factor = max_magnitude / magnitude
        return x * factor, y * factor
    return x, y

def vector_dot_product(x1, y1, x2, y2):
    """Calculate dot product of two vectors."""
    return x1 * x2 + y1 * y2

def vector_reflection(incident_x, incident_y, normal_x, normal_y):
    """Calculate reflection vector when bouncing off a surface."""
    # Normalize the normal vector
    norm_x, norm_y = normalize_vector(normal_x, normal_y)
    
    # Calculate dot product
    dot = vector_dot_product(incident_x, incident_y, norm_x, norm_y)
    
    # Calculate reflection vector: r = i - 2(i·n)n
    reflection_x = incident_x - 2 * dot * norm_x
    reflection_y = incident_y - 2 * dot * norm_y
    
    return reflection_x, reflection_y

def add_noise(value, noise_amount):
    """Add random noise to a value."""
    return value + random.uniform(-noise_amount, noise_amount)