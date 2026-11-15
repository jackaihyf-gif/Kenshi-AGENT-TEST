"""Windows Kenshi launch handshake with opt-in handling of its known mod warning.

This is explicitly requested native launcher automation, not a general-purpose
desktop controller. It sends no mouse/keyboard input and rejects unknown warnings.
"""

import ctypes
import os
import subprocess
import time
from ctypes import wintypes as W
from pathlib import Path

from .adapters.base import Deadline
from .errors import AdapterError, FeatureUnavailable, OperationTimeout


def mod_warning_button(dialog: dict) -> dict | None:
    """Only acknowledge the observed missing/order warning, in Chinese or English."""
    title = dialog["title"].strip().casefold()
    if title not in {"mod警告", "mods warning", "mod warning"}:
        return None
    text = " ".join(child["text"] for child in dialog["children"]
                    if child["class"].casefold() == "static").casefold()
    known = ("一个或多个mod已丢失或顺序错误" in text or
             "one or more mods are missing or in incorrect order" in text)
    if not known:
        return None
    for child in dialog["children"]:
        label = child["text"].replace("&", "").casefold().strip()
        if child["class"].casefold() == "button" and child["id"] in (1, 6):
            if label in {"是(y)", "是", "yes", "ok", "确定", "确认"}:
                return child
    return None


def launcher_roots(table: dict) -> set[int]:
    """RE_Kenshi may retain its parent launcher while starting one game child."""
    game = {pid for pid, (_, name) in table.items() if name == "kenshi_x64.exe"}
    return {pid for pid in game if table[pid][0] not in game}


def process_may_be_running(exit_code: int | None) -> bool:
    """Unknown exit status must never bypass the existing-process guard."""
    return exit_code is None or exit_code == 259


def start_game(executable: Path, deadline: Deadline, *, attach: bool = False,
               inspect: bool = False, skip_mod_warnings: bool = False,
               bridge_dir: Path | None = None) -> dict:
    if os.name != "nt":
        raise FeatureUnavailable("Native Kenshi startup is available on Windows only")
    if executable.name.lower() != "kenshi_x64.exe" or not executable.is_file():
        raise AdapterError("Configure the installed Kenshi kenshi_x64.exe")
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

    class ProcessEntry(ctypes.Structure):
        _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("pid", W.DWORD),
                    ("heap", ctypes.c_size_t), ("module", W.DWORD), ("threads", W.DWORD),
                    ("parent", W.DWORD), ("priority", W.LONG), ("flags", W.DWORD),
                    ("name", W.WCHAR * 260)]

    kernel.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = W.HANDLE
    kernel.Process32FirstW.argtypes = [W.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [W.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.GetExitCodeProcess.argtypes = [W.HANDLE, ctypes.POINTER(W.DWORD)]
    kernel.GetExitCodeProcess.restype = W.BOOL
    user.EnumWindows.argtypes = [callback_type, W.LPARAM]
    user.EnumChildWindows.argtypes = [W.HWND, callback_type, W.LPARAM]
    user.GetDlgCtrlID.argtypes = [W.HWND]
    user.GetDlgCtrlID.restype = ctypes.c_int
    user.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
    user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
    user.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
    user.GetDlgItem.argtypes = [W.HWND, ctypes.c_int]
    user.GetDlgItem.restype = W.HWND
    user.IsWindowEnabled.argtypes = [W.HWND]
    user.IsWindowEnabled.restype = W.BOOL
    user.SendMessageTimeoutW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM,
                                       W.UINT, W.UINT, ctypes.POINTER(ctypes.c_size_t)]
    user.SendMessageTimeoutW.restype = ctypes.c_size_t
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.PostMessageW.restype = W.BOOL

    def processes():
        snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
        if snapshot == W.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        result = {}
        try:
            entry = ProcessEntry()
            entry.dwSize = ctypes.sizeof(entry)
            more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
            while more:
                # A denied/sandboxed child can remain as a zero-thread process
                # object until its parent closes its handles. It has no game loop.
                handle = kernel.OpenProcess(0x1000, False, entry.pid)
                exit_code = None  # Access failure is not evidence of termination.
                if handle:
                    code = W.DWORD()
                    if kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                        exit_code = code.value
                    kernel.CloseHandle(handle)
                if entry.threads and process_may_be_running(exit_code):
                    result[entry.pid] = (entry.parent, entry.name.lower())
                more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            kernel.CloseHandle(snapshot)
        return result

    initial_table = processes()
    existing = {pid for pid, (_, name) in initial_table.items() if name == "kenshi_x64.exe"}
    if existing and not attach:
        raise AdapterError("Kenshi already running; use start --attach-launcher explicitly")
    if attach:
        roots = launcher_roots(initial_table)
        if len(roots) != 1:
            raise AdapterError("Attaching requires one Kenshi process tree, not independent games")
        owned = roots
        started_pid = None
    else:
        process = subprocess.Popen([str(executable)], cwd=executable.parent)
        started_pid = process.pid
        owned = {process.pid}
    actions = []
    handled = set()
    started_at = time.time()
    while True:
        deadline.remaining()
        table = processes()
        for _ in range(4):
            owned.update(pid for pid, (parent, name) in table.items()
                         if parent in owned and name == "kenshi_x64.exe")
        candidates = []
        observed_windows = []

        @callback_type
        def visit(window, _, found=candidates, observed=observed_windows):
            pid = W.DWORD()
            user.GetWindowThreadProcessId(window, ctypes.byref(pid))
            if pid.value not in owned:
                return True
            title, kind = ctypes.create_unicode_buffer(512), ctypes.create_unicode_buffer(128)
            user.GetWindowTextW(window, title, len(title))
            user.GetClassNameW(window, kind, len(kind))
            record = {"title": title.value, "class": kind.value, "pid": pid.value,
                      "enabled": bool(user.IsWindowEnabled(window)),
                      "handle": window, "children": []}
            observed.append(record)
            if kind.value != "#32770":
                return True
            descendants = {}

            @callback_type
            def child_visit(child, _):
                identifier = user.GetDlgCtrlID(child)
                label, cls = ctypes.create_unicode_buffer(2048), ctypes.create_unicode_buffer(128)
                user.GetWindowTextW(child, label, len(label))
                user.GetClassNameW(child, cls, len(cls))
                record["children"].append({"id": identifier, "text": label.value,
                                           "class": cls.value, "handle": child})
                if identifier in (1002, 1003, 1004, 1006, 1010):
                    descendants[identifier] = child
                return True

            user.EnumChildWindows(window, child_visit, 0)
            controls = [descendants.get(i) for i in (1002, 1003, 1004, 1006, 1010)]
            if all(controls) and title.value.startswith("Kenshi ") and record["enabled"]:
                button_class = ctypes.create_unicode_buffer(64)
                user.GetClassNameW(controls[1], button_class, len(button_class))
                if button_class.value.lower() == "button":
                    found.append((window, controls[1], pid.value, title.value))
            return True

        user.EnumWindows(visit, 0)
        if inspect:
            return {"windows": [row for row in observed_windows if row["class"] == "#32770"]}
        warnings = []
        for row in observed_windows:
            if row["class"] == "#32770" and row["enabled"]:
                button = mod_warning_button(row)
                if button:
                    if not skip_mod_warnings:
                        raise AdapterError("Known mod warning found; use --skip-mod-warnings")
                    warnings.append((row, button))
        if len(warnings) > 1:
            raise AdapterError("Multiple active mod warnings; refusing ambiguity")
        if warnings:
            row, button = warnings[0]
            key = (row["handle"], button["id"], row["title"])
            if key not in handled:
                # Standard MessageBox handles IDYES/IDOK directly, even in background.
                if not user.PostMessageW(row["handle"], 0x111, button["id"], button["handle"]):
                    raise ctypes.WinError(ctypes.get_last_error())
                handled.add(key)
                actions.append({"action": "accept_mod_warning", "dialog": row})
            deadline.sleep(.1)
            continue
        if len(candidates) > 1:
            raise AdapterError("Multiple matching settings dialogs; refusing ambiguity")
        if candidates:
            window, button, pid, title = candidates[0]
            # WM_COMMAND + BN_CLICKED; IDs independently observed on this launcher.
            # Queue it; cross-process synchronous sends can stall modal initialization.
            key = (window, 1003, title)
            if key not in handled:
                sent = user.PostMessageW(button, 0xF5, 0, 0)
                if not sent:
                    raise AdapterError(f"Startup confirmation rejected: {ctypes.get_last_error()}")
                handled.add(key)
                actions.append({"action": "confirm_settings", "pid": pid, "title": title})
            if bridge_dir is None:
                return {"started_pid": started_pid, "actions": actions,
                        "initialized": False, "game_verified": False,
                        "note": "Game-side RPC not configured; confirmation alone is not proof"}
        if bridge_dir is not None and not candidates:
            from .bridge import LuaBridge

            try:
                response = LuaBridge(bridge_dir).call("status", Deadline(
                    min(.8, deadline.remaining())))
            except OperationTimeout:
                pass
            else:
                return {"started_pid": started_pid, "actions": actions,
                        "initialized": True, "game_verified": False,
                        "elapsed_seconds": round(time.time() - started_at, 3),
                        "in_game_response": response}
        if not any(pid in table for pid in owned):
            raise AdapterError("Kenshi exited before its startup dialog appeared")
        if deadline.remaining() < .2:
            raise AdapterError(
                f"Game-side initialization not observed; windows: {observed_windows}"
            )
        deadline.sleep(.1)
