# Le Futebole


# Soccer Simulation Project

A 2D soccer simulation built with Python and Pygame. The interactive game is
human vs AI; the same engine also runs reproducible all-AI matches for
headless monitoring and experiments.

## Gameplay Preview

![Gameplay Animation](assets/match_improved_short.gif)


## Features

- 6v6 teams: five role-aware outfield players plus a goalkeeper
- Human-controlled Team 1 with AI teammates, against an autonomous Team 2
- Tactical AI for formations, defensive blocks, marking, rest defence,
  passing, shooting, support runs, and goalkeeping
- Timestep-aware movement, stamina, possession contests, and restarts
- Simple 2D graphical interface using Pygame
- Scoreboard, match timer, possession, shots, selection marker, and controls

## Documentation

Read the [technical documentation and simulation paper](https://marcostx.github.io/futebole/)
for the engine architecture, equations, rules, tactical model, human-control
fairness, and 220-match parameter sweep.

## Project Structure
```futebole/
├── README.md
├── book.toml
├── requirements.txt
├── main.py
├── monitor_match.py
├── experiments/       # Reproducible seeded parameter-sweep tools
├── paper/             # LaTeX source and curated figures
├── reports/           # mdBook source and development reports
├── src/
│   ├── game_engine.py
│   ├── entities.py
│   ├── ai.py
│   ├── human_controller.py
│   ├── input.py
│   └── ui.py
└── tests/
```

## Installation

Clone the repository:
```bash
git clone https://github.com/marcostx/futebole.git
cd futebole
```

Create a virtual environment:
```bash
python -m venv venv
```

Activate the virtual environment:

On macOS/Linux:
```bash
source venv/bin/activate
```

Install dependencies:
```bash
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

