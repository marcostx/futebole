"""
Soccer Simulation - Main Entry Point
This script initializes and runs the soccer simulation game.
"""

import pygame
import sys

from src.game_engine import GameEngine
from src import input as game_input


def main():
    """Initialize and run the soccer simulation game."""
    pygame.init()
    game = GameEngine()
    clock = pygame.time.Clock()

    while True:
        # Drain the event queue once per frame; the same list feeds both the
        # system controls below and the gameplay input layer.
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # System controls (distinct from gameplay input).
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_SPACE:
                    game.toggle_pause()
                elif event.key == pygame.K_r:
                    game.reset_game()

        # Resolve this frame's human input (movement + actions) and hand it to
        # the engine for the human controller to consume. Harmless in all-AI
        # mode: nothing reads it when no team is human-controlled.
        game.set_player_input(
            game_input.read_input(pygame.key.get_pressed(), events))

        game.update()
        game.render()

        # Cap the frame rate (reuse one clock so it can measure frame time).
        clock.tick(60)


if __name__ == "__main__":
    main()
