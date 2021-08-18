import time

from botlib.bot import Bot


def main():
    bot = Bot()
    while True:
        bot.scan()
        print(bot.own)
        # print(bot.target)
        time.sleep(0.1)


if __name__ == '__main__':
    main()
