import time

from botlib.bot import Bot
from waypointlib.routing import get_euclidean_distance


def estimate_walk_speed(bot):
    bot.scan()
    prev_coordinate = bot.get_own_coordinate()
    results = []
    bot.ensure_walking_state(True)
    for i in range(10):
        bot.scan()
        curr_coordinate = bot.get_own_coordinate()
        delta_distance = get_euclidean_distance(prev_coordinate, curr_coordinate)
        print(curr_coordinate, prev_coordinate)
        prev_coordinate = curr_coordinate
        results.append(delta_distance)
        time.sleep(1)
    bot.ensure_walking_state(False)
    print(results)


def main():
    bot = Bot()
    estimate_walk_speed(bot)


if __name__ == '__main__':
    main()
