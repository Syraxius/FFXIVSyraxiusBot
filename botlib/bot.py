import enum
import json
import math
import time

import win32api
import win32con

from botlib.control import keyboard_send_vk_as_scan_code
from botlib.memory import get_winlist, get_hwnd, get_hwnd_base_address, get_memory_values
from waypointlib.routing import get_euclidean_distance

address_descriptions = {
    'mp': {
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (0x1CC,),
        'datatype': 'integer',
    },

    'distance_to_target': {
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (0x378,),
        'datatype': 'float',
    },

    'x': {
        'base_address_offset': 0x1DBBFD0,
        'pointer_offsets': (),
        'datatype': 'float',
    },

    'y': {
        'base_address_offset': 0x1DBBFD8,
        'pointer_offsets': (),
        'datatype': 'float',
    },

    'z': {
        'base_address_offset': 0x1DBBFE0,
        'pointer_offsets': (),
        'datatype': 'float',
    },

    'x_complex': {
        'base_address_offset': 0x01DAF9A8,
        'pointer_offsets': (0x18, 0xD4),
        'datatype': 'float',
    },

    'y_complex': {
        'base_address_offset': 0x01DAF9A8,
        'pointer_offsets': (0x18, 0xCC),
        'datatype': 'float',
    }
}

spells = {
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
        'delay': 0.5,
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
        'delay': 0.5,
        'recast': 60,
    },
    'swiftcast': {
        'button': 8,
        'delay': 0.5,
        'recast': 60,
    },
}


class OverallState(enum.Enum):
    RETURNING = 1
    ACQUIRING = 2
    APPROACHING = 3
    ATTACKING = 4


class BlackMageAttackState(enum.Enum):
    ICE = 1
    FIRE = 2
    FIRE3 = 3
    THUNDER = 4


class Bot:
    def __init__(self, mode='patrol'):
        winlist = get_winlist()
        self.hwnd = get_hwnd('FINAL FANTASY XIV', winlist)
        self.base_address = get_hwnd_base_address(self.hwnd)

        self.mp = 0
        self.distance_to_target = 0
        self.is_target_selected = False
        self.x = 0
        self.y = 0
        self.z = 0
        self.x_complex = 0
        self.y_complex = 0
        self.scan()
        self.init_x = self.x
        self.init_y = self.y
        self.init_z = self.z

        self.state_overall = OverallState.RETURNING
        self.attack = self.attack_blackmage
        self.state_attack = BlackMageAttackState.FIRE3
        self.is_autorun = False
        self.affinity_timestamp = 0
        self.transpose_timestamp = 0
        self.luciddreaming_timestamp = 0
        self.swiftcast_timestamp = 0
        self.swiftcast_active = False

        self.max_distance_to_target = 10
        self.max_patrol_distance = 30
        self.mode = mode  # 'patrol', 'dungeon_follow', 'assist_autotarget', 'assist'
        if self.mode == 'dungeon_follow':
            self.max_distance_to_target = 10
        else:
            self.max_distance_to_target = 25

    def scan(self):
        self.mp = get_memory_values(self.hwnd, self.base_address, address_descriptions['mp'])
        self.x = get_memory_values(self.hwnd, self.base_address, address_descriptions['x'])
        self.y = get_memory_values(self.hwnd, self.base_address, address_descriptions['y'])
        self.z = get_memory_values(self.hwnd, self.base_address, address_descriptions['z'])
        self.x_complex = get_memory_values(self.hwnd, self.base_address, address_descriptions['x_complex'])
        self.y_complex = get_memory_values(self.hwnd, self.base_address, address_descriptions['y_complex'])
        self.distance_to_target = get_memory_values(self.hwnd, self.base_address, address_descriptions['distance_to_target'])
        self.is_target_selected = self.distance_to_target != 0

    def get_current_coordinate(self):
        return [self.x, self.y, self.z]

    def get_current_direction(self):
        curr_direction = math.atan2(self.y_complex, self.x_complex)
        if curr_direction < 0:
            curr_direction += 2 * math.pi
        return curr_direction

    def get_target_direction(self, target_x, target_y):
        direction_x = target_x - self.x
        direction_y = -(target_y - self.y)
        target_direction = math.atan2(direction_y, direction_x)
        if target_direction < 0:
            target_direction = target_direction + 2 * math.pi
        return target_direction

    def ensure_walking_state(self, is_walking):
        if is_walking:
            if not self.is_autorun:
                keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))
                self.is_autorun = True
        elif not is_walking:
            if self.is_autorun:
                keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))
                self.is_autorun = False

    def get_turn_duration(self, radians):
        # Delta Radians = 2.65 * Turn Duration + 0.0142
        # Delta Radians = 2.4 * Turn Duration + 0.055
        # Why different?
        turn_speed = 2.4  # rad/s
        turn_min_amount = 0.055  # rad
        turn_duration = (abs(radians) - turn_min_amount) / turn_speed
        if turn_duration < 0:
            turn_duration = 0
        return turn_duration

    def turn_by_radians(self, direction, radians):
        turn_duration = self.get_turn_duration(radians)
        self.turn_by_duration(direction, turn_duration)

    def turn_by_duration(self, direction, turn_duration):
        if direction == 'left':
            keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('a', 0), action='hold', duration=turn_duration)
        elif direction == 'right':
            keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('d', 0), action='hold', duration=turn_duration)

    def cast(self, spell, swiftcast_active=False):
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx(str(spell['button']), 0))
        if swiftcast_active:
            time.sleep(spell['recast'])
        else:
            time.sleep(spell['delay'])

    def attack_blackmage(self):
        affinity_delta = time.time() - self.affinity_timestamp
        transpose_delta = time.time() - self.transpose_timestamp
        luciddreaming_delta = time.time() - self.luciddreaming_timestamp
        swiftcast_delta = time.time() - self.swiftcast_timestamp

        if affinity_delta > 15:
            if self.mp < 2000:
                self.state_attack = BlackMageAttackState.ICE
            else:
                self.state_attack = BlackMageAttackState.FIRE3

        if self.state_attack == BlackMageAttackState.FIRE3:
            if self.mp < 2000:
                self.state_attack = BlackMageAttackState.ICE
            self.cast(spells['fire3'], swiftcast_active=self.swiftcast_active)
            self.affinity_timestamp = time.time()
            if self.swiftcast_active:
                self.swiftcast_active = False
            self.state_attack = BlackMageAttackState.FIRE
        elif self.state_attack == BlackMageAttackState.FIRE:
            if self.mp < 2000:
                if transpose_delta < spells['transpose']['recast']:
                    time.sleep(transpose_delta)
                self.cast(spells['transpose'])
                self.transpose_timestamp = time.time()
                self.affinity_timestamp = time.time()
                self.state_attack = BlackMageAttackState.THUNDER
                return
            if luciddreaming_delta >= spells['luciddreaming']['recast']:
                self.cast(spells['luciddreaming'])
                self.luciddreaming_timestamp = time.time()
            self.cast(spells['fire'])
            self.affinity_timestamp = time.time()
        elif self.state_attack == BlackMageAttackState.THUNDER:
            self.cast(spells['thunder2'])
            self.state_attack = BlackMageAttackState.ICE
        elif self.state_attack == BlackMageAttackState.ICE:
            if self.mp >= 8000:
                if swiftcast_delta >= spells['swiftcast']['recast']:
                    self.cast(spells['swiftcast'])
                    self.swiftcast_timestamp = time.time()
                    self.swiftcast_active = True
                    self.state_attack = BlackMageAttackState.FIRE3
                    return
                if transpose_delta >= spells['transpose']['recast']:
                    self.cast(spells['transpose'])
                    self.transpose_timestamp = time.time()
                    self.affinity_timestamp = time.time()
                    self.state_attack = BlackMageAttackState.FIRE
                    return
            self.cast(spells['ice'])
            self.affinity_timestamp = time.time()

    def calculate_final_direction(self, target_direction, current_direction):
        provisional_direction = target_direction - current_direction
        if -math.pi < provisional_direction < math.pi:
            final_direction = provisional_direction
        elif 180 < provisional_direction:
            final_direction = provisional_direction - 2 * math.pi
        else:
            final_direction = provisional_direction + 2 * math.pi
        return final_direction

    def calculate_navigation(self, target_x, target_y):
        distance_delta = get_euclidean_distance([self.x, self.y, 0], [target_x, target_y, 0])
        current_direction = self.get_current_direction()
        target_direction = self.get_target_direction(target_x, target_y)
        final_direction = self.calculate_final_direction(target_direction, current_direction)
        is_turn_left = final_direction > 0
        direction_delta = abs(final_direction)
        return distance_delta, direction_delta, is_turn_left

    def start(self):
        is_autorun = False

        last_x = self.x
        last_y = self.y
        last_state = None
        acquiring_timestamp = None

        while True:
            self.scan()

            distance_delta, direction_delta, is_turn_left = self.calculate_navigation(self.init_x, self.init_y)
            delta_y = self.y - last_y
            delta_x = self.x - last_x
            distance_delta_last = math.sqrt((delta_x * delta_x) + (delta_y * delta_y))
            last_x = self.x
            last_y = self.y

            if self.state_overall != last_state:
                print(self.state_overall)
            last_state = self.state_overall

            if self.state_overall == OverallState.RETURNING:
                if self.mode != 'patrol':
                    self.state_overall = OverallState.ACQUIRING
                    acquiring_timestamp = time.time()
                    continue
                if distance_delta < 3:
                    self.state_overall = OverallState.ACQUIRING
                    acquiring_timestamp = time.time()
                    if is_autorun:
                        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))  # Hotkey for autorun
                        is_autorun = False
                    continue
                if abs(direction_delta) > 0.088:
                    if is_autorun:
                        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))  # Hotkey for autorun
                        is_autorun = False
                    turn_speed = 2.8  # rad/s
                    turn_duration = abs(direction_delta) / turn_speed
                    if is_turn_left:
                        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('a', 0), action='hold', duration=turn_duration)  # Hotkey for turn left
                    else:
                        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('d', 0), action='hold', duration=turn_duration)  # Hotkey for turn left
                if distance_delta_last < 0.1 and is_autorun:
                    keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_SPACE)  # Hotkey for jump
                if not is_autorun:
                    keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))  # Hotkey for autorun
                    is_autorun = True
                time.sleep(0.2)

            if self.state_overall == OverallState.ACQUIRING:
                if self.is_target_selected:
                    self.state_overall = OverallState.APPROACHING
                    continue
                if self.mode == 'dungeon_follow':
                    keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('9', 0))  # Hotkey for following focused
                if self.mode == 'patrol' or self.mode == 'dungeon_follow' or self.mode == 'assist_autotarget':
                    keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F11)  # Hotkey for targeting nearest enemy
                time.sleep(0.2)
                if self.mode == 'patrol':
                    if time.time() - acquiring_timestamp > 5:
                        turn_duration = math.pi / 2 / 2.65
                        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('d', 0), action='hold', duration=turn_duration)  # Hotkey for turn left
                        acquiring_timestamp = time.time()
                    if distance_delta > self.max_patrol_distance:
                        self.state_overall = OverallState.RETURNING
                        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F1)  # Hotkey for targeting self, acting as a deselect

            elif self.state_overall == OverallState.APPROACHING:
                if not self.is_target_selected:
                    self.state_overall = OverallState.ACQUIRING
                    acquiring_timestamp = time.time()
                    if is_autorun:
                        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))  # Hotkey for autorun
                        is_autorun = False
                    continue
                if self.distance_to_target < self.max_distance_to_target:
                    self.state_overall = OverallState.ATTACKING
                    if is_autorun:
                        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))  # Hotkey for autorun
                        is_autorun = False
                    continue
                keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('f', 0))  # Hotkey for face
                if distance_delta_last < 0.1 and is_autorun:
                    keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_SPACE)  # Hotkey for jump
                if not is_autorun:
                    keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))  # Hotkey for autorun
                    is_autorun = True
                time.sleep(0.2)
                if self.mode == 'patrol':
                    if distance_delta > self.max_patrol_distance:
                        self.state_overall = OverallState.RETURNING
                        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F1)  # Hotkey for targeting self, acting as a deselect
                        if is_autorun:
                            keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))  # Hotkey for autorun
                            is_autorun = False

            elif self.state_overall == OverallState.ATTACKING:
                if not self.is_target_selected:
                    self.state_overall = OverallState.ACQUIRING
                    acquiring_timestamp = time.time()
                    continue
                if self.distance_to_target > self.max_distance_to_target:
                    self.state_overall = OverallState.APPROACHING
                    continue
                self.attack()
                if self.mode == 'patrol':
                    if distance_delta > self.max_patrol_distance:
                        self.state_overall = OverallState.RETURNING
                        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F1)  # Hotkey for targeting self, acting as a deselect

    def record(self, interval='0.1'):
        coordinates = []
        try:
            while True:
                self.scan()
                coordinates.append((self.x, self.y, self.z))
                time.sleep(interval)
        except KeyboardInterrupt:
            filename = 'recording%s.json' % (int(time.time() * 1000))
            with open(filename, 'w') as f:
                print('Writing %s waypoints to %s' % (len(coordinates), filename))
                f.write(json.dumps(coordinates))
