# Le Futebole


# Soccer Simulation Project

A simple 2D soccer simulation game built with Python and Pygame where two AI-controlled teams compete against each other.

## Gameplay Preview

![Gameplay Animation](assets/match.gif)


## Features

- Two AI-controlled teams with 3-5 players each
- Basic AI decision-making: moving towards the ball, passing, shooting
- Simple 2D graphical interface using Pygame
- Scoreboard and match timer
- Autonomous gameplay without human intervention

## Project Structure
```futebole/
├── README.md
├── requirements.txt
├── main.py
├── assets/
│   ├── field.png
│   └── ball.png
└── src/
    ├── __init__.py
    ├── game_engine.py
    ├── entities.py
    ├── ai.py
    ├── ui.py
    └── utils.py
```

Installation

Clone the repository:
git clone https://github.com/yourusername/soccer-simulation.git
cd soccer-simulation

# Create a virtual environment:
```
python -m venv venv
```

Activate the virtual environment:

On macOS/Linux:
```
source venv/bin/activate
```

Install dependencies:
```
pip install -r requirements.txt
```

## Running the Game
To start the simulation:
python main.py
Game Controls

ESC: Exit the game
SPACE: Pause/Resume the game
R: Reset the match

## AI Improvements

Implement more sophisticated team formations
Add player roles (defender, midfielder, striker)
Incorporate machine learning for improved decision-making
Add strategy adjustments based on game score

## Visual Enhancements

Add player animations
Implement more detailed field graphics
Add visual effects for goals, passes, and other events
Create a replay system for goals

## Game Mechanics

Add game physics (ball bouncing, player collisions)
Implement weather effects that impact gameplay
Add referee and fouls system
Create a tournament mode with multiple matches

