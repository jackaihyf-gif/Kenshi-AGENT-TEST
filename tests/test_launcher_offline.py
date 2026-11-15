"""Exercise Win32 handshake decisions with fake APIs; never load a system DLL."""

from types import SimpleNamespace

import pytest

from kenshi_test import launcher
from kenshi_test.adapters.base import Deadline
from kenshi_test.errors import AdapterError, OperationTimeout


class Function:
    def __init__(self, call):
        self.call = call

    def __call__(self, *args):
        return self.call(*args)


@pytest.fixture
def windows(monkeypatch, tmp_path):
    exe = tmp_path / "kenshi_x64.exe"
    exe.write_bytes(b"synthetic, never executed")
    state = SimpleNamespace(existing=False, windows=True, posts=[], fail_post=False)

    def first(snapshot, pointer):
        if not state.existing:
            return False
        entry = pointer._obj
        entry.pid, entry.parent, entry.threads, entry.name = 10, 1, 1, "kenshi_x64.exe"
        return True

    def pid(window, pointer):
        pointer._obj.value = 10

    def text(window, buffer, length):
        buffer.value = "Kenshi 1.0" if window == 100 else "Start"

    def kind(window, buffer, length):
        buffer.value = "#32770" if window == 100 else "Button"

    def post(*args):
        state.posts.append(args)
        return not state.fail_post

    functions = {
        "CreateToolhelp32Snapshot": lambda *a: 1,
        "Process32FirstW": first,
        "Process32NextW": lambda *a: False,
        "CloseHandle": lambda *a: True,
        "OpenProcess": lambda *a: 1,
        "GetExitCodeProcess": lambda h, p: setattr(p._obj, "value", 259) or True,
        "EnumWindows": lambda cb, p: cb(100, p) if state.windows else None,
        "EnumChildWindows": lambda w, cb, p: [cb(i, p) for i in (1002, 1003, 1004, 1006, 1010)],
        "GetWindowThreadProcessId": pid,
        "GetWindowTextW": text,
        "GetClassNameW": kind,
        "GetDlgCtrlID": lambda w: w,
        "GetDlgItem": lambda *a: 0,
        "IsWindowEnabled": lambda *a: True,
        "SendMessageTimeoutW": lambda *a: 1,
        "PostMessageW": post,
    }
    api = SimpleNamespace(**{k: Function(v) for k, v in functions.items()})
    monkeypatch.setattr(launcher, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(launcher.ctypes, "WinDLL", lambda *a, **k: api, raising=False)
    monkeypatch.setattr(launcher.ctypes, "WINFUNCTYPE", lambda *a: lambda f: f, raising=False)
    monkeypatch.setattr(launcher.ctypes, "get_last_error", lambda: 5, raising=False)

    def spawn(*args, **kwargs):
        state.existing = True
        return SimpleNamespace(pid=10)

    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    return exe, state


def test_launch_confirmation_is_not_game_verification(windows):
    exe, state = windows
    result = launcher.start_game(exe, Deadline(1))
    assert result["started_pid"] == 10
    assert not result["initialized"] and not result["game_verified"]
    assert len(state.posts) == 1


def test_existing_game_requires_explicit_attach(windows):
    exe, state = windows
    state.existing = True
    with pytest.raises(AdapterError, match="already running"):
        launcher.start_game(exe, Deadline(1))
    result = launcher.start_game(exe, Deadline(1), attach=True, inspect=True)
    assert len(result["windows"]) == 1
    assert state.posts == []


def test_attach_without_game_refused(windows):
    exe, _ = windows
    with pytest.raises(AdapterError, match="one Kenshi process tree"):
        launcher.start_game(exe, Deadline(1), attach=True)


def test_failed_confirmation_is_error(windows):
    exe, state = windows
    state.fail_post = True
    with pytest.raises(AdapterError, match="confirmation rejected"):
        launcher.start_game(exe, Deadline(1))


def test_bridge_ready_does_not_verify_mod(windows, monkeypatch, tmp_path):
    from kenshi_test.bridge import LuaBridge

    exe, state = windows
    state.windows = False
    monkeypatch.setattr(LuaBridge, "call", lambda *a, **k: {"state": {"phase": "ready"}})
    result = launcher.start_game(exe, Deadline(1), bridge_dir=tmp_path)
    assert result["initialized"] and not result["game_verified"]


def test_bridge_timeout_is_bounded(windows, monkeypatch, tmp_path):
    from kenshi_test.bridge import LuaBridge

    exe, state = windows
    state.windows = False

    def timeout(*a, **k):
        raise OperationTimeout("synthetic timeout")

    monkeypatch.setattr(LuaBridge, "call", timeout)
    with pytest.raises(AdapterError, match="not observed"):
        launcher.start_game(exe, Deadline(0.15), bridge_dir=tmp_path)


def test_invalid_executable_is_rejected(windows, tmp_path):
    with pytest.raises(AdapterError, match="Configure"):
        launcher.start_game(tmp_path / "other.exe", Deadline(1))
