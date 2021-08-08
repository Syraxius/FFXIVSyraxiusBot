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
    w = WaypointRouter(coordinates)
    bot.scan()
    a = bot.get_current_coordinate()
    b = destination
    shortest_path = w.get_shortest_path_coordinates(a, b)
    print('Shortest path:' % shortest_path)
    next_coordinate = shortest_path.pop(0)
    is_autorun = False
    while True:
        bot.scan()
        if len(shortest_path) == 0:
            if is_autorun:
                keyboard_send_vk_as_scan_code(bot.hwnd, win32api.VkKeyScanEx('r', 0))
                is_autorun = False
            break
        if next_coordinate is None:
            next_coordinate = shortest_path.pop(0)
        direction_delta, distance_delta, is_turn_left = bot.calculate_navigation(next_coordinate[0], next_coordinate[1])
        print(direction_delta, distance_delta, is_turn_left)
        if distance_delta < 1:
            next_coordinate = None
        else:
            # Delta Radians = 2.65 * Turn Duration + 0.0142
            # Delta Radians = 2.4 * Turn Duration + 0.055
            # Why different?
            turn_speed = 2.4  # rad/s
            turn_min_amount = 0.055
            turn_duration = (abs(direction_delta) - turn_min_amount) / turn_speed
            if turn_duration > 0.3:
                if is_autorun:
                    keyboard_send_vk_as_scan_code(bot.hwnd, win32api.VkKeyScanEx('r', 0))
                    is_autorun = False
            if turn_duration > 0:
                if is_turn_left:
                    keyboard_send_vk_as_scan_code(bot.hwnd, win32api.VkKeyScanEx('a', 0), action='hold', duration=turn_duration)  # Hotkey for turn left
                else:
                    keyboard_send_vk_as_scan_code(bot.hwnd, win32api.VkKeyScanEx('d', 0), action='hold', duration=turn_duration)  # Hotkey for turn right
            if not is_autorun:
                keyboard_send_vk_as_scan_code(bot.hwnd, win32api.VkKeyScanEx('r', 0))
                is_autorun = True
        time.sleep(0.05)


def main():
    bot = Bot()
    recording = 'recordings/uldahsample.json'
    walk(bot, recording, CRYSTAL)
    walk(bot, recording, GATE)


if __name__ == '__main__':
    main()
