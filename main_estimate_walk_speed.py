from botlib.bot import Bot

import time

import win32api

from botlib.control import keyboard_send_vk_as_scan_code
from waypointlib.routing import get_euclidean_distance


def estimate_walk_speed(bot):
    bot.scan()
    prev_coordinate = bot.get_current_coordinate()
    results = []
    keyboard_send_vk_as_scan_code(bot.hwnd, win32api.VkKeyScanEx('r', 0))
    for i in range(10):
        bot.scan()
        curr_coordinate = bot.get_current_coordinate()
        delta_distance = get_euclidean_distance(prev_coordinate, curr_coordinate)
        print(curr_coordinate, prev_coordinate)
        prev_coordinate = curr_coordinate
        results.append(delta_distance)
        time.sleep(1)
    keyboard_send_vk_as_scan_code(bot.hwnd, win32api.VkKeyScanEx('r', 0))
    print(results)


def main():
    bot = Bot()
    estimate_walk_speed(bot)


if __name__ == '__main__':
    main()
