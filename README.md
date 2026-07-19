# Le Futebole


# Soccer Simulation Project

A simple 2D soccer simulation game built with Python and Pygame where two AI-controlled teams compete against each other.

## Gameplay Preview

![Gameplay Animation](assets/match_improved_short.gif)


## Features

- Two AI-controlled teams with 3-5 players each
- Basic AI decision-making: moving towards the ball, passing, shooting
- Simple 2D graphical interface using Pygame
- Scoreboard and match timer
- Human vs AI: Team 1 is keyboard-controlled, Team 2 is AI (see Controls)

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
```
python main.py
```

## Controls

Team 1 (red) is human-controlled; Team 2 (blue) is AI. You control one player
at a time, marked by a cyan chevron above their head. A compact legend of these
controls is also shown on-screen while you play.

**Gameplay**

- Move: `W` `A` `S` `D` or the arrow keys
- Sprint: hold `Shift` (drains stamina faster)
- Pass: `J` (toward a teammate in the direction you are facing/moving)
- Shoot: `K` (aims for the corner away from the keeper)
- Switch player while defending: `Tab` (cycles to the next-closest player)

While your team has the ball you control the ball carrier; while defending the
game auto-selects the player nearest the ball (press `Tab` to switch).

**System**

- `Space`: Pause / resume
- `R`: Reset the match
- `Esc`: Quit

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

