import enum
import math
import time

import win32api
import win32con
import win32gui

import ctypes
import pywintypes
import win32process
from ctypes import wintypes


def get_winlist():
    winlist = []
    toplist = []

    def _enum_cb(hwnd, results):
        winlist.append((hwnd, win32gui.GetWindowText(hwnd)))

    win32gui.EnumWindows(_enum_cb, toplist)
    return winlist


def get_hwnd(name, winlist):
    return [(hwnd, title) for hwnd, title in winlist if name in title][0][0]


def get_hwnd_base_address(hwnd):
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, pywintypes.FALSE, pid)
    base_address = win32process.EnumProcessModules(handle)[0]
    win32api.CloseHandle(handle)
    return base_address


def get_memory_values(hwnd, base_address, address_description):
    # Specify the params and return type of ReadProcessMemory
    # https://stackoverflow.com/questions/33855690/trouble-with-readprocessmemory-in-python-to-read-64bit-process-memory
    ctypes.windll.kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    ctypes.windll.kernel32.ReadProcessMemory.restype = wintypes.BOOL

    process_vm_read = 0x0010  # Permission
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    handle = ctypes.windll.kernel32.OpenProcess(process_vm_read, False, pid)

    address_buffer = ctypes.c_uint64()
    if address_description['datatype'] == 'integer':
        final_buffer = ctypes.c_uint32()
    elif address_description['datatype'] == 'float':
        final_buffer = ctypes.c_float()

    base_pointer = base_address + address_description['base_address_offset']
    if len(address_description['pointer_offsets']) > 0:
        ctypes.windll.kernel32.ReadProcessMemory(handle, base_pointer, ctypes.byref(address_buffer), ctypes.sizeof(address_buffer), None)
        next_address = address_buffer.value
        position = 1
        for pointer_offset in address_description['pointer_offsets']:
            next_address = next_address + pointer_offset
            if position != len(address_description['pointer_offsets']):
                ctypes.windll.kernel32.ReadProcessMemory(handle, next_address, ctypes.byref(address_buffer), ctypes.sizeof(address_buffer), None)
                next_address = address_buffer.value
            position += 1
    else:
        next_address = base_pointer
    ctypes.windll.kernel32.ReadProcessMemory(handle, next_address, ctypes.byref(final_buffer), ctypes.sizeof(final_buffer), None)
    curr_value = final_buffer.value

    ctypes.windll.kernel32.CloseHandle(handle)
    return curr_value


def keyboard_send_vk_as_scan_code(hwnd, vk, extended=0, action='press', duration=0.0):
    scan_code = win32api.MapVirtualKey(vk, 0)
    lparam = extended << 24 | scan_code << 16
    if action == 'press':
        win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam)
        win32gui.SendMessage(hwnd, win32con.WM_KEYUP, vk, lparam)
    elif action == 'hold':
        win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam)
        time.sleep(duration)
        win32gui.SendMessage(hwnd, win32con.WM_KEYUP, vk, lparam)
    elif action == 'down':
        win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam)
    elif action == 'up':
        win32gui.SendMessage(hwnd, win32con.WM_KEYUP, vk, lparam)


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
        'delay': 2.5
    },
    'fire': {
        'button': 2,
        'delay': 2.5
    },
    'transpose': {
        'button': 3,
        'delay': 0.5
    }
}


class OverallState(enum.Enum):
    RETURNING = 1
    ACQUIRING = 2
    APPROACHING = 3
    ATTACKING = 4


class BlackMageAttackState(enum.Enum):
    ICE = 1
    FIRE = 2


class Bot:
    def __init__(self):
        winlist = get_winlist()
        self.hwnd = get_hwnd('FINAL FANTASY XIV', winlist)
        self.base_address = get_hwnd_base_address(self.hwnd)

        self.mp = 0
        self.distance_to_target = 0
        self.is_target_selected = False
        self.x = 0
        self.y = 0
        self.x_complex = 0
        self.y_complex = 0
        self.scan()
        self.init_x = self.x
        self.init_y = self.y

        self.state_overall = OverallState.RETURNING
        self.attack = self.attack_blackmage
        self.state_attack = BlackMageAttackState.FIRE
        self.transpose_timestamp = time.time()

        self.max_distance_to_target = 10
        self.max_patrol_distance = 30
        self.mode = 'patrol'  # 'patrol', 'dungeon', 'assist_autotarget', 'assist'
        if self.mode == 'dungeon':
            self.max_distance_to_target = 10
        else:
            self.max_distance_to_target = 25

    def scan(self):
        self.mp = get_memory_values(self.hwnd, self.base_address, address_descriptions['mp'])
        self.x = get_memory_values(self.hwnd, self.base_address, address_descriptions['x'])
        self.y = get_memory_values(self.hwnd, self.base_address, address_descriptions['y'])
        self.x_complex = get_memory_values(self.hwnd, self.base_address, address_descriptions['x_complex'])
        self.y_complex = get_memory_values(self.hwnd, self.base_address, address_descriptions['y_complex'])
        self.distance_to_target = get_memory_values(self.hwnd, self.base_address, address_descriptions['distance_to_target'])
        self.is_target_selected = self.distance_to_target != 0

    def cast(self, spell):
        keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx(str(spell['button']), 0))
        time.sleep(spell['delay'])

    def attack_blackmage(self):
        transpose_delta = time.time() - self.transpose_timestamp

        if self.state_attack == BlackMageAttackState.FIRE:
            if self.mp < 2000:
                if transpose_delta < 5:
                    time.sleep(transpose_delta)
                self.cast(spells['transpose'])
                self.transpose_timestamp = time.time()
                self.state_attack = BlackMageAttackState.ICE
                return
            self.cast(spells['fire'])
        elif self.state_attack == BlackMageAttackState.ICE:
            if self.mp >= 8000:
                if transpose_delta >= 5:
                    self.cast(spells['transpose'])
                    self.transpose_timestamp = time.time()
                    self.state_attack = BlackMageAttackState.FIRE
                    return
            self.cast(spells['ice'])

    def calculate_navigation(self, target_x, target_y):
        direction_x = target_x - self.x
        direction_y = -(target_y - self.y)
        current_direction = math.atan2(self.y_complex, self.x_complex)  # 0 is East
        if current_direction < 0:
            current_direction = current_direction + 2 * math.pi
        target_direction = math.atan2(direction_y, direction_x)  # 0 is East
        if target_direction < 0:
            target_direction = target_direction + 2 * math.pi
        direction_delta = target_direction - current_direction
        distance_delta = math.sqrt(direction_x * direction_x + direction_y * direction_y)
        is_turn_left = 0 < direction_delta < math.pi
        return direction_delta, distance_delta, is_turn_left

    def start(self):
        is_autorun = False

        last_x = self.x
        last_y = self.y
        last_state = None
        acquiring_timestamp = None

        while True:
            self.scan()

            direction_delta, distance_delta, is_turn_left = self.calculate_navigation(self.init_x, self.init_y)
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
                    turn_speed = 2.65  # rad/s
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
                if self.mode == 'dungeon':
                    keyboard_send_vk_as_scan_code(self.hwnd, win32api.VkKeyScanEx('9', 0))  # Hotkey for following focused
                    keyboard_send_vk_as_scan_code(self.hwnd, win32con.VK_F1)  # Hotkey for targeting self, acting as a deselect
                if self.mode == 'patrol' or self.mode == 'dungeon' or self.mode == 'assist_autotarget':
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
                        continue

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
                        continue


def main():
    bot = Bot()
    bot.start()


if __name__ == '__main__':
    main()
