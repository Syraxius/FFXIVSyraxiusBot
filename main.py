import enum
import time

import win32api
import win32con
import win32gui

import ctypes
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


def keyboard_send_vk_as_scan_code(hwnd, vk, extended=0):
    scan_code = win32api.MapVirtualKey(vk, 0)
    lparam = extended << 24 | scan_code << 16
    win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam)
    win32gui.SendMessage(hwnd, win32con.WM_KEYUP, vk, lparam)


def get_memory_values(hwnd, address_description):
    # Specify the params and return type of ReadProcessMemory
    # https://stackoverflow.com/questions/33855690/trouble-with-readprocessmemory-in-python-to-read-64bit-process-memory
    ctypes.windll.kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    ctypes.windll.kernel32.ReadProcessMemory.restype = wintypes.BOOL

    process_vm_read = 0x0010  # Permission
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    handle = ctypes.windll.kernel32.OpenProcess(process_vm_read, False, pid)

    address_buffer = ctypes.c_uint64()
    final_buffer = ctypes.c_uint32()

    base_pointer = address_description['base']
    ctypes.windll.kernel32.ReadProcessMemory(handle, base_pointer, ctypes.byref(address_buffer), ctypes.sizeof(address_buffer), None)
    next_address = address_buffer.value
    position = 1
    for offset in address_description['offsets']:
        next_address = next_address + offset
        if position != len(address_description['offsets']):
            ctypes.windll.kernel32.ReadProcessMemory(handle, next_address, ctypes.byref(address_buffer), ctypes.sizeof(address_buffer), None)
            next_address = address_buffer.value
    ctypes.windll.kernel32.ReadProcessMemory(handle, next_address, ctypes.byref(final_buffer), ctypes.sizeof(final_buffer), None)
    curr_value = final_buffer.value

    ctypes.windll.kernel32.CloseHandle(handle)
    return curr_value


address_descriptions = {
    'mp': {
        'base': 0x7ff76d178210,
        'offsets': (0x1CC,)
    },
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


def cast(hwnd, spell):
    keyboard_send_vk_as_scan_code(hwnd, win32api.VkKeyScanEx(str(spell['button']), 0))
    time.sleep(spell['delay'])


def main():
    winlist = get_winlist()
    hwnd = get_hwnd('FINAL FANTASY XIV', winlist)

    class BlackMageState(enum.Enum):
        ICE = 1
        FIRE = 2

    state = BlackMageState.FIRE
    transpose_timestamp = time.time()
    while True:
        mp = get_memory_values(hwnd, address_descriptions['mp'])
        transpose_delta = time.time() - transpose_timestamp

        if state == BlackMageState.FIRE:
            if mp < 2000:
                if transpose_delta < 5:
                    time.sleep(transpose_delta)
                cast(hwnd, spells['transpose'])
                state = BlackMageState.ICE
                continue
            cast(hwnd, spells['fire'])

        if state == BlackMageState.ICE:
            if mp >= 8000:
                if transpose_delta > 5:
                    cast(hwnd, spells['transpose'])
                    state = BlackMageState.FIRE
                continue
            cast(hwnd, spells['ice'])


if __name__ == '__main__':
    main()
