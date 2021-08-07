from botlib.bot import Bot
from main_visualize import CRYSTAL, GATE, SHOP


def main():
    bot = Bot()
    recording = 'recordings/uldahsample.json'
    bot.walk(recording, CRYSTAL)
    bot.walk(recording, GATE)


if __name__ == '__main__':
    main()
