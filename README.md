# FFXIV Syraxius Bot
Experimental bot for Final Fantasy XIV. Still largely WIP.

Feel free to raise any suggestions, ideas or bugs.

# Disclaimer:
- This software is for educational purposes only.
- Hacking is illegal and it violates FFXIV's terms of use.
- I am not responsible for any consequence resulting from the use of this software.

# Installation (for Windows):
- Clone this repository (or download this repository and extract it somewhere).
- Install Python 3.9 from https://www.python.org/.
- Create a Python 3.9 virtual environment in this folder using `python3 -m venv venv`.
- Activate your virtual environment using `cd venv/Scripts && activate`.
- Install requirements listed in requirements.txt using `pip install -r requirements.txt`.
- (Personally, I just use PyCharm IDE for all these).

# Features

- Combat automation engine
  - Assist
    - Memory-reading and state-machine based combat automation.
    - Black Mage automatic optimal fire / blizzard combo + buffs (other classes combo still WIP).
    - Automatically chooses skills and combos based on current level (adapts to level sync too).
    - Achieve the highest possible DPS with available skills.
    - Asynchronous non-blocking implementation.
    - Detect cast failures and readapt (due to line of sight, interruption, out of range, etc.).
    - Fast skill cancellation and target switching.
- Gameplay automation engine
  - Dungeon
    - Memory-reading and state-machine based gameplay automation.
    - Progress through dungeon at the team's pace without running ahead.
    - Human-like movement and fighting.
    - Automatically engage only aggro'ed monsters.
    - Automatically accept duty.
    - Automatically skip cutscenes.
- Navigation engine
  - Human-like in-game character control - behave and move exactly like a controller player.
  - Real-time simultaneous localization and mapping (SLAM) - learns topology of maps without any prior hardcoding or waypoints recording.
  - Fast stuck detection and resolution algorithm - automatically discovers and reroutes across obstacles and learns them permanently.
  - Shortest path routing for navigation (SSSP using Dijkstra's algorithm) - picks the best route to every destination intelligently.
  - Waypoints recording, visualization and optimization (optional).
- Memory-reading engine
  - Obtain information like HP, MP, coordinates, map information, target information, and more directly from game engine.
- Others
  - Control game even when game is minimized.

# Getting Started

## Combat automation

### Assist

Automates rotations for your character, leaving you free to make other decisions.

<img src="./readme_resources/assist.png" />

Modify `main.py` and change `mode` to the following:
- `assist`
  - Automatically run attack rotation only when you select a target and it is in range.
- `assist_autotarget`
  - Automatically select nearest enemy and run attack rotation when in range.
- `assist_autoapproach`
  - Automatically approach your selected enemy and run attack rotation when in range.
- `assist_autotarget_autoapproach`
  - Automatically select nearest enemy, approach, and run attack rotation when in range.

Update the dictionary of `spells` in `botlib/jobs/black_mage.py` accordingly (or move your own hotbar to match).

Run `main.py` and have fun!

## Gameplay automation

### Dungeon

Automates dungeon runs with human-like navigation and fighting.

<img src="./readme_resources/dungeon.png" />

Note: The `assist` modes above need to be working before trying out `dungeon` mode.

Modify `main.py` with the following changes:
1. Change `mode` to `dungeon`.
2. Specify the correct `dungeon_config`.
3. ~~Point to the right waypoint file (there are some samples in recordings folder, or record your own)~~ (Optional)
4. ~~Specify the correct end coordinate (when using your own recording, ensure that you test using visualize tool)~~ (Optional)

Run `main.py` and have fun!

## Waypoints

Note:
- Manual waypoint recording is optional / deprecated.
- The current engine is able to intelligently learn the map in real-time without any prior recording.
- These instructions here are usually for developmental purposes.

### Record waypoints

Run `main_record.py` and walk around in-game.

When you stop it with CTRL+C, a recording<timestamp>.json will be created containing the waypoints.

### Visualize waypoints

<img src="./readme_resources/visualize.png" />

The above shows a sample recording for Tam-Tara Deepcroft.

Modify `main_visualize.py` and point it to your recording file.

Specify the start and end coordinates for the shortest path routing. (You can try using the first and end coordinates in your recording JSON file.)

Run `main_visualize.py` to generate a visualization of your waypoints and the optimal route based on your start and end coordinates.

### Test waypoints in-game

Modify `main_walk.py` and point it to your recording file. (You may use the sample, which is in Ul'Dah. Start from the Ul'Dah Aetherite Plaza.)

Specify the start and end coordinates for the shortest path routing. (You can try using the first and end coordinates in your recording JSON file.)

Run `main_walk.py` to walk your character between the waypoints nearest to the coordinates you specified.

# Additional tools

## Estimation tools

Running `main_estimate_turn_speed.py` will give you a list of `<hold duration, delta radians>` values for linear regression plotting. Current results show default keyboard turn speed to be `delta radians = 2.4 * hold duration + 0.055`

Running `main_estimate_walk_speed.py` will give you walking speed in yards/sec. Current results show default character speed to be `6 yards/sec`.

Running `main_memory_check.py` will repeatedly print game object values read from memory (shows your current coordinates, rotation, and other information).
