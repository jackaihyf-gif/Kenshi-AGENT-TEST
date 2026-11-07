"""KenshiLua file-watch reload must retain the already active bridge and globals."""

import ctypes
import json
import os
from pathlib import Path

import pytest


def test_watch_reload_keeps_old_bridge_and_cold_start_selects_fix():
    runtime = os.environ.get("KENSHI_TEST_LUA51")
    if not runtime:
        pytest.skip("Set KENSHI_TEST_LUA51 to exercise the material loader in LuaJIT")
    lib = ctypes.CDLL(runtime)
    lib.luaL_newstate.restype = ctypes.c_void_p
    for name, args in [
        ("luaL_openlibs", [ctypes.c_void_p]),
        ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
        ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
        ("lua_tolstring", [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]),
        ("lua_close", [ctypes.c_void_p]),
    ]:
        getattr(lib, name).argtypes = args
    lib.lua_tolstring.restype = ctypes.c_char_p
    root = Path(__file__).parents[1]
    loader = root / "experiments/material_binding/material_native.lua"
    code = "LOADER_PATH=" + json.dumps(loader.as_posix()) + "\n"
    code += (root / "tests/fixtures/material_loader_watch.lua").read_text("utf8")
    state = lib.luaL_newstate()
    lib.luaL_openlibs(state)
    try:
        result = lib.luaL_loadstring(state, code.encode("utf8"))
        if not result:
            result = lib.lua_pcall(state, 0, 0, 0)
        assert result == 0, lib.lua_tolstring(state, -1, None).decode("utf8")
    finally:
        lib.lua_close(state)
