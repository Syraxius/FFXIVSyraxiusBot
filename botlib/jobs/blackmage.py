import enum
import time

from botlib.bot import Bot

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
        'delay': 0,
        'recast': 5,
    },
    'blizzard3': {
        'button': 4,
        'delay': 3.5,
        'recast': 2.5,
    },
    'fire3': {
        'button': 5,
        'delay': 3.5,
        'recast': 2.5,
    },
    'thunder': {
        'button': 6,
        'delay': 2.5,
        'recast': 2.5,
    },
    'thunder2': {
        'button': 7,
        'delay': 3,
        'recast': 2.5,
    },
    'thunder3': {
        'button': 6,
        'delay': 2.5,
        'recast': 2.5,
    },
    'luciddreaming': {
        'button': 8,
        'delay': 0,
        'recast': 60,
    },
    'swiftcast': {
        'button': 9,
        'delay': 0,
        'recast': 60,
    },
}


class BlackMageAttackState(enum.Enum):
    INITIATE = 1
    BUFFS = 2
    ICE = 3
    FIRE = 4
    THUNDER = 5
    TRANSPOSE_TO_ICE = 6
    TRANSPOSE_TO_FIRE = 7


class BlackMageBot(Bot):
    def __init__(self, mode, dungeon_config=None, navigation_config=None):
        super(BlackMageBot, self).__init__(self.attack_blackmage, mode=mode, dungeon_config=dungeon_config, navigation_config=navigation_config)
        self.skills = skills
        self.skill_timestamp = {}
        self.change_state_attack(BlackMageAttackState.INITIATE)

    def attack_blackmage(self):
        if self.state_attack == BlackMageAttackState.INITIATE:
            if self.own['mp'] < 4000:
                self.change_state_attack(BlackMageAttackState.ICE)
                return
            if self.own['level'] >= 34:
                self.cast('fire3')
            else:
                self.cast('fire')
            self.change_state_attack(BlackMageAttackState.BUFFS)

        elif self.state_attack == BlackMageAttackState.BUFFS:
            if self.get_skill_is_cooldown('luciddreaming'):
                self.cast('luciddreaming')
                self.set_skill_cooldown('luciddreaming', self.skills['luciddreaming']['recast'])
            self.change_state_attack(BlackMageAttackState.FIRE)

        elif self.state_attack == BlackMageAttackState.FIRE:
            if self.own['mp'] < 2400:
                self.change_state_attack(BlackMageAttackState.TRANSPOSE_TO_ICE)
                return
            self.cast('fire')

        elif self.state_attack == BlackMageAttackState.TRANSPOSE_TO_ICE:
            if self.own['level'] >= 40:
                self.cast('blizzard3')
            else:
                time.sleep(self.get_skill_cooldown_remaining('transpose'))
                self.cast('transpose')
                self.set_skill_cooldown('transpose', self.skills['transpose']['recast'])
            self.state_attack = BlackMageAttackState.THUNDER

        elif self.state_attack == BlackMageAttackState.THUNDER:
            if self.own['level'] >= 26:
                self.cast('thunder2')
            elif self.own['level'] >= 6:
                self.cast('thunder')
            self.change_state_attack(BlackMageAttackState.ICE)

        elif self.state_attack == BlackMageAttackState.ICE:
            if self.own['mp'] >= 7000:
                self.change_state_attack(BlackMageAttackState.TRANSPOSE_TO_FIRE)
                return
            self.cast('ice')

        elif self.state_attack == BlackMageAttackState.TRANSPOSE_TO_FIRE:
            if self.own['level'] >= 34:
                self.cast('fire3')
                self.change_state_attack(BlackMageAttackState.FIRE)
                return
            else:
                if self.get_skill_is_cooldown('transpose'):
                    time.sleep(self.get_skill_cooldown_remaining('transpose'))
                    self.cast('transpose')
                    self.set_skill_cooldown('transpose', self.skills['transpose']['recast'])
                    self.change_state_attack(BlackMageAttackState.FIRE)
