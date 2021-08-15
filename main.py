import signal

from botlib.jobs.blackmage import BlackMageBot
from main_visualize import OUTSIDE_CRYSTAL, TAMTARA_END


def main():
    dungeon_config = {
        'tamtara': {
            'exit_coordinate': TAMTARA_END,
            'map_id': 8,
        },
        'uldah': {
            'exit_coordinate': OUTSIDE_CRYSTAL,
            'map_id': 13,
        }
    }
    navigation_config = {
        'empty': {
            'recordings': None,
            'custom_cache_name': None,
        }, 'uldah': {
            'recordings': ['caches/sampleuldah.json'],
            'custom_cache_name': None,
        }, 'tamtara': {
            'recordings': ['recordings/tamtara1.json', 'recordings/tamtara2.json', 'recordings/tamtara3.json'],
            'custom_cache_name': 'caches/tamtaracombined.cache',
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
