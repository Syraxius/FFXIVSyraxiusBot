from botlib.bot import Bot
from main_visualize import CRYSTAL, GATE, SHOP

import json
import time

import win32api

from botlib.control import keyboard_send_vk_as_scan_code
from waypointlib.routing import WaypointRouter


def walk(bot, recording, destination):
    with open(recording) as f:
        coordinates = json.loads(f.read())
    bot.scan()
    a = bot.get_current_coordinate()
    b = destination
    w = WaypointRouter(coordinates)
    shortest_path = w.get_shortest_path_coordinates(a, b)
    print('Shortest path:' % shortest_path)
    next_coordinate = shortest_path.pop(0)
    while True:
        bot.scan()
        if len(shortest_path) == 0:
            bot.ensure_walking_state(False)
            break
        if next_coordinate is None:
            next_coordinate = shortest_path.pop(0)
        distance_delta, direction_delta, is_turn_left = bot.calculate_navigation(next_coordinate[0], next_coordinate[1])
        print(distance_delta, direction_delta, is_turn_left)
        if distance_delta < 1:
            next_coordinate = None
        else:
            turn_duration = bot.get_turn_duration(direction_delta)
            if turn_duration > 0.3:
                bot.ensure_walking_state(False)
            if turn_duration > 0:
                if is_turn_left:
                    bot.turn_by_duration('left', turn_duration)
                else:
                    bot.turn_by_duration('right', turn_duration)
            bot.ensure_walking_state(True)
        time.sleep(0.05)


def main():
    bot = Bot()
    recording = 'recordings/uldahsample.json'
    walk(bot, recording, GATE)
    walk(bot, recording, CRYSTAL)


if __name__ == '__main__':
    main()
