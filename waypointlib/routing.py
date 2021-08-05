import json
from queue import PriorityQueue
from optimize import generate_optimized_adjacency_list, get_euclidean_distance, print_adjacency_list
from visualize import visualize_coordinates


class WaypointRouter:
    def __init__(self, coordinates):
        self.adjacency_list = generate_optimized_adjacency_list(coordinates)

    def get_closest_adjacency_list_node(self, coordinate):
        closest_adjacency_list_node = None
        closest_distance = 999999
        for adjacency_list_node in self.adjacency_list:
            if closest_adjacency_list_node is None:
                closest_adjacency_list_node = adjacency_list_node
            curr_distance = get_euclidean_distance(coordinate, adjacency_list_node.coordinate)
            if curr_distance < closest_distance:
                closest_adjacency_list_node = adjacency_list_node
                closest_distance = curr_distance
        return closest_adjacency_list_node

    def get_shortest_path(self, coordinate_a, coordinate_b):
        # print_adjacency_list(self.adjacency_list)
        nearest_adjacency_list_node_a = self.get_closest_adjacency_list_node(coordinate_a)
        nearest_adjacency_list_node_b = self.get_closest_adjacency_list_node(coordinate_b)
        parent = []
        distance = []
        for i in range(len(self.adjacency_list)):
            parent.append(-1)
            distance.append(999999)
        parent[nearest_adjacency_list_node_a.index] = nearest_adjacency_list_node_a.index
        distance[nearest_adjacency_list_node_a.index] = 0
        pq = PriorityQueue()
        pq.put((0, nearest_adjacency_list_node_a))
        while pq:
            curr_distance, curr_node = pq.get()
            for neighbor in curr_node.neighbors:
                neighbor_node = self.adjacency_list[neighbor]
                curr_neighbor_distance = curr_distance + get_euclidean_distance(curr_node.coordinate, neighbor_node.coordinate)
                if curr_neighbor_distance < distance[neighbor_node.index]:
                    parent[neighbor_node.index] = curr_node.index
                    distance[neighbor_node.index] = curr_neighbor_distance
                    pq.put((curr_neighbor_distance, neighbor_node))
            if parent[nearest_adjacency_list_node_b.index] != -1:
                break
        if parent[nearest_adjacency_list_node_b.index] != -1:
            path = []
            curr_index = nearest_adjacency_list_node_b.index
            while parent[curr_index] != curr_index:
               path.append(curr_index)
               curr_index = parent[curr_index]
            path.append(curr_index)
            path.reverse()
            return path
        else:
            return []

    def get_shortest_path_coordinates(self, coordinate_a, coordinate_b):
        path = self.get_shortest_path(coordinate_a, coordinate_b)
        coordinates = []
        for i in path:
            coordinates.append(self.adjacency_list[i].coordinate)
        return coordinates


def main():
    with open('recordingsample.json') as f:
        coordinates = json.loads(f.read())
    w = WaypointRouter(coordinates)
    a = [-155.91844177246094, -171.25912475585938, -2.000059127807617]
    b = [-166.8415069580078, -15.939008712768555, 13.29746150970459]
    shortest_path = w.get_shortest_path_coordinates(a, b)
    visualize_coordinates(coordinates, shortest_path)


if __name__ == '__main__':
    main()