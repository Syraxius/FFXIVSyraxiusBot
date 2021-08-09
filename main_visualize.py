import json

from waypointlib.routing import WaypointRouter
from waypointlib.visualize import visualize_coordinates

# sampleuldah.json
SHOP = [-68.68133544921875, -110.83563232421875, 4.611909866333008]
GATE = [-166.8415069580078, -15.939008712768555, 13.29746150970459]
CRYSTAL = [-155.56903076171875, -157.19174194335938, -2.0]

# samplewestthanalan.json
BRASSBLADE = [424.6500244140625, 150.00262451171875, 93.94908905029297]
CACTUARS = [278.73040771484375, 151.35186767578125, 54.582115173339844]

# satasha1.json
SATASHA_START = [359.743896484375, -224.9156036376953, 45.95530319213867]
SATASHA_END = [-323.0476989746094, 341.2820129394531, 5.576686859130859]

# tamtara1.json
TAMTARA_START = [-55.617027282714844, -142.02220153808594, 49.4320068359375]
TAMTARA_END = [-44.96254348754883, -17.00678253173828, 14.04631519317627]


def main():
    path = 'recordings/tamtara1.json'
    with open(path) as f:
        coordinates = json.loads(f.read())
    w = WaypointRouter(path)
    a = TAMTARA_START
    b = TAMTARA_END
    shortest_path = w.get_shortest_path_coordinates(a, b)
    visualize_coordinates(coordinates, shortest_path)


if __name__ == '__main__':
    main()
