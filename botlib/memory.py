import ctypes
from ctypes import wintypes

import pywintypes
import win32api
import win32con
import win32gui
import win32process
import win32security


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


def get_privilege(privilege_name='SeDebugPrivilege'):
    # Adapted from: https://github.com/hacksysteam/WpadEscape/blob/master/inject-dll.py
    # The SeDebugPrivilege is required to write to memory
    success = False
    privilege_id = win32security.LookupPrivilegeValue(None, privilege_name)
    new_privilege = [(privilege_id, win32con.SE_PRIVILEGE_ENABLED)]
    h_token = win32security.OpenProcessToken(win32process.GetCurrentProcess(), win32security.TOKEN_ALL_ACCESS)
    if h_token:
        success = win32security.AdjustTokenPrivileges(h_token, 0, new_privilege)
        win32api.CloseHandle(h_token)
    return success


def open_process_vm_read_handle(hwnd):
    # Specify the params and return type of ReadProcessMemory
    # https://stackoverflow.com/questions/33855690/trouble-with-readprocessmemory-in-python-to-read-64bit-process-memory
    ctypes.windll.kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    ctypes.windll.kernel32.ReadProcessMemory.restype = wintypes.BOOL

    PROCESS_VM_READ = 0x0010
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_VM_READ, False, pid)

    return handle


def open_process_vm_write_handle(hwnd):
    ctypes.windll.kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    ctypes.windll.kernel32.WriteProcessMemory.restype = wintypes.BOOL

    # Get SeDebugPrivilege
    get_privilege()

    # https://docs.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights
    # PROCESS_VM_WRITE and PROCESS_VM_OPERATION are required for WriteProcessMemory
    PROCESS_VM_WRITE = 0x0020
    PROCESS_VM_OPERATION = 0x0008
    PROCESS_ALL_ACCESS = (PROCESS_VM_WRITE | PROCESS_VM_OPERATION)
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)

    return handle


def close_process_vm_handle(handle):
    ctypes.windll.kernel32.CloseHandle(handle)


def get_final_address(hwnd, base_address, address_description, external_handle=None):
    if external_handle:
        handle = external_handle
    else:
        handle = open_process_vm_read_handle(hwnd)

    address_buffer = ctypes.c_uint64()
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

    return next_address


def get_memory_value(hwnd, base_address, address_description, external_handle=None):
    if external_handle:
        handle = external_handle
    else:
        handle = open_process_vm_read_handle(hwnd)

    if address_description['datatype'] == 'integer':
        final_buffer = ctypes.c_uint32()
    elif address_description['datatype'] == 'byte':
        final_buffer = ctypes.c_uint8()
    elif address_description['datatype'] == 'float':
        final_buffer = ctypes.c_float()
    elif address_description['datatype'] == 'string':
        final_buffer = ctypes.create_string_buffer(address_description['length'])

    final_address = get_final_address(hwnd, base_address, address_description, external_handle=handle)

    ctypes.windll.kernel32.ReadProcessMemory(handle, final_address, ctypes.byref(final_buffer), ctypes.sizeof(final_buffer), None)
    curr_value = final_buffer.value

    if not external_handle:
        close_process_vm_handle(handle)

    return curr_value


def get_multiple_memory_values(hwnd, base_address, base_address_offset, partial_descriptions):
    memory_values = {}
    for name in partial_descriptions:
        partial_description = partial_descriptions[name]
        address_description = partial_description.copy()
        address_description['base_address_offset'] = base_address_offset
        memory_values[name] = get_memory_value(hwnd, base_address, address_description)
    return memory_values


def set_memory_value(hwnd, base_address, address_description, value, external_read_handle=None, external_write_handle=None):
    if external_read_handle:
        read_handle = external_read_handle
    else:
        read_handle = open_process_vm_read_handle(hwnd)

    if external_write_handle:
        write_handle = external_write_handle
    else:
        write_handle = open_process_vm_write_handle(hwnd)

    final_address = get_final_address(hwnd, base_address, address_description, external_handle=read_handle)

    if address_description['datatype'] == 'integer':
        final_buffer = ctypes.c_uint32(value)
    elif address_description['datatype'] == 'byte':
        final_buffer = ctypes.c_uint8(value)
    elif address_description['datatype'] == 'float':
        final_buffer = ctypes.c_float(value)

    ctypes.windll.kernel32.WriteProcessMemory(write_handle, final_address, ctypes.byref(final_buffer), ctypes.sizeof(final_buffer), None)
