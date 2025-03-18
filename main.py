"""
Soccer Simulation - Main Entry Point
This script initializes and runs the soccer simulation game.
"""

import pygame
import sys
from src.game_engine import GameEngine

def main():
    """
    Main function to initialize and run the soccer simulation game.
    """
    # Initialize pygame
    pygame.init()
    
    # Create game engine instance
    game = GameEngine()
    
    # Main game loop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Handle key presses
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_SPACE:
                    game.toggle_pause()
                elif event.key == pygame.K_r:
                    game.reset_game()
        
        # Update game state
        game.update()
        
        # Render game
        game.render()
        
        # Cap the frame rate
        pygame.time.Clock().tick(60)

if __name__ == "__main__":
    main()