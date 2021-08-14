from gevent import monkey
monkey.patch_all()

import time

from botlib.bot import Bot
from main_visualize import CRYSTAL, OUTSIDE_CRYSTAL, GATE, SHOP, BRASSBLADE, CACTUARS


def walk(bot, destination):
    bot.scan()
    a = bot.get_own_coordinate()
    b = destination
    shortest_path = bot.w.get_shortest_path_coordinates(a, b)
    curr_node = shortest_path.pop(0)
    prev_node = None
    prev_distance_delta = None
    while True:
        bot.scan()
        if len(shortest_path) == 0:
            bot.ensure_walking_state(False)
            break
        if curr_node is None:
            curr_node = shortest_path.pop(0)
            print('Next node is %s at %s' % (curr_node.index, curr_node.coordinate))
            prev_distance_delta = None
        distance_delta, direction_delta, is_turn_left = bot.calculate_navigation(curr_node.coordinate[0], curr_node.coordinate[1])
        # print(distance_delta, direction_delta, is_turn_left)
        if prev_distance_delta:
            if prev_distance_delta - distance_delta < 0.01 and bot.is_moving == 1:
                print('STUCK!!!')
                if prev_node:
                    print('Unlinking %s from %s' % (prev_node.index, curr_node.index))
                    prev_node.unlink_from(curr_node)
                    shortest_path = bot.w.get_shortest_path_coordinates(prev_node.coordinate, b)
                    if prev_node:
                        print('Next rolling back to node %s at %s' % (prev_node.index, prev_node.coordinate))
                else:
                    shortest_path = bot.w.get_shortest_path_coordinates(bot.get_own_coordinate(), b)
                    if prev_node:
                        print('Next rolling back to current coordinates at %s' % (bot.get_own_coordinate()))
                curr_node = None
                prev_node = None
                prev_distance_delta = None
                continue
        if distance_delta < 1:
            prev_node = curr_node
            curr_node = None
        else:
            bot.turn_to_target(curr_node.coordinate[0], curr_node.coordinate[1])
            bot.ensure_walking_state(True)
        prev_distance_delta = distance_delta
        time.sleep(0.05)


def main():
    bot = Bot()
    bot.w.load_adjacency_list('caches/autolearn_%s.cache' % bot.map_id)
    walk(bot, CRYSTAL)
    walk(bot, OUTSIDE_CRYSTAL)
    walk(bot, CRYSTAL)
    walk(bot, OUTSIDE_CRYSTAL)
    walk(bot, CRYSTAL)
    walk(bot, OUTSIDE_CRYSTAL)
    walk(bot, CRYSTAL)


if __name__ == '__main__':
    main()
