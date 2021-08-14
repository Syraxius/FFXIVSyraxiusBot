import matplotlib.pyplot as plt


def get_points(coordinates):
    x_points = []
    y_points = []
    z_points = []
    for coordinate in coordinates:
        x_points.append(coordinate[0])
        y_points.append(-coordinate[1])
        z_points.append(coordinate[2])
    return x_points, y_points, z_points


def visualize_coordinates(coordinates, path=None):
    ax = plt.axes(projection='3d')
    ax.set_xlabel('x axis')
    ax.set_ylabel('y axis')
    ax.set_zlabel('z axis')

    x_points, y_points, z_points = get_points(coordinates)
    ax.scatter3D(x_points, y_points, z_points, s=1)
    if path:
        x_path_points, y_path_points, z_path_points = get_points(path)
        ax.plot3D(x_path_points, y_path_points, z_path_points, 'red')

    plt.show()
