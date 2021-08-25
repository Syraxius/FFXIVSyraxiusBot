import signal

from botlib.jobs.blackmage import BlackMageBot
from main_visualize import OUTSIDE_CRYSTAL, TAMTARA_END, TOTORAK_END


def main():
    dungeon_config = {
        'uldah': {
            'exit_coordinate': OUTSIDE_CRYSTAL,
            'map_id': 13,
        }, 'tamtara': {
            'exit_coordinate': TAMTARA_END,
            'map_id': 8,
        }, 'totorak': {
            'exit_coordinate': TOTORAK_END,
            'map_id': 9,
        }
    }
    bot = BlackMageBot(mode='dungeon', dungeon_config=dungeon_config['tamtara'])

    def handler(signum, frame):
        bot.stop_all()
    signal.signal(signal.SIGINT, handler)

    bot.learn_asynchronous()
    bot.start_asynchronous()
    bot.joinall()


if __name__ == '__main__':
    main()
