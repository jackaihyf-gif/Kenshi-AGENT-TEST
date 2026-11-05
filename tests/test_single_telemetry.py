"""Run the isolated read-only observer's rejection cases in actual LuaJIT."""

import ctypes
import os
from pathlib import Path

import pytest


def test_single_telemetry_rejects_unsafe_and_unknown_without_counter_reset():
    runtime = os.environ.get("KENSHI_TEST_LUA51")
    if not runtime:
        pytest.skip("Set KENSHI_TEST_LUA51 to exercise the installed LuaJIT runtime")
    lib = ctypes.CDLL(runtime)
    lib.luaL_newstate.restype = ctypes.c_void_p
    for name, args in [
        ("luaL_openlibs", [ctypes.c_void_p]),
        ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
        ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
        ("lua_close", [ctypes.c_void_p]),
        ("lua_tolstring", [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]),
    ]:
        getattr(lib, name).argtypes = args
    lib.lua_tolstring.restype = ctypes.c_char_p
    state = lib.luaL_newstate()
    assert state
    lib.luaL_openlibs(state)

    def run(code):
        result = lib.luaL_loadstring(state, code.encode("utf-8"))
        if not result:
            result = lib.lua_pcall(state, 0, 0, 0)
        assert result == 0, lib.lua_tolstring(state, -1, None)

    try:
        root = Path(__file__).parents[1]
        module = root / "integration/kenshilua/single_telemetry.lua"
        run("Observer=assert(loadfile(" + repr(module.as_posix()) + "))()")
        run((root / "tests/fixtures/single_telemetry.lua").read_text("utf-8"))
    finally:
        lib.lua_close(state)
