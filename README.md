# FFXIVSyraxiusBot
Experimental bot for FFXIV. Still WIP.

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
