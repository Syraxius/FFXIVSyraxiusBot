from waypointlib.routing import WaypointRouter
from waypointlib.visualize import visualize_coordinates

SHOP = [-68.68133544921875, -110.83563232421875, 4.611909866333008]
GATE = [-166.8415069580078, -15.939008712768555, 13.29746150970459]
CRYSTAL = [-153.48963928222656, -155.07110595703125, -2.0]
OUTSIDE_CRYSTAL = [-133.09352111816406, -127.75234985351562, 2.0]

SATASHA_START = [359.743896484375, -224.9156036376953, 45.95530319213867]
SATASHA_END = [-323.0476989746094, 341.2820129394531, 5.576686859130859]

TAMTARA_START = [-55.617027282714844, -142.02220153808594, 49.4320068359375]
TAMTARA_END = [-42.771080020000000, -17.288520810000000, 14.0677499800000]

TOTORAK_START = [-320.5662841796875, -79.58805847167969, 11.879193305969238]
TOTORAK_END = [237.2834014892578, -139.6256103515625, -39.54104995727539]


def main():
    # Using recording:
    # recordings = ['recordings/tamtara1.json', 'recordings/tamtara2.json', 'recordings/tamtara3.json']
    # w = WaypointRouter(recordings=recordings, custom_cache_name='caches/tamtaracombined.cache')

    # Using cache directly:
    w = WaypointRouter()
    w.load_adjacency_list('caches/autolearn_9.cache')

    a = TOTORAK_START
    b = TOTORAK_END
    adjacency_list = w.get_adjacency_list()
    coordinates = []
    for adjacency_list_node in adjacency_list:
        coordinates.append(adjacency_list_node.coordinate)
    shortest_path = w.get_shortest_path_coordinates(a, b)
    shortest_path_coordinates = []
    for node in shortest_path:
        shortest_path_coordinates.append(node.coordinate)
    visualize_coordinates(coordinates, shortest_path_coordinates)


if __name__ == '__main__':
    main()
