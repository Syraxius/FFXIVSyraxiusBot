# FFXIVSyraxiusBot
Experimental bot for FFXIV. Still WIP.

# Features

- Navigation:
  - Waypoints record
  - Waypoints visualization
  - Shortest path routing (Dijkstra)
  - Human-like in-game character control
- Combat automation:
  - BlackMage automatic optimal ice/fire combo
  - Other classes combo still WIP
- Gameplay automation:
  - Dungeon
    - Waypoint-based navigation
    - Human-like movement and fighting
    - Progress through dungeon with the team
    - Automatically engage only aggro'ed monsters
    - Automatically skip cutscenes

# Waypoints

## Record waypoints

Run `main_record.py` and walk around.

When you stop it with CTRL+C, a recording<timestamp>.json will be created containing the waypoints.

## Visualize waypoints

<img src="./readme_resources/visualize.png" />

The above shows a sample recording for Tam-Tara Deepcroft.

Modify `main_visualize.py` and point it to your recording file.

Specify the start and end coordinates for the routing (you can peek in your recording file for reference).

Run `main_visualize.py` to generate visualization of your waypoints.

## Test waypoints in-game

Modify `main_walk.py` and point it to your recording file.

Specify the start and end coordinates for the routing (you can peek in your recording file for reference).

Run `main_walk.py` to walk your character between the waypoints nearest to the coordinates you specified.

# Bot

(Note that all modes also automatically dump a waypoint recording for use later)

## Combat assistance

Modify `main.py` and change `mode` to the following:
- `assist` - Run attack combo when target selected and within range
- `assist_autotarget` - Automatically select nearest enemy and attack if in range
- `assist_autotarget_autoapproach` - Automatically select nearest enemy, approach, and attack when in range
- `assist_autoapproach` - Automatically approach your selected enemy and attack when in range

Run `main.py` and have fun!

## Dungeon

Modify `main.py` with the following changes:
- Change `mode` to `dungeon`
- Point to the right waypoint file (there are some samples in recordings folder, or record your own)
- Specify the correct end coordinate (when using your own recording, ensure that you test using visualize tool)

Run `main.py` and have fun!

# Additional tools

## Estimation tools

Running `main_estimate_turn_speed.py` will give you a list of <hold duration, delta radians> values for linear regression plotting.
- Current results show default keyboard turn speed to be `delta radians = 2.4 * hold duration + 0.055`

Running `main_estimate_walk_speed.py` will give you walking speed in yards/sec.
- Current results show default character speed to be `6 yards/sec`.