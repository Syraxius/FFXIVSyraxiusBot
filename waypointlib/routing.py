from queue import PriorityQueue

from .optimize import generate_optimized_adjacency_list_from_file, get_euclidean_distance, debouncing_distance, connecting_distance, add_to_adjacency_list, AdjacencyListNode, save_adjacency_list_to_file, load_adjacency_list_from_file


class WaypointRouter:
    def __init__(self, recordings=None, custom_cache_name=None):
        if recordings:
            self.adjacency_list = generate_optimized_adjacency_list_from_file(recordings, custom_cache_name=custom_cache_name)
        else:
            self.adjacency_list = []

    def get_adjacency_list(self):
        return self.adjacency_list

    def save_adjacency_list(self, cache_name):
        print('Writing %s nodes to %s' % (len(self.adjacency_list), cache_name))
        save_adjacency_list_to_file(self.adjacency_list, cache_name)

    def load_adjacency_list(self, cache_name):
        adjacency_list = load_adjacency_list_from_file(cache_name)
        if adjacency_list:
            self.adjacency_list = adjacency_list
        else:
            self.adjacency_list = []
        print('Loaded %s nodes from %s' % (len(self.adjacency_list), cache_name))

    def add_to_adjacency_list(self, coordinate, can_add_unconnected=False):
        nearest = self.get_closest_adjacency_list_node(coordinate)
        if not nearest:
            node = AdjacencyListNode(0, coordinate)
            self.adjacency_list.append(node)
            return node
        distance = get_euclidean_distance(nearest.coordinate, coordinate)
        if can_add_unconnected:
            if debouncing_distance < distance:
                return add_to_adjacency_list(coordinate, self.adjacency_list)
        else:
            if debouncing_distance < distance < connecting_distance:
                return add_to_adjacency_list(coordinate, self.adjacency_list)
        return None

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
        if not nearest_adjacency_list_node_a or not nearest_adjacency_list_node_b:
            return []
        parent = {nearest_adjacency_list_node_a.index: nearest_adjacency_list_node_a.index}
        distance = {nearest_adjacency_list_node_a.index: 0}
        pq = PriorityQueue()
        pq.put((0, nearest_adjacency_list_node_a.index, nearest_adjacency_list_node_a))
        while pq:
            # print(parent)
            curr_distance, _, curr_node = pq.get()
            if curr_distance > distance.get(curr_node.index, 999999):
                continue
            for neighbor in curr_node.neighbors:
                neighbor_node = self.adjacency_list[neighbor]
                curr_neighbor_distance = curr_distance + get_euclidean_distance(curr_node.coordinate, neighbor_node.coordinate)
                if curr_neighbor_distance < distance.get(neighbor_node.index, 999999):
                    parent[neighbor_node.index] = curr_node.index
                    distance[neighbor_node.index] = curr_neighbor_distance
                    pq.put((curr_neighbor_distance, neighbor_node.index, neighbor_node))
            if parent.get(nearest_adjacency_list_node_b.index, -1) != -1:
                break
        if parent.get(nearest_adjacency_list_node_b.index, -1) != -1:
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
            coordinates.append(self.adjacency_list[i])
        return coordinates
