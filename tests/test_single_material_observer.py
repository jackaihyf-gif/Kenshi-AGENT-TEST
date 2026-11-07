"""Exercise the actual read-only module-selection callback in LuaJIT."""

import ctypes
import os
from pathlib import Path

import pytest


def test_single_observer_known_versions_and_fail_closed_cases():
    runtime = os.environ.get("KENSHI_TEST_LUA51")
    if not runtime:
        pytest.skip("Set KENSHI_TEST_LUA51 to exercise the read-only observer")
    root = Path(__file__).parents[1]
    source = (root / "integration/kenshilua/game_ops.lua").read_text("utf8")
    body = source.split("material_slots=function()", 1)[1].split("    end})", 1)[0]
    setup = r"""
local plugins='D:/synthetic/plugin'
local loaded={}
local value=5
local wrongPath=false
local missingExport=false
local ffi={cdef=function()end,new=function()return {}end,
 string=function(p)return p.path end,cast=function(_,fn)return fn end,
 load=function()error('Never load a DLL from the observer')end}
local kernel={
 GetModuleHandleA=function(path)return loaded[path] and path or nil end,
 GetModuleFileNameA=function(module,out,capacity)
  assert(capacity==32768);out.path=wrongPath and 'D:/wrong.dll' or module
  return #out.path
 end,
 GetProcAddress=function(module,name)
  assert(loaded[module] and name=='T60_material_slots')
  if missingExport then return nil end
  return function()return value end
 end,
 LoadLibraryA=function()error('Never load a DLL from the observer')end,
}
local names={'T60MaterialBridge_v091.dll','T60MaterialBridge_v091_bindingfix_20261106.dll',
 'T60MaterialBridge_v091_isolatednormal_20261107.dll'}
local function path(name)return (plugins..'/'..name):gsub('/',string.char(92))end
local function one(name)loaded={[path(name)]=true}end
"""
    checks = r"""
for _,name in ipairs(names)do one(name);assert(observe()==5)end
loaded={};assert(not pcall(observe))
one(names[1]);loaded[path(names[2])]=true;assert(not pcall(observe))
one(names[3]);wrongPath=true;assert(not pcall(observe));wrongPath=false
missingExport=true;assert(not pcall(observe));missingExport=false
for _,n in ipairs({-1,33,1.5})do value=n;assert(not pcall(observe))end
value=0;assert(observe()==0);value=32;assert(observe()==32)
"""
    code = setup + "\nlocal observe=function()\n" + body + "\nend\n" + checks
    lib = ctypes.CDLL(runtime)
    lib.luaL_newstate.restype = ctypes.c_void_p
    lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lib.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lib.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    lib.lua_tolstring.restype = ctypes.c_char_p
    lib.lua_close.argtypes = [ctypes.c_void_p]
    state = lib.luaL_newstate()
    assert state
    lib.luaL_openlibs(state)
    try:
        result = lib.luaL_loadstring(state, code.encode("utf8"))
        if not result:
            result = lib.lua_pcall(state, 0, 0, 0)
        assert result == 0, lib.lua_tolstring(state, -1, None)
    finally:
        lib.lua_close(state)
