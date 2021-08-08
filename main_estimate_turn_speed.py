from botlib.bot import Bot

import math
import time

import win32api

from botlib.control import keyboard_send_vk_as_scan_code


def estimate_turn_speed(bot):
    bot.scan()
    prev_direction = math.atan2(bot.y_complex, bot.x_complex)
    if prev_direction < 0:
        prev_direction += 2 * math.pi
    results = []
    for i in range(100):
        total_radians = 0.0
        turn_duration = 0.01 * i
        times = 1
        for _ in range(times):
            bot.turn_by_duration('left', turn_duration)
            bot.scan()
            current_direction = math.atan2(bot.y_complex, bot.x_complex)
            if current_direction < 0:
                current_direction += 2 * math.pi
            provisional_direction = current_direction - prev_direction
            if -math.pi < provisional_direction < math.pi:
                final_direction = provisional_direction
            elif 180 < provisional_direction:
                final_direction = provisional_direction - 2 * math.pi
            else:
                final_direction = provisional_direction + 2 * math.pi
            print(final_direction)
            total_radians += final_direction
            prev_direction = current_direction
            time.sleep(0.1)
        average_radians = total_radians / times
        results.append((turn_duration, average_radians))
    print(results)


def main():
    bot = Bot()
    estimate_turn_speed(bot)


if __name__ == '__main__':
    main()
