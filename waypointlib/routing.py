from queue import PriorityQueue

from .optimize import generate_optimized_adjacency_list_from_file, get_euclidean_distance


class WaypointRouter:
    def __init__(self, recording):
        self.adjacency_list = generate_optimized_adjacency_list_from_file(recording)

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
        for _ in range(len(self.adjacency_list)):
            parent.append(-1)
            distance.append(999999)
        parent[nearest_adjacency_list_node_a.index] = nearest_adjacency_list_node_a.index
        distance[nearest_adjacency_list_node_a.index] = 0
        pq = PriorityQueue()
        pq.put((0, nearest_adjacency_list_node_a.index, nearest_adjacency_list_node_a))
        while pq:
            # print(parent)
            curr_distance, _, curr_node = pq.get()
            for neighbor in curr_node.neighbors:
                neighbor_node = self.adjacency_list[neighbor]
                curr_neighbor_distance = curr_distance + get_euclidean_distance(curr_node.coordinate, neighbor_node.coordinate)
                if curr_neighbor_distance < distance[neighbor_node.index]:
                    parent[neighbor_node.index] = curr_node.index
                    distance[neighbor_node.index] = curr_neighbor_distance
                    pq.put((curr_neighbor_distance, neighbor_node.index, neighbor_node))
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
