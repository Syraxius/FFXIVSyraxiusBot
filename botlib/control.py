import time

import win32api
import win32con
import win32gui


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