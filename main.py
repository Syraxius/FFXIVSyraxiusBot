import enum
import time

from botlib.bot import Bot
from main_visualize import CRYSTAL, GATE, SHOP, BRASSBLADE, CACTUARS, SATASHA_START, SATASHA_END, TAMTARA_START, TAMTARA_END

skills = {
    'ice': {
        'button': 1,
        'delay': 2.5,
        'recast': 2.5,
    },
    'fire': {
        'button': 2,
        'delay': 2.5,
        'recast': 2.5,
    },
    'transpose': {
        'button': 3,
        'delay': 0.1,
        'recast': 5,
    },
    'fire3': {
        'button': 4,
        'delay': 3.5,
        'recast': 2.5,
    },
    'thunder': {
        'button': 5,
        'delay': 2.5,
        'recast': 2.5,
    },
    'thunder2': {
        'button': 6,
        'delay': 3,
        'recast': 2.5,
    },
    'luciddreaming': {
        'button': 7,
        'delay': 0.1,
        'recast': 60,
    },
    'swiftcast': {
        'button': 8,
        'delay': 0.1,
        'recast': 60,
    },
}


class BlackMageAttackState(enum.Enum):
    INITIATE = 1
    ICE = 2
    FIRE = 3
    THUNDER = 4


class BlackMageBot(Bot):
    def __init__(self, mode, navigation_config=None):
        super(BlackMageBot, self).__init__(self.attack_blackmage, mode=mode, navigation_config=navigation_config)
        self.skills = skills
        self.skill_timestamp = {}
        self.state_attack = BlackMageAttackState.INITIATE
        self.swiftcast_active = False

    def attack_blackmage(self):
        if self.get_skill_is_cooldown('affinity'):
            if self.mp < 2000:
                self.state_attack = BlackMageAttackState.ICE
            else:
                self.state_attack = BlackMageAttackState.INITIATE

        if self.state_attack == BlackMageAttackState.INITIATE:
            if self.mp < 2000:
                self.state_attack = BlackMageAttackState.ICE
            if self.level >= 34:
                self.cast('fire3', swiftcast_active=self.swiftcast_active)
            else:
                self.cast('fire', swiftcast_active=self.swiftcast_active)
            self.set_skill_cooldown('affinity', 15)
            if self.swiftcast_active:
                self.swiftcast_active = False
            self.state_attack = BlackMageAttackState.FIRE

        elif self.state_attack == BlackMageAttackState.FIRE:
            if self.mp < 2000:
                time.sleep(self.get_skill_cooldown_remaining('transpose'))
                self.cast('transpose')
                self.set_skill_cooldown('transpose', self.skills['transpose']['recast'])
                self.set_skill_cooldown('affinity', 15)
                if self.level >= 6:
                    self.state_attack = BlackMageAttackState.THUNDER
                else:
                    self.state_attack = BlackMageAttackState.ICE
                return
            if self.get_skill_cooldown_remaining('luciddreaming') <= 0:
                self.cast('luciddreaming')
                self.set_skill_cooldown('luciddreaming', self.skills['luciddreaming']['recast'])
            self.cast('fire')
            self.set_skill_cooldown('affinity', 15)

        elif self.state_attack == BlackMageAttackState.THUNDER:
            if self.level >= 26:
                self.cast('thunder2')
            else:
                self.cast('thunder')
            self.state_attack = BlackMageAttackState.ICE

        elif self.state_attack == BlackMageAttackState.ICE:
            if self.mp >= 8000:
                if self.level >= 34:
                    if self.get_skill_is_cooldown('swiftcast'):
                        self.cast('swiftcast')
                        self.set_skill_cooldown('swiftcast', self.skills['swiftcast']['recast'])
                        self.swiftcast_active = True
                        self.state_attack = BlackMageAttackState.INITIATE
                        return
                else:
                    if self.get_skill_is_cooldown('transpose'):
                        self.cast('transpose')
                        self.set_skill_cooldown('transpose', self.skills['transpose']['recast'])
                        self.set_skill_cooldown('affinity', 15)
                        self.state_attack = BlackMageAttackState.FIRE
                        return
            self.cast('ice')
            self.set_skill_cooldown('affinity', 15)


def main():
    navigation_config = {
        'tamtara': {
            'recordings': ['recordings/tamtara1.json', 'recordings/tamtara2.json', 'recordings/tamtara3.json'],
            'navigation_cache_name': 'recordings/tamtaracombined.cache',
            'navigation_target': TAMTARA_END,
            'navigation_map_id': 8,
        }
    }
    bot = BlackMageBot(mode='dungeon', navigation_config=navigation_config['tamtara'])
    bot.start()


if __name__ == '__main__':
    main()
