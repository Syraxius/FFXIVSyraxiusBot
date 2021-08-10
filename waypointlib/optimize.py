import json
import math
import os
import pickle

debouncing_distance = 0.2
connecting_distance = 3


def get_euclidean_distance(coordinate_a, coordinate_b):
    coordinate_diff = []
    for i in range(len(coordinate_a)):
        coordinate_diff.append(coordinate_a[i] - coordinate_b[i])
    return math.sqrt(sum(i ** 2 for i in coordinate_diff))


def get_euclidean_distance_flat(coordinate_a, coordinate_b):
    coordinate_diff = []
    for i in range(2):
        coordinate_diff.append(coordinate_a[i] - coordinate_b[i])
    return math.sqrt(sum(i ** 2 for i in coordinate_diff))


def debounce_coordinates(coordinates):
    debounced_coordinates = []
    prev_coordinate = None
    for coordinate in coordinates:
        if not prev_coordinate:
            prev_coordinate = coordinate
            continue
        if get_euclidean_distance(coordinate, prev_coordinate) >= debouncing_distance:
            debounced_coordinates.append(coordinate)
        prev_coordinate = coordinate
    return debounced_coordinates


class AdjacencyListNode:
    def __init__(self, index, coordinate):
        self.index = index
        self.coordinate = coordinate
        self.neighbors = set()

    def link_to(self, other_node):
        self.neighbors.add(other_node.index)
        other_node.neighbors.add(self.index)


def generate_adjacency_list(coordinates, existing_adjacency_list):
    adjacency_list = []
    if existing_adjacency_list:
        adjacency_list = existing_adjacency_list
    prev_adjacency_list_node = None
    index_offset = len(adjacency_list)
    for index in range(len(coordinates)):
        eff_index = index + index_offset
        coordinate = coordinates[index]
        curr_adjacency_list_node = AdjacencyListNode(eff_index, coordinate)
        if prev_adjacency_list_node:
            prev_adjacency_list_node.link_to(curr_adjacency_list_node)
        for other_adjacency_list_node in adjacency_list:
            curr_distance = get_euclidean_distance(curr_adjacency_list_node.coordinate, other_adjacency_list_node.coordinate)
            # print('%s->%s = %s' % (curr_adjacency_list_node.index, other_adjacency_list_node.index, curr_distance))
            if curr_distance < connecting_distance:
                curr_adjacency_list_node.link_to(other_adjacency_list_node)
        adjacency_list.append(curr_adjacency_list_node)
        prev_adjacency_list_node = curr_adjacency_list_node
    return adjacency_list


def print_adjacency_list(adjacency_list):
    for adjacency_list_node in adjacency_list:
        print('%s:%s: %s' % (adjacency_list_node.index, adjacency_list_node.coordinate, adjacency_list_node.neighbors))


def generate_optimized_adjacency_list(coordinates, existing_adjacency_list):
    debounced_coordinates = debounce_coordinates(coordinates)
    adjacency_list = generate_adjacency_list(debounced_coordinates, existing_adjacency_list)
    return adjacency_list


def generate_optimized_adjacency_list_from_file(recordings, custom_cache_name=None):
    cache_name = '%s.cache' % recordings[0]
    if custom_cache_name:
        cache_name = custom_cache_name
    if os.path.isfile(cache_name):
        with open(cache_name, 'rb') as f:
            adjacency_list = pickle.load(f)
        return adjacency_list
    adjacency_list = []
    for recording in recordings:
        with open(recording) as f:
            coordinates = json.loads(f.read())
        adjacency_list = generate_optimized_adjacency_list(coordinates, adjacency_list)
    with open(cache_name, 'wb') as f:
        pickle.dump(adjacency_list, f)
    return adjacency_list
