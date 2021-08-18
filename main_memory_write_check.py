import time

from botlib.bot import Bot, address_descriptions
from botlib.memory import set_memory_value


def main():
    bot = Bot()
    hwnd = bot.hwnd
    address_description = address_descriptions['character_rotation']
    value = 0.1
    set_memory_value(hwnd, bot.base_address, address_description, value)


if __name__ == '__main__':
    main()
