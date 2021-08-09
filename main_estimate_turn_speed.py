import math
import time

from botlib.bot import Bot


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
            final_direction = bot.calculate_final_direction(current_direction, prev_direction)
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
