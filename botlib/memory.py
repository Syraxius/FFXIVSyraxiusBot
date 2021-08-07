import ctypes
from ctypes import wintypes

import pywintypes
import win32api
import win32con
import win32gui
import win32process


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
