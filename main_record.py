from gevent import monkey
monkey.patch_all()

import signal
from botlib.bot import Bot


def main():
    bot = Bot()
    bot.record_asynchronous()

    def handler(signum, frame):
        bot.stop_all()
    signal.signal(signal.SIGINT, handler)

    bot.joinall()


if __name__ == '__main__':
    main()
