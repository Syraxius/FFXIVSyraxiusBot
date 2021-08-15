import gevent
from gevent import monkey
monkey.patch_all()

import enum
import json
import math
import random
import time

import win32api
import win32con

from botlib.control import keyboard_send_vk_as_scan_code
from botlib.memory import get_winlist, get_hwnd, get_hwnd_base_address, open_process_vm_read_handle, close_process_vm_read_handle, get_memory_value, get_multiple_memory_values
from waypointlib.routing import get_euclidean_distance, WaypointRouter

address_descriptions = {
    'own_pointer': {  # This is the pointer to self game object
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'target_pointer': {  # This is the pointer to target game object (TargetSystem->Target)
        'base_address_offset': 0x01DB8140,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'teammate1_pointer': {  # This is the pointer to first teammate (usually self)
        'base_address_offset': 0x1DDFB60,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'teammate2_pointer': {  # This is the pointer to second teammate
        'base_address_offset': 0x1DDFB68,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'teammate3_pointer': {  # This is the pointer to third teammate
        'base_address_offset': 0x1DDFB70,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'teammate4_pointer': {  # This is the pointer to fourth teammate
        'base_address_offset': 0x1DDFB78,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'map_id': {
        'base_address_offset': 0x01DB7F24,  # Search 13 at Steps of Nald is 13, and 20 at Western Thanalan
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'is_moving': {  # Search 0 when not autorun, and 1 when autorun
        'base_address_offset': 0x01DB7F70,
        'pointer_offsets': (0x18C,),
        'datatype': 'integer',
    },

    'is_waiting_for_duty': {  # Search 1 when waiting for duty, and 0 when not
        'base_address_offset': 0x01DF3D5C,
        'pointer_offsets': (),
        'datatype': 'byte',
    },

    'is_duty_found_window': {  # Search "ui/uld/NotificationItem.uld" after duty notification pops up, and "ui/uld/JournalDetail.uld" after opening inventory
        'base_address_offset': 0x01DBC560,
        'pointer_offsets': (),
        'datatype': 'string',
        'length': 32,
    },

    'is_cutscene': {  # Search 0 when not in cutscene (e.g. in dungeon cutscene), and 1 when in cutscene
        'base_address_offset': 0x01D69F68,
        'pointer_offsets': (),
        'datatype': 'integer',
    },
}

game_object_fields = {
    'name': {
        'pointer_offsets': (0x30,),
        'datatype': 'string',
        'length': 64
    },

    'object_id': {
        'pointer_offsets': (0x74,),
        'datatype': 'integer',
    },

    'object_kind': {
        'pointer_offsets': (0x8C,),
        'datatype': 'byte',
    },

    'sub_kind': {
        'pointer_offsets': (0x8D,),
        'datatype': 'byte',
    },

    'distance_xy': {
        'pointer_offsets': (0x90,),
        'datatype': 'byte',
    },

    'distance_z': {
        'pointer_offsets': (0x92,),
        'datatype': 'byte',
    },

    'x': {
        'pointer_offsets': (0xA0,),
        'datatype': 'float',
    },

    'y': {
        'pointer_offsets': (0xA8,),
        'datatype': 'float',
    },

    'z': {
        'pointer_offsets': (0xA4,),
        'datatype': 'float',
    },

    'game_rotation': {
        'pointer_offsets': (0xB0,),
        'datatype': 'float',
    },
}

battle_character_fields = {
    'hp': {
        'pointer_offsets': (0x1C4,),
        'datatype': 'integer',
    },

    'hp_max': {
        'pointer_offsets': (0x1C8,),
        'datatype': 'integer',
    },

    'mp': {
        'pointer_offsets': (0x1CC,),
        'datatype': 'integer',
    },

    'mp_max': {
        'pointer_offsets': (0x1D0,),
        'datatype': 'integer',
    },

    'class_job': {
        'pointer_offsets': (0x1E2,),
        'datatype': 'byte',
    },

    'level': {
        'pointer_offsets': (0x1E3,),
        'datatype': 'byte',
    },

    'name_id': {
        'pointer_offsets': (0x1940,),
        'datatype': 'integer',
    },

    'is_casting': {
        'pointer_offsets': (0x1B80+0x00,),
        'datatype': 'byte',
    },

    'curr_cast_time': {
        'pointer_offsets': (0x1B80+0x34,),
        'datatype': 'float',
    },

    'total_cast_time': {
        'pointer_offsets': (0x1B80+0x38,),
        'datatype': 'float',
    },
}


def game_to_normal_rotation(game_rotation):
    # Before: +-0 is south. +-pi is north.  pi/2 is east. -pi/2 is west.
    # After: +-0 is east. +pi/2 is north.  +pi is west. +pi*3/2 is south.
    if 0 <= game_rotation < math.pi / 2:
        return game_rotation + math.pi * 3 / 2
    elif math.pi / 2 <= game_rotation < math.pi:
        return game_rotation - math.pi * 1 / 2
    elif -math.pi <= game_rotation < -math.pi / 2:
        return game_rotation + math.pi * 3 / 2
    elif -math.pi / 2 <= game_rotation < 0:
        return game_rotation + math.pi * 3 / 2


def build_game_object(hwnd, base_address, base_address_offset):
    game_object = get_multiple_memory_values(hwnd, base_address, base_address_offset, game_object_fields)

    # Update helper information
    game_object['rotation'] = game_to_normal_rotation(game_object['game_rotation'])
    game_object['is_player_character'] = game_object['object_kind'] == 1
    game_object['is_battle_npc'] = game_object['object_kind'] == 2
    game_object['is_exit'] = game_object['name'] == b'Exit'

    # Update character information
    if game_object['object_kind'] in [1, 2]:
        game_object.update(get_multiple_memory_values(hwnd, base_address, base_address_offset, battle_character_fields))
        game_object['is_damaged'] = game_object['hp'] != game_object['hp_max']

    return game_object


class AssistState(enum.Enum):
    ACQUIRING_ENEMY = 1
    NAVIGATING_ENEMY = 2
    ATTACKING = 3


class DungeonState(enum.Enum):
    NAVIGATING_DUNGEON = 1
    EXITING_DUNGEON = 2
    TOGGLING_TEAMMATE = 3
    SELECTING_TEAMMATE = 4
    CHECKING_TEAMMATE = 5
    NAVIGATING_TO_TEAMMATE = 6
    SELECTING_ENEMY = 7
    CHECKING_ENEMY = 8
    ATTACKING = 9


class DungeonTeammateState(enum.Enum):
    TANK = 0
    DPS = 1


class Bot:
    def __init__(self, attack=None, mode='assist', dungeon_config=None, navigation_config=None):
        winlist = get_winlist()
        self.hwnd = get_hwnd('FINAL FANTASY XIV', winlist)
        self.base_address = get_hwnd_base_address(self.hwnd)

        self.last_message = ''

        self.own = None
        self.target_acquired = False
        self.target = None
        self.teammate1_acquired = False
        self.teammate1 = False
        self.teammate2_acquired = False
        self.teammate2 = False
        self.teammate3_acquired = False
        self.teammate3 = False
        self.teammate4_acquired = False
        self.teammate4 = False
        self.map_id = 0
        self.is_moving = False
        self.is_waiting_for_duty = False
        self.is_duty_found_window = False
        self.is_cutscene = False
        self.scan()
        self.init_x = self.own['x']
        self.init_y = self.own['y']
        self.init_z = self.own['z']

        self.shortest_path = []
        self.curr_node = None
        self.prev_node = None
        self.prev_distance_delta = None
        self.target_coordinate = None
        self.w = None
        if dungeon_config:
            self.navigation_target_coordinate = dungeon_config['exit_coordinate']
            self.navigation_map_id = dungeon_config['map_id']
        if navigation_config and navigation_config['recordings']:
            self.w = WaypointRouter(navigation_config['recordings'], custom_cache_name=navigation_config['custom_cache_name'])
        else:
            self.w = WaypointRouter()
            self.w.load_adjacency_list('caches/autolearn_%s.cache' % self.map_id)

        self.mode = mode  # 'assist', 'dungeon'
        self.state_overall = None
        self.state_attack = None
        self.prev_state_attack = None
        self.attack = attack
        self.curr_skill = None
        self.curr_cast_time = None
        self.total_cast_time = None
        self.cast_attempt_timestamp = None
        self.prev_enemy_object_id = None

        self.max_distance_to_teammate = 5
        self.max_distance_to_target_low = 10
        self.max_distance_to_target_high = 20

        self.stop = False
        self.workers = []
        self.bot_worker = None
        self.recording_worker = None
        self.learning_worker = None

    def debounced_print(self, message):
        if self.last_message != message:
            print(message)
        self.last_message = message

    def scan(self):
        handle = open_process_vm_read_handle(self.hwnd)

        # Build own game object
        self.own = build_game_object(self.hwnd, self.base_address, address_descriptions['teammate1_pointer']['base_address_offset'])

        # Build target game object
        self.target_acquired = get_memory_value(self.hwnd, self.base_address, address_descriptions['target_pointer'])
        if self.target_acquired:
            self.target = build_game_object(self.hwnd, self.base_address, address_descriptions['target_pointer']['base_address_offset'])
        else:
            self.target = None

        # Query additional data
        self.map_id = get_memory_value(self.hwnd, self.base_address, address_descriptions['map_id'], external_handle=handle)
        self.is_moving = get_memory_value(self.hwnd, self.base_address, address_descriptions['is_moving'], external_handle=handle)
        self.is_cutscene = get_memory_value(self.hwnd, self.base_address, address_descriptions['is_cutscene'], external_handle=handle)
        self.is_waiting_for_duty = get_memory_value(self.hwnd, self.base_address, address_descriptions['is_waiting_for_duty'], external_handle=handle) == 1
        self.is_duty_found_window = get_memory_value(self.hwnd, self.base_address, address_descriptions['is_duty_found_window'], external_handle=handle) == b'ui/uld/NotificationItem.uld'

        close_process_vm_read_handle(handle)

    def scan_coordinates(self):
        handle = open_process_vm_read_handle(self.hwnd)

        self.map_id = get_memory_value(self.hwnd, self.base_address, address_descriptions['map_id'], external_handle=handle)

        self.teammate1_acquired = get_memory_value(self.hwnd, self.base_address, address_descriptions['teammate1_pointer'])
        if self.teammate1_acquired:
            self.teammate1 = build_game_object(self.hwnd, self.base_address, address_descriptions['teammate1_pointer']['base_address_offset'])
        else:
            self.teammate1 = None

        self.teammate2_acquired = get_memory_value(self.hwnd, self.base_address, address_descriptions['teammate2_pointer'])
        if self.teammate2_acquired:
            self.teammate2 = build_game_object(self.hwnd, self.base_address, address_descriptions['teammate2_pointer']['base_address_offset'])
        else:
            self.teammate2 = None

        self.teammate3_acquired = get_memory_value(self.hwnd, self.base_address, address_descriptions['teammate3_pointer'])
        if self.teammate3_acquired:
            self.teammate3 = build_game_object(self.hwnd, self.base_address, address_descriptions['teammate3_pointer']['base_address_offset'])
        else:
            self.teammate3 = None

        self.teammate4_acquired = get_memory_value(self.hwnd, self.base_address, address_descriptions['teammate4_pointer'])
        if self.teammate4_acquired:
            self.teammate4 = build_game_object(self.hwnd, self.base_address, address_descriptions['teammate4_pointer']['base_address_offset'])
        else:
            self.teammate4 = None

        close_process_vm_read_handle(handle)

    def get_own_coordinate(self):
        return [self.own['x'], self.own['y'], self.own['z']]

    def get_current_direction(self):
        return self.own['rotation']

    def get_target_direction(self, target_x, target_y):
        direction_x = target_x - self.own['x']
        direction_y = -(target_y - self.own['y'])
        target_direction = math.atan2(direction_y, direction_x)
        if target_direction < 0:
            target_direction = target_direction + 2 * math.pi
        return target_direction

    def ensure_walking_state(self, is_walking):
        if is_walking:
            if not self.is_moving:
                keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))
        elif not is_walking:
            if self.is_moving:
                keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))

    def get_turn_duration(self, radians, ensure_nonnegative=True):
        # Delta Radians = 2.4 * Turn Duration + 0.055
        turn_speed = 2.4  # rad/s
        turn_min_amount = 0.055  # rad
        turn_duration = (abs(radians) - turn_min_amount) / turn_speed
        if ensure_nonnegative:
            if turn_duration < 0:
                turn_duration = 0
        return turn_duration

    def turn_by_radians(self, direction, radians, ensure_minimum=True):
        turn_duration = self.get_turn_duration(radians, ensure_nonnegative=False)
        if ensure_minimum:
            if turn_duration < 0:
                return
        self.turn_by_duration(direction, turn_duration)

    def turn_by_duration(self, direction, turn_duration):
        if turn_duration > 0.3:
            self.ensure_walking_state(False)
        if direction == 'left':
            keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('a', 0), action='hold', duration=turn_duration)
        elif direction == 'right':
            keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('d', 0), action='hold', duration=turn_duration)

    def calculate_final_direction(self, target_direction, current_direction):
        provisional_direction = target_direction - current_direction
        if -math.pi < provisional_direction < math.pi:
            final_direction = provisional_direction
        elif math.pi < provisional_direction:
            final_direction = provisional_direction - 2 * math.pi
        else:
            final_direction = provisional_direction + 2 * math.pi
        return final_direction

    def calculate_navigation(self, target_x, target_y):
        distance_delta = get_euclidean_distance([self.own['x'], self.own['y'], 0], [target_x, target_y, 0])
        current_direction = self.get_current_direction()
        target_direction = self.get_target_direction(target_x, target_y)
        final_direction = self.calculate_final_direction(target_direction, current_direction)
        is_turn_left = final_direction > 0
        direction_delta = abs(final_direction)
        return distance_delta, direction_delta, is_turn_left

    def turn_to_target(self, target_x, target_y):
        distance_delta, direction_delta, is_turn_left = self.calculate_navigation(target_x, target_y)
        if is_turn_left:
            self.turn_by_radians('left', direction_delta)
        else:
            self.turn_by_radians('right', direction_delta)

    def change_state_attack(self, state_attack):
        self.prev_state_attack = self.state_attack
        self.state_attack = state_attack

    def confirm_state_attack(self):
        self.prev_state_attack = None

    def rollback_state_attack(self):
        if self.prev_state_attack:
            self.state_attack = self.prev_state_attack
            self.prev_state_attack = None

    def cast(self, skill_name, silent=False):
        if not silent:
            print('Using %s' % skill_name)
        skill = self.skills[skill_name]
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx(str(skill['button']), 0))
        if skill['delay'] > 0:
            self.curr_skill = skill_name
            self.set_cast_attempt()

    def set_cast_time(self):
        self.total_cast_time = self.own['total_cast_time']
        self.curr_cast_time = self.own['curr_cast_time']

    def clear_cast_time(self):
        self.total_cast_time = None
        self.curr_cast_time = None

    def get_cast_time_done(self):
        if self.total_cast_time and self.curr_cast_time:
            return self.total_cast_time - self.curr_cast_time < 0.2
        else:
            return True

    def get_cast_failed(self):
        return not self.own['is_casting'] and not self.get_cast_time_done()

    def set_cast_attempt(self):
        if not self.cast_attempt_timestamp:
            self.cast_attempt_timestamp = time.time()

    def clear_cast_attempt(self):
        self.cast_attempt_timestamp = None

    def get_cast_attempt_expired(self, timeout=1):
        if self.cast_attempt_timestamp:
            return time.time() - self.cast_attempt_timestamp > timeout
        else:
            return False

    def set_skill_cooldown(self, skill, cooldown):
        self.skill_timestamp[skill] = (time.time(), cooldown)

    def get_skill_cooldown_remaining(self, skill):
        skill_timestamp, cooldown = self.skill_timestamp.get(skill, (0, 0))
        return max(0, cooldown - (time.time() - skill_timestamp))

    def get_skill_is_cooldown(self, skill):
        return self.get_skill_cooldown_remaining(skill) <= 0

    def get_nearest_enemy(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F11)  # Hotkey for targeting nearest enemy (in view)

    def get_tank(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F2)  # Hotkey for targeting tank member

    def get_healer(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F3)  # Hotkey for targeting healer member

    def get_dps(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F4)  # Hotkey for targeting DPS member

    def get_teammate(self):
        if random.random() > 0.5:
            self.get_tank()
        else:
            self.get_dps()

    def get_tank_target(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F2)  # Hotkey for targeting tank member
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('t', 0))

    def get_healer_target(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F3)  # Hotkey for targeting healer member
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('t', 0))

    def get_dps_target(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F4)  # Hotkey for targeting DPS member
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('t', 0))

    def get_teammate_target(self):
        if random.random() > 0.5:
            self.get_tank_target()
        else:
            self.get_dps_target()

    def cancel(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_ESCAPE)

    def use_nearest_npc_or_object(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F12)  # Hotkey for targeting nearest NPC or object
        time.sleep(0.1)
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_NUMPAD0)  # Hotkey for selecting confirm
        time.sleep(0.1)
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_NUMPAD0)  # Hotkey for selecting confirm

    def skip_cutscene(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_ESCAPE)  # Hotkey for opening skip menu
        time.sleep(0.1)
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_NUMPAD0)  # Hotkey for selecting confirm
        time.sleep(0.1)
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_NUMPAD0)  # Hotkey for confirming

    def accept_duty(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_NUMPAD4)  # Hotkey for selecting middle
        time.sleep(0.1)
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_NUMPAD4)  # Hotkey for selecting Commence
        time.sleep(0.1)
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_NUMPAD0)  # Hotkey for confirming

    def cancel_routing_target(self, continue_walking=False):
        if not self.w:
            return
        self.shortest_path = []
        self.curr_node = None
        self.prev_node = None
        self.target_coordinate = None
        self.prev_distance_delta = None
        if not continue_walking:
            self.ensure_walking_state(False)

    def init_routing_target(self, target_coordinate, continue_walking=False):
        if not self.w:
            return
        self.cancel_routing_target(continue_walking=continue_walking)
        self.target_coordinate = target_coordinate
        a = self.get_own_coordinate()
        b = target_coordinate
        self.shortest_path = self.w.get_shortest_path_coordinates(a, b)

    def walk_to_routing_target(self, target_coordinate=None, reinit_if_empty=True, reinit_if_different=False):
        if reinit_if_different:
            if self.target_coordinate != target_coordinate:
                self.init_routing_target(target_coordinate)
        if self.curr_node is None:
            if len(self.shortest_path) == 0:
                if reinit_if_empty and target_coordinate:
                    # Forward projection if already walking, to ensure that the waypoint is more likely in front of the character
                    delta_x = 0
                    delta_y = 0
                    if self.is_moving:
                        current_direction = self.get_current_direction()
                        delta_x = 3 * math.cos(current_direction)
                        delta_y = -(3 * math.sin(current_direction))
                    self.init_routing_target([target_coordinate[0] + delta_x, target_coordinate[1] + delta_y], continue_walking=True)
                else:
                    self.ensure_walking_state(False)
                    return False
            if len(self.shortest_path) == 0:
                return False
            self.curr_node = self.shortest_path.pop(0)
            self.prev_distance_delta = None
        distance_delta, direction_delta, is_turn_left = self.calculate_navigation(self.curr_node.coordinate[0], self.curr_node.coordinate[1])
        if self.prev_distance_delta:
            if self.prev_distance_delta - distance_delta < 0.01 and self.is_moving == 1:
                self.debounced_print('STUCK!!!')
                if self.prev_node:
                    self.debounced_print('Unlinking %s from %s' % (self.prev_node.index, self.curr_node.index))
                    self.prev_node.unlink_from(self.curr_node)
                    self.shortest_path = self.w.get_shortest_path_coordinates(self.prev_node.coordinate, self.target_coordinate)
                else:
                    self.shortest_path = self.w.get_shortest_path_coordinates(self.get_own_coordinate(), self.target_coordinate)
                self.curr_node = None
                self.prev_node = None
                return True
        self.prev_distance_delta = distance_delta
        if distance_delta < 1:
            self.curr_node = None
            self.prev_node = self.curr_node
        else:
            self.turn_to_target(self.curr_node.coordinate[0], self.curr_node.coordinate[1])
            self.ensure_walking_state(True)
        time.sleep(0.05)
        return True

    def start(self):
        if self.mode == 'assist':
            self.state_overall = AssistState.ACQUIRING_ENEMY
            self.start_assist(autotarget=False, autoapproach=False)
        elif self.mode == 'assist_autotarget':
            self.state_overall = AssistState.ACQUIRING_ENEMY
            self.start_assist(autotarget=True, autoapproach=False)
        elif self.mode == 'assist_autotarget_autoapproach':
            self.state_overall = AssistState.ACQUIRING_ENEMY
            self.start_assist(autotarget=True, autoapproach=True)
        elif self.mode == 'assist_autoapproach':
            self.state_overall = AssistState.ACQUIRING_ENEMY
            self.start_assist(autotarget=False, autoapproach=True)
        elif self.mode == 'dungeon':
            self.state_overall = DungeonState.SELECTING_TEAMMATE
            self.start_dungeon()

    def start_assist(self, autotarget=False, autoapproach=False):
        last_state = None
        while not self.stop:
            self.scan()

            if self.state_overall != last_state:
                print(self.state_overall)
            last_state = self.state_overall

            if self.state_overall == AssistState.ACQUIRING_ENEMY:
                if self.target_acquired:
                    self.debounced_print('Selection acquired. Navigating to enemy')
                    self.state_overall = AssistState.NAVIGATING_ENEMY
                    continue
                if autotarget:
                    self.debounced_print('No selection. Attempting to select enemy')
                    self.get_nearest_enemy()
                time.sleep(0.1)

            elif self.state_overall == AssistState.NAVIGATING_ENEMY:
                if not self.target_acquired:
                    self.debounced_print('No selection. Attempting to acquire enemy')
                    if autoapproach:
                        self.ensure_walking_state(False)
                    self.state_overall = AssistState.ACQUIRING_ENEMY
                    continue
                if self.target['distance_xy'] < self.max_distance_to_target_high:
                    self.debounced_print('Enemy in range. Attempting to attack')
                    if autoapproach:
                        self.ensure_walking_state(False)
                    self.state_overall = AssistState.ATTACKING
                    continue
                if autoapproach:
                    self.debounced_print('Enemy out of range range. Attempting to approach enemy')
                    self.turn_to_target(self.target['x'], self.target['y'])
                    self.ensure_walking_state(True)
                time.sleep(0.1)

            elif self.state_overall == AssistState.ATTACKING:
                if not self.target_acquired:
                    self.debounced_print('No selection. Attempting to acquire enemy')
                    self.state_overall = AssistState.ACQUIRING_ENEMY
                    continue
                if self.target['distance_xy'] > self.max_distance_to_target_high:
                    self.debounced_print('Enemy out of range. Attempting to acquire enemy')
                    self.state_overall = AssistState.ACQUIRING_ENEMY
                    continue
                if self.is_moving:
                    self.debounced_print('Still moving, waiting for stop')
                    time.sleep(0.1)
                    continue
                if self.own['is_casting'] == 1 and self.target['is_battle_npc'] and self.prev_enemy_object_id != self.target['object_id']:
                    self.cancel()
                    time.sleep(0.05)
                    continue
                if self.own['is_casting'] == 1:
                    self.clear_cast_attempt()
                    self.set_cast_time()
                    time.sleep(0.05)
                    continue
                self.prev_enemy_object_id = self.target['object_id']
                if self.get_cast_attempt_expired():
                    self.debounced_print('Cast attempt expired. Attempting to acquire enemy')
                    self.rollback_state_attack()
                    self.clear_cast_time()
                    self.clear_cast_attempt()
                    self.state_overall = AssistState.ACQUIRING_ENEMY
                    continue
                if self.get_cast_failed():
                    self.debounced_print('Cast interrupted. Attempting to acquire enemy')
                    self.rollback_state_attack()
                    self.clear_cast_time()
                    self.clear_cast_attempt()
                    self.state_overall = AssistState.ACQUIRING_ENEMY
                    continue
                if self.cast_attempt_timestamp:
                    if self.curr_skill:
                        self.cast(self.curr_skill, silent=True)
                    continue
                self.debounced_print('Enemy in range. Attacking!')
                self.confirm_state_attack()
                self.attack()

    def start_dungeon(self):
        teammate_state = DungeonTeammateState.TANK
        last_state = None
        while not self.stop:
            self.scan()

            if self.map_id != self.navigation_map_id:
                self.debounced_print('Map ID %s does not match expected %s, waiting.' % (self.map_id, self.navigation_map_id))
                self.state_overall = DungeonState.SELECTING_ENEMY
                teammate_state = DungeonTeammateState.TANK
                self.cancel_routing_target()
                if self.is_duty_found_window:
                    time.sleep(1)
                    self.accept_duty()
                    time.sleep(1)
                time.sleep(1)
                continue

            if self.is_cutscene:
                time.sleep(5)
                self.skip_cutscene()
                time.sleep(5)
                continue

            if self.state_overall != last_state:
                print(self.state_overall)
            last_state = self.state_overall

            if self.state_overall == DungeonState.NAVIGATING_DUNGEON:
                is_continue_walking = self.walk_to_routing_target(self.navigation_target_coordinate, reinit_if_empty=False, reinit_if_different=True)
                if not is_continue_walking:
                    self.debounced_print('Reached end of dungeon!')
                    self.state_overall = DungeonState.EXITING_DUNGEON
                    continue
                self.state_overall = DungeonState.TOGGLING_TEAMMATE

            elif self.state_overall == DungeonState.EXITING_DUNGEON:
                self.walk_to_routing_target(self.navigation_target_coordinate, reinit_if_empty=False, reinit_if_different=True)
                self.use_nearest_npc_or_object()

            elif self.state_overall == DungeonState.TOGGLING_TEAMMATE:
                if teammate_state == DungeonTeammateState.TANK:
                    teammate_state = DungeonTeammateState.DPS
                else:
                    teammate_state = DungeonTeammateState.TANK
                self.state_overall = DungeonState.SELECTING_TEAMMATE

            elif self.state_overall == DungeonState.SELECTING_TEAMMATE:
                if teammate_state == DungeonTeammateState.TANK:
                    self.get_tank()
                else:
                    self.get_dps()
                self.state_overall = DungeonState.CHECKING_TEAMMATE
                time.sleep(0.05)

            elif self.state_overall == DungeonState.CHECKING_TEAMMATE:
                if not self.target_acquired:
                    self.debounced_print('No selection. Attempting to navigate dungeon')
                    self.state_overall = DungeonState.NAVIGATING_DUNGEON
                    continue
                if not self.target['is_player_character']:
                    self.debounced_print('Non-player selected. Attempting to navigate dungeon')
                    self.state_overall = DungeonState.NAVIGATING_DUNGEON
                    continue
                self.debounced_print('Teammate selected. Attempting to navigate to teammate')
                self.cancel_routing_target()  # Need to cancel routing when entering dynamic waypoint
                self.state_overall = DungeonState.NAVIGATING_TO_TEAMMATE

            elif self.state_overall == DungeonState.NAVIGATING_TO_TEAMMATE:
                if not self.target_acquired:
                    self.debounced_print('No selection. Attempting to select teammate')
                    self.cancel_routing_target()
                    self.state_overall = DungeonState.TOGGLING_TEAMMATE
                    continue
                if not self.target['is_player_character']:
                    self.debounced_print('Non-player selected. Attempting to select teammate')
                    self.state_overall = DungeonState.SELECTING_TEAMMATE
                    continue
                if self.target['distance_xy'] < self.max_distance_to_teammate:
                    self.debounced_print('Teammate in range. Attempting to select enemy')
                    self.cancel_routing_target()
                    self.state_overall = DungeonState.SELECTING_ENEMY
                    continue
                self.debounced_print('Navigating to teammate')
                self.walk_to_routing_target([self.target['x'], self.target['y']], reinit_if_empty=True, reinit_if_different=False)

            elif self.state_overall == DungeonState.SELECTING_ENEMY:
                if teammate_state == DungeonTeammateState.TANK:
                    self.get_tank_target()
                else:
                    self.get_dps_target()
                self.state_overall = DungeonState.CHECKING_ENEMY
                time.sleep(0.05)

            elif self.state_overall == DungeonState.CHECKING_ENEMY:
                if not self.target_acquired:
                    self.debounced_print('No selection. Attempting to select teammate')
                    self.state_overall = DungeonState.TOGGLING_TEAMMATE
                    continue
                if self.target['is_exit']:
                    self.debounced_print('Selection is exit. Attempting to exit!')
                    self.state_overall = DungeonState.EXITING_DUNGEON
                    continue
                if not (self.target['is_battle_npc'] and self.target['is_damaged']):
                    self.debounced_print('Selection is not a damaged enemy. Attempting to select teammate')
                    self.state_overall = DungeonState.TOGGLING_TEAMMATE
                    continue
                if self.target['distance_xy'] > self.max_distance_to_target_high:
                    self.debounced_print('Enemy out of range. Attempting to select teammate')
                    self.state_overall = DungeonState.SELECTING_TEAMMATE
                    continue
                self.debounced_print('Enemy in range. Attempting to attack enemy')
                self.state_overall = DungeonState.ATTACKING

            elif self.state_overall == DungeonState.ATTACKING:
                if not self.target_acquired:
                    self.debounced_print('No selection. Attempting to select enemy')
                    self.clear_cast_time()
                    self.clear_cast_attempt()
                    self.state_overall = DungeonState.SELECTING_ENEMY
                    continue
                if not (self.target['is_battle_npc'] and self.target['is_damaged']):
                    self.debounced_print('Selection is not a damaged enemy. Attempting to select enemy')
                    self.clear_cast_time()
                    self.clear_cast_attempt()
                    self.state_overall = DungeonState.SELECTING_ENEMY
                    continue
                if self.target['distance_xy'] > self.max_distance_to_target_high:
                    self.debounced_print('Enemy out of range. Attempting to select enemy')
                    self.clear_cast_time()
                    self.clear_cast_attempt()
                    self.state_overall = DungeonState.SELECTING_ENEMY
                    continue
                if self.own['is_casting'] == 1 and self.target['is_battle_npc'] and self.prev_enemy_object_id != self.target['object_id']:
                    self.cancel()
                    time.sleep(0.05)
                    continue
                if self.own['is_casting'] == 1:
                    self.clear_cast_attempt()
                    self.set_cast_time()
                    time.sleep(0.05)
                    continue
                self.prev_enemy_object_id = self.target['object_id']
                if self.get_cast_attempt_expired():
                    self.debounced_print('Cast attempt expired. Attempting to select teammate')
                    self.rollback_state_attack()
                    self.clear_cast_time()
                    self.clear_cast_attempt()
                    self.state_overall = DungeonState.TOGGLING_TEAMMATE
                    continue
                if self.get_cast_failed():
                    self.debounced_print('Cast interrupted. Attempting to acquire enemy')
                    self.rollback_state_attack()
                    self.clear_cast_time()
                    self.clear_cast_attempt()
                    self.state_overall = DungeonState.SELECTING_ENEMY
                    continue
                if self.cast_attempt_timestamp:
                    if self.curr_skill:
                        self.cast(self.curr_skill, silent=True)
                    continue
                self.debounced_print('Enemy in range. Attacking!')
                self.confirm_state_attack()
                self.attack()
                if self.target['name_id'] == 73:  # Galvanth the dominator
                    self.debounced_print('Galvanth detected. Attempting to select DPS target')
                    teammate_state = DungeonTeammateState.DPS
                    self.state_overall = DungeonState.SELECTING_ENEMY

    def record(self, interval=0.1):
        print('Recording!')
        coordinates = []
        while not self.stop:
            self.scan_coordinates()
            if coordinates and get_euclidean_distance(coordinates[-1], self.get_own_coordinate()) > 1:
                coordinates.append(self.get_own_coordinate())
            else:
                coordinates.append(self.get_own_coordinate())
            time.sleep(interval)
        filename = 'recording%s.json' % (int(time.time() * 1000))
        with open(filename, 'w') as f:
            print('Writing %s waypoints to %s' % (len(coordinates), filename))
            f.write(json.dumps(coordinates))

    def learn(self, interval=0.1):
        print('Learning!')
        self.w.load_adjacency_list('caches/autolearn_%s.cache' % self.map_id)
        prev_map_id = self.map_id
        while not self.stop:
            self.scan_coordinates()

            if prev_map_id != self.map_id:
                print('Map change detected: %s -> %s' % (prev_map_id, self.map_id))
                self.w.save_adjacency_list('caches/autolearn_%s.cache' % prev_map_id)
                self.w.load_adjacency_list('caches/autolearn_%s.cache' % self.map_id)
                prev_map_id = self.map_id
                continue

            new_nodes = []
            node = self.w.add_to_adjacency_list(self.get_own_coordinate(), can_add_unconnected=True)
            if node:
                new_nodes.append(node)
            if self.teammate2_acquired:
                node = self.w.add_to_adjacency_list([self.teammate2['x'], self.teammate2['y'], self.teammate2['z']], can_add_unconnected=True)
                if node:
                    new_nodes.append(node)
            if self.teammate3_acquired:
                node = self.w.add_to_adjacency_list([self.teammate3['x'], self.teammate3['y'], self.teammate3['z']], can_add_unconnected=True)
                if node:
                    new_nodes.append(node)
            if self.teammate4_acquired:
                node = self.w.add_to_adjacency_list([self.teammate4['x'], self.teammate4['y'], self.teammate4['z']], can_add_unconnected=True)
                if node:
                    new_nodes.append(node)
            if new_nodes:
                print('%s new nodes learned, total nodes %s' % (len(new_nodes), len(self.w.adjacency_list)))
            time.sleep(interval)

        self.w.save_adjacency_list('caches/autolearn_%s.cache' % self.map_id)

    def start_asynchronous(self):
        if not self.bot_worker:
            self.bot_worker = gevent.spawn(self.start)
            self.bot_worker.start()
            self.workers.append(self.bot_worker)
        print('Bot worker started!')

    def record_asynchronous(self, interval=0.1):
        if not self.recording_worker:
            self.recording_worker = gevent.spawn(self.record, interval=interval)
            self.recording_worker.start()
            self.workers.append(self.recording_worker)
        print('Record worker started!')

    def learn_asynchronous(self, interval=0.1):
        if not self.learning_worker:
            self.learning_worker = gevent.spawn(self.learn, interval=interval)
            self.learning_worker.start()
            self.workers.append(self.learning_worker)
        print('Learn worker started!')

    def stop_all(self):
        self.stop = True
        print('Stopped all workers gracefully')

    def joinall(self):
        gevent.joinall(self.workers)
