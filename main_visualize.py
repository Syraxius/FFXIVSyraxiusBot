import json
from waypointlib.routing import WaypointRouter
from waypointlib.visualize import visualize_coordinates

SHOP = [-68.68133544921875, -110.83563232421875, 4.611909866333008]  # Shop
GATE = [-166.8415069580078, -15.939008712768555, 13.29746150970459]  # Gate
CRYSTAL = [-155.56903076171875, -157.19174194335938, -2.0]  # Crystal


def main():
    with open('recordings/uldahsample.json') as f:
        coordinates = json.loads(f.read())
    w = WaypointRouter(coordinates)
    a = CRYSTAL
    b = GATE
    shortest_path = w.get_shortest_path_coordinates(a, b)
    visualize_coordinates(coordinates, shortest_path)


if __name__ == '__main__':
    main()
