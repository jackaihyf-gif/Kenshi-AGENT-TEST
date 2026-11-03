"""Ownership and bounds for temporary isolated-test loadouts in actual LuaJIT."""

import ctypes
import os
from pathlib import Path


def test_isolated_weapon_loadout_preserves_original_and_bounds_generation():
    runtime = os.environ.get("KENSHI_TEST_LUA51")
    if not runtime:
        import pytest

        pytest.skip("Set KENSHI_TEST_LUA51 to exercise the installed LuaJIT runtime")
    lib = ctypes.CDLL(str(runtime))
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
    lib.luaL_openlibs(state)

    def run(code):
        status = lib.luaL_loadstring(state, code.encode())
        if not status:
            status = lib.lua_pcall(state, 0, 0, 0)
        assert status == 0, lib.lua_tolstring(state, -1, None).decode()

    try:
        module = Path(__file__).parents[1] / "integration/kenshilua/weapon_test_controller.lua"
        run("Controller=assert(loadfile(" + repr(module.as_posix()) + "))()")
        run((Path(__file__).parent / "fixtures/weapon_loadout.lua").read_text("utf-8"))
    finally:
        lib.lua_close(state)
