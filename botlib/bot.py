import enum
import json
import math
import random
import time

import win32api
import win32con

from botlib.control import keyboard_send_vk_as_scan_code
from botlib.memory import get_winlist, get_hwnd, get_hwnd_base_address, get_memory_values
from waypointlib.routing import get_euclidean_distance, WaypointRouter

address_descriptions = {
    'mp': {  # Search MP directly
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (0x1CC,),
        'datatype': 'integer',
    },

    'level': {  # Search level directly, then search again after level sync
        'base_address_offset': 0x1DE3640,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'selection_dx': {  # Get selection_dy then subtract 8
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (0x360,),
        'datatype': 'float',
    },

    'selection_dy': {  # Get selection_dz then subtract 8
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (0x368,),
        'datatype': 'float',
    },

    'selection_dz': {  # Get selection_distance then subtract 8
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (0x370,),
        'datatype': 'float',
    },

    'selection_distance': {  # Search increase/decrease with a target selected
        'base_address_offset': 0x01DB8210,
        'pointer_offsets': (0x378,),
        'datatype': 'float',
    },

    'selection_acquired': {  # Use the pointer for selection_hp
        'base_address_offset': 0x01DB8140,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'selection_hp': {  # Search unknown initial, then search decreased bv damaged amount
        'base_address_offset': 0x01DB8140,
        'pointer_offsets': (0x1C4,),
        'datatype': 'integer',
    },

    'selection_max_hp': {  # Get selection_hp then add 4
        'base_address_offset': 0x01DB8140,
        'pointer_offsets': (0x1C8,),
        'datatype': 'integer',
    },

    'selection_mp': {  # Get selection_max_hp then add 4
        'base_address_offset': 0x01DB8140,
        'pointer_offsets': (0x1CC,),
        'datatype': 'integer',
    },

    'selection_max_mp': {  # Get selection_mp then add 4
        'base_address_offset': 0x01DB8140,
        'pointer_offsets': (0x1D0,),
        'datatype': 'integer',
    },

    'selection_npc_id': {  # Search for # in BNpcName around the address range pointed by the base pointer.
        'base_address_offset': 0x01DB8140,
        'pointer_offsets': (0x1940,),
        'datatype': 'integer',
    },

    'x': {  # Search increased when walking to east, and decreased when walking to west
        'base_address_offset': 0x1DBBFD0,
        'pointer_offsets': (),
        'datatype': 'float',
    },

    'y': {  # Search increased when walking to south, and decreased when walking to north
        'base_address_offset': 0x1DBBFD8,
        'pointer_offsets': (),
        'datatype': 'float',
    },

    'z': {  # Get y then add 8
        'base_address_offset': 0x1DBBFE0,
        'pointer_offsets': (),
        'datatype': 'float',
    },

    'x_complex': {  # East is close to 1.0, West is close to -1.0
        'base_address_offset': 0x01DAF9A8,
        'pointer_offsets': (0x18, 0xD4),
        'datatype': 'float',
    },

    'y_complex': {  # North is close to 1.0, South is close to -1.0
        'base_address_offset': 0x01DAF9A8,
        'pointer_offsets': (0x18, 0xCC),
        'datatype': 'float',
    },

    'map_id': {
        'base_address_offset': 0x1DB7F24,  # Search 13 at Steps of Nald is 13, and 20 at Western Thanalan
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'is_moving': {  # Search 0 when not autorun, and 1 when autorun
        'base_address_offset': 0x01DB7F70,
        'pointer_offsets': (0x18C,),
        'datatype': 'integer',
    },

    'is_duty_found_window': {  # Search 1677747308 when duty found window is closed, and 1684829486 when open
        'base_address_offset': 0x1DBC57C,
        'pointer_offsets': (),
        'datatype': 'integer',
    },

    'is_cutscene': {  # Search 0 when not in cutscene (e.g. in dungeon cutscene), and 1 when in cutscene
        'base_address_offset': 0x1D69F68,
        'pointer_offsets': (),
        'datatype': 'integer',
    },
}


class AssistState(enum.Enum):
    ACQUIRING_ENEMY = 1
    NAVIGATING_ENEMY = 2
    ATTACKING = 3


class DungeonState(enum.Enum):
    NAVIGATING_DUNGEON = 1
    SELECTING_TEAMMATE = 2
    CHECKING_TEAMMATE = 3
    NAVIGATING_TO_TEAMMATE = 4
    SELECTING_ENEMY = 5
    CHECKING_ENEMY = 6
    LINEAR_APPROACHING_TARGET = 7
    ATTACKING = 8
    TOGGLING_TEAMMATE = 9


class DungeonTeammateState(enum.Enum):
    TANK = 0
    DPS = 1


class SelectionType(enum.Enum):
    ENEMY_ENGAGED = 0
    ENEMY_HOSTILE_SELF = 63
    ENEMY_HOSTILE_OTHERS = 64
    ENEMY_IDLE = 79
    NPC_FRIENDLY = 93
    PLAYER_TEAM = 9961552
    PLAYER_OTHERS = 5046330


class Bot:
    def __init__(self, attack=None, mode='assist', navigation_config=None):
        winlist = get_winlist()
        self.hwnd = get_hwnd('FINAL FANTASY XIV', winlist)
        self.base_address = get_hwnd_base_address(self.hwnd)

        self.mp = 0
        self.level = 0
        self.x = 0
        self.y = 0
        self.z = 0
        self.x_complex = 0
        self.y_complex = 0
        self.selection_dx = 0
        self.selection_dy = 0
        self.selection_dz = 0
        self.selection_distance = 0
        self.selection_x = 0
        self.selection_y = 0
        self.selection_z = 0
        self.map_id = 0
        self.selection_acquired = False
        self.selection_hp = 0
        self.selection_max_hp = 0
        self.selection_mp = 0
        self.selection_max_mp = 0
        self.selection_npc_id = 0
        self.is_moving = False
        self.is_cutscene = False
        self.is_duty_found_window = False
        self.scan()
        self.init_x = self.x
        self.init_y = self.y
        self.init_z = self.z

        self.state_overall = None
        self.attack = attack

        self.max_distance_to_teammate = 5
        self.max_distance_to_target = 10
        self.max_distance_to_target_high = 20
        self.mode = mode  # 'assist', 'dungeon'

        self.shortest_path = []
        self.next_coordinate = None
        self.target_coordinate = None
        self.w = None
        if navigation_config:
            self.navigation_target = navigation_config['navigation_target']
            self.navigation_map_id = navigation_config['navigation_map_id']
            self.w = WaypointRouter(navigation_config['recordings'], custom_cache_name=navigation_config['navigation_cache_name'])
            self.init_routing_target(self.navigation_target)

        self.last_message = ''

    def debounced_print(self, message):
        if self.last_message != message:
            print(message)
        self.last_message = message

    def scan(self):
        self.mp = get_memory_values(self.hwnd, 'mp', self.base_address, address_descriptions['mp'])
        self.level = get_memory_values(self.hwnd, 'level', self.base_address, address_descriptions['level'])
        self.x = get_memory_values(self.hwnd, 'x', self.base_address, address_descriptions['x'])
        self.y = get_memory_values(self.hwnd, 'y', self.base_address, address_descriptions['y'])
        self.z = get_memory_values(self.hwnd, 'z', self.base_address, address_descriptions['z'])
        self.x_complex = get_memory_values(self.hwnd, 'x_complex', self.base_address, address_descriptions['x_complex'])
        self.y_complex = get_memory_values(self.hwnd, 'y_complex', self.base_address, address_descriptions['y_complex'])
        self.selection_dx = get_memory_values(self.hwnd, 'selection_dx', self.base_address, address_descriptions['selection_dx'])
        self.selection_dy = get_memory_values(self.hwnd, 'selection_dy', self.base_address, address_descriptions['selection_dy'])
        self.selection_dz = get_memory_values(self.hwnd, 'selection_dz', self.base_address, address_descriptions['selection_dz'])
        self.selection_distance = get_memory_values(self.hwnd, 'selection_distance', self.base_address, address_descriptions['selection_distance'])
        self.selection_x = self.x + self.selection_dx
        self.selection_y = self.y + self.selection_dy
        self.selection_z = self.z + self.selection_dz
        self.map_id = get_memory_values(self.hwnd, 'map_id', self.base_address, address_descriptions['map_id'])
        self.selection_acquired = get_memory_values(self.hwnd, 'selection_acquired', self.base_address, address_descriptions['selection_acquired']) != 0
        self.selection_hp = get_memory_values(self.hwnd, 'selection_hp', self.base_address, address_descriptions['selection_hp'])
        self.selection_max_hp = get_memory_values(self.hwnd, 'selection_max_hp', self.base_address, address_descriptions['selection_max_hp'])
        self.selection_mp = get_memory_values(self.hwnd, 'selection_mp', self.base_address, address_descriptions['selection_mp'])
        self.selection_max_mp = get_memory_values(self.hwnd, 'selection_max_mp', self.base_address, address_descriptions['selection_max_mp'])
        self.selection_npc_id = get_memory_values(self.hwnd, 'selection_npc_id', self.base_address, address_descriptions['selection_npc_id'])
        self.selection_is_enemy = self.selection_max_mp < 10000  # self.selection_npc_id != 0
        self.selection_is_damaged = self.selection_hp != self.selection_max_hp
        self.is_moving = get_memory_values(self.hwnd, 'is_moving', self.base_address, address_descriptions['is_moving'])
        self.is_cutscene = get_memory_values(self.hwnd, 'is_cutscene', self.base_address, address_descriptions['is_cutscene'])
        self.is_duty_found_window = get_memory_values(self.hwnd, 'is_duty_found_window', self.base_address, address_descriptions['is_duty_found_window']) == 1684829486

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
            if not self.is_moving:
                keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))
        elif not is_walking:
            if self.is_moving:
                keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('r', 0))

    def get_turn_duration(self, radians, ensure_nonnegative=True):
        # Delta Radians = 2.65 * Turn Duration + 0.0142
        # Delta Radians = 2.4 * Turn Duration + 0.055
        # Delta Radians = 2.35 * Turn Duration + 0
        # Why different?
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
        distance_delta = get_euclidean_distance([self.x, self.y, 0], [target_x, target_y, 0])
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

    def cast(self, skill_name, swiftcast_active=False):
        print('Using %s' % skill_name)
        skill = self.skills[skill_name]
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx(str(skill['button']), 0))
        if swiftcast_active:
            time.sleep(skill['recast'])
        else:
            time.sleep(skill['delay'])

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

    def get_dps_target(self):
        keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F4)  # Hotkey for targeting DPS member
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('t', 0))

    def get_teammate_target(self):
        if random.random() > 0.5:
            self.get_tank_target()
        else:
            self.get_dps_target()

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
        self.next_coordinate = None
        self.target_coordinate = None
        if not continue_walking:
            self.ensure_walking_state(False)

    def init_routing_target(self, target_coordinate, continue_walking=False):
        if not self.w:
            return
        self.cancel_routing_target(continue_walking=continue_walking)
        self.target_coordinate = target_coordinate
        a = self.get_current_coordinate()
        b = target_coordinate
        self.shortest_path = self.w.get_shortest_path_coordinates(a, b)

    def walk_to_routing_target(self, target_coordinate=None, reinit_if_empty=True, reinit_if_different=False):
        if reinit_if_different:
            if self.target_coordinate != target_coordinate:
                self.init_routing_target(target_coordinate)
        if self.next_coordinate is None:
            if len(self.shortest_path) == 0:
                if reinit_if_empty and target_coordinate:
                    delta_x = 0
                    delta_y = 0
                    if self.is_moving:
                        current_direction = self.get_current_direction()
                        delta_x = 6 * math.cos(current_direction)
                        delta_y = -(6 * math.sin(current_direction))
                    self.init_routing_target([target_coordinate[0] + delta_x, target_coordinate[1] + delta_y], continue_walking=True)
                else:
                    self.ensure_walking_state(False)
                    return False
            self.next_coordinate = self.shortest_path.pop(0)
        distance_delta, direction_delta, is_turn_left = self.calculate_navigation(self.next_coordinate[0], self.next_coordinate[1])
        if distance_delta < 1:
            self.next_coordinate = None
        else:
            turn_duration = self.get_turn_duration(direction_delta)
            if turn_duration > 0.3:
                self.ensure_walking_state(False)
            if turn_duration > 0:
                if is_turn_left:
                    self.turn_by_duration('left', turn_duration)
                else:
                    self.turn_by_duration('right', turn_duration)
            self.ensure_walking_state(True)
        return True

    def start(self):
        if self.mode == 'dungeon':
            self.state_overall = DungeonState.SELECTING_TEAMMATE
            self.start_dungeon()
        elif self.mode == 'assist':
            self.state_overall = AssistState.ACQUIRING_ENEMY
            self.start_assist(autotarget=False, autoapproach=False)
        elif self.mode == 'assist_autotarget':
            self.state_overall = AssistState.ACQUIRING_ENEMY
            self.start_assist(autotarget=True, autoapproach=False)
        elif self.mode == 'assist_autotarget_autoapproach':
            self.start_assist(autotarget=True, autoapproach=True)
            self.state_overall = AssistState.ACQUIRING_ENEMY
        elif self.mode == 'assist_autoapproach':
            self.start_assist(autotarget=False, autoapproach=True)
            self.state_overall = AssistState.ACQUIRING_ENEMY

    def start_assist(self, autotarget=False, autoapproach=False):
        record_timestamp = time.time()
        coordinates = []
        try:
            while True:
                self.scan()

                if time.time() - record_timestamp > 0.1:
                    coordinates.append((self.x, self.y, self.z))
                    record_timestamp = time.time()

                if self.state_overall == AssistState.ACQUIRING_ENEMY:
                    if self.selection_acquired:
                        self.debounced_print('Selection acquired. Navigating to enemy')
                        self.state_overall = AssistState.NAVIGATING_ENEMY
                        continue
                    if autotarget:
                        self.debounced_print('No selection. Attempting to select enemy')
                        self.get_nearest_enemy()
                    time.sleep(0.1)

                elif self.state_overall == AssistState.NAVIGATING_ENEMY:
                    if not self.selection_acquired:
                        self.debounced_print('No selection. Attempting to acquire enemy')
                        if autoapproach:
                            self.ensure_walking_state(False)
                        self.state_overall = AssistState.ACQUIRING_ENEMY
                        continue
                    if self.selection_distance < self.max_distance_to_target_high:
                        self.debounced_print('Enemy in range. Attempting to attack')
                        if autoapproach:
                            self.ensure_walking_state(False)
                        self.state_overall = AssistState.ATTACKING
                        continue
                    if autoapproach:
                        self.debounced_print('Enemy out of range range. Attempting to approach enemy')
                        self.turn_to_target(self.selection_x, self.selection_y)
                        self.ensure_walking_state(True)
                    time.sleep(0.1)

                elif self.state_overall == AssistState.ATTACKING:
                    if not self.selection_acquired:
                        self.debounced_print('No selection. Attempting to acquire enemy')
                        self.state_overall = AssistState.ACQUIRING_ENEMY
                        continue
                    if self.selection_distance > self.max_distance_to_target_high:
                        self.debounced_print('Enemy out of range. Attempting to acquire enemy')
                        self.state_overall = AssistState.ACQUIRING_ENEMY
                        continue
                    if self.is_moving:
                        self.debounced_print('Still moving, waiting for stop')
                        time.sleep(0.1)
                        continue
                    self.debounced_print('Enemy in range. Attacking!')
                    self.attack()
        finally:
            filename = 'recording%s.json' % (int(time.time() * 1000))
            with open(filename, 'w') as f:
                print('Writing %s waypoints to %s' % (len(coordinates), filename))
                f.write(json.dumps(coordinates))

    def start_dungeon(self):
        record_timestamp = time.time()
        coordinates = []
        try:
            teammate_state = DungeonTeammateState.TANK
            last_state = None
            while True:
                self.scan()

                if self.is_duty_found_window:
                    time.sleep(1)
                    self.accept_duty()
                    time.sleep(5)

                if self.map_id != self.navigation_map_id:
                    self.debounced_print(
                        'Map ID %s does not match expected %s, waiting.' % (self.map_id, self.navigation_map_id))
                    time.sleep(1)
                    continue

                if self.is_cutscene:
                    time.sleep(5)
                    self.skip_cutscene()
                    time.sleep(5)
                    continue

                if time.time() - record_timestamp > 0.1:
                    coordinates.append((self.x, self.y, self.z))
                    record_timestamp = time.time()

                if self.state_overall != last_state:
                    print(self.state_overall)
                last_state = self.state_overall

                if self.state_overall == DungeonState.NAVIGATING_DUNGEON:
                    is_continue_walking = self.walk_to_routing_target(self.navigation_target, reinit_if_empty=False, reinit_if_different=True)
                    if not is_continue_walking:
                        self.debounced_print('Reached end of dungeon!')
                        continue
                    self.state_overall = DungeonState.TOGGLING_TEAMMATE
                    time.sleep(0.05)

                elif self.state_overall == DungeonState.TOGGLING_TEAMMATE:
                    if teammate_state == DungeonTeammateState.TANK:
                        teammate_state = DungeonTeammateState.DPS
                    else:
                        teammate_state = DungeonTeammateState.TANK
                    self.state_overall = DungeonState.SELECTING_TEAMMATE

                elif self.state_overall == DungeonState.SELECTING_TEAMMATE:
                    # self.get_teammate()
                    if teammate_state == DungeonTeammateState.TANK:
                        self.get_tank()
                    else:
                        self.get_dps()
                    self.state_overall = DungeonState.CHECKING_TEAMMATE

                elif self.state_overall == DungeonState.CHECKING_TEAMMATE:
                    if not self.selection_acquired:
                        self.debounced_print('No selection. Attempting to navigate dungeon')
                        self.state_overall = DungeonState.NAVIGATING_DUNGEON
                        continue
                    if self.selection_is_enemy:
                        self.debounced_print('Enemy selected. Attempting to check enemy')
                        self.state_overall = DungeonState.CHECKING_ENEMY
                        continue
                    self.debounced_print('Teammate selected. Attempting to navigate to teammate')
                    self.cancel_routing_target()  # Need to cancel routing when entering dynamic waypoint
                    self.state_overall = DungeonState.NAVIGATING_TO_TEAMMATE

                elif self.state_overall == DungeonState.NAVIGATING_TO_TEAMMATE:
                    if not self.selection_acquired:
                        self.debounced_print('No selection. Attempting to select teammate')
                        self.cancel_routing_target()
                        self.state_overall = DungeonState.TOGGLING_TEAMMATE
                        continue
                    if self.selection_is_enemy:
                        self.debounced_print('Enemy selected. Attempting to check enemy')
                        self.cancel_routing_target()
                        self.state_overall = DungeonState.CHECKING_ENEMY
                        continue
                    if self.selection_distance < self.max_distance_to_teammate:
                        self.debounced_print('Teammate in range. Attempting to select enemy')
                        self.cancel_routing_target()
                        self.state_overall = DungeonState.SELECTING_ENEMY
                        continue
                    self.debounced_print('Navigating to teammate')
                    self.walk_to_routing_target([self.selection_x, self.selection_y], reinit_if_empty=True, reinit_if_different=False)
                    time.sleep(0.05)

                elif self.state_overall == DungeonState.SELECTING_ENEMY:
                    # self.get_teammate_target()
                    if teammate_state == DungeonTeammateState.TANK:
                        self.get_tank_target()
                    else:
                        self.get_dps_target()
                    self.state_overall = DungeonState.CHECKING_ENEMY

                elif self.state_overall == DungeonState.CHECKING_ENEMY:
                    if not self.selection_acquired:
                        self.debounced_print('No selection. Attempting to select teammate')
                        self.state_overall = DungeonState.TOGGLING_TEAMMATE
                        continue
                    if not (self.selection_is_enemy and self.selection_is_damaged):
                        self.debounced_print('Selection is not a damaged enemy. Attempting to select teammate')
                        self.state_overall = DungeonState.TOGGLING_TEAMMATE
                        continue
                    if self.selection_distance > self.max_distance_to_target_high:
                        self.debounced_print('Enemy out of range. Attempting to select teammate')
                        self.state_overall = DungeonState.TOGGLING_TEAMMATE
                        continue
                    if self.selection_npc_id == 73:  # If Galvanth the dominator, target the DPS's target
                        self.debounced_print('Galvanth detected. Attempting to acquire DPS target')
                        self.get_dps_target()
                        self.state_overall = DungeonState.LINEAR_APPROACHING_TARGET
                    self.debounced_print('Enemy in range. Attempting to attack enemy')
                    self.state_overall = DungeonState.ATTACKING

                elif self.state_overall == DungeonState.LINEAR_APPROACHING_TARGET:
                    if not self.selection_acquired:
                        self.debounced_print('No selection. Attempting to select enemy')
                        self.state_overall = DungeonState.SELECTING_ENEMY
                        continue
                    if not (self.selection_is_enemy and self.selection_is_damaged):
                        self.debounced_print('Selection is not a damaged enemy. Attempting to select enemy')
                        self.state_overall = DungeonState.SELECTING_ENEMY
                        continue
                    if self.selection_distance < self.max_distance_to_target_high:
                        self.debounced_print('Enemy in range. Attempting to attack')
                        self.state_overall = DungeonState.ATTACKING
                        continue
                    self.debounced_print('Enemy out of range range. Attempting to approach enemy')
                    self.turn_to_target(self.selection_x, self.selection_y)
                    self.ensure_walking_state(True)
                    time.sleep(0.1)

                elif self.state_overall == DungeonState.ATTACKING:
                    if not self.selection_acquired:
                        self.debounced_print('No selection. Attempting to select enemy')
                        self.state_overall = DungeonState.SELECTING_ENEMY
                        continue
                    if not (self.selection_is_enemy and self.selection_is_damaged):
                        self.debounced_print('Selection is not a damaged enemy. Attempting to select enemy')
                        self.state_overall = DungeonState.SELECTING_ENEMY
                        continue
                    if self.selection_distance > self.max_distance_to_target_high:
                        self.debounced_print('Enemy out of range. Attempting to select enemy')
                        self.state_overall = DungeonState.SELECTING_ENEMY
                        continue
                    self.attack()
                    if self.selection_npc_id == 73:  # If Galvanth the dominator, target the DPS's target
                        self.debounced_print('Galvanth detected. Attempting to acquire DPS target')
                        teammate_state = DungeonTeammateState.DPS
                        self.get_dps_target()
                        self.state_overall = DungeonState.LINEAR_APPROACHING_TARGET

        finally:
            filename = 'recording%s.json' % (int(time.time() * 1000))
            with open(filename, 'w') as f:
                print('Writing %s waypoints to %s' % (len(coordinates), filename))
                f.write(json.dumps(coordinates))

    def record(self, interval=0.1):
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
