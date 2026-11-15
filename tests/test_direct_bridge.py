import ctypes
import json
import os
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest

from kenshi_test.adapters.base import Deadline
from kenshi_test.bridge import LuaBridge, validate_control
from kenshi_test.errors import AdapterError, ConfigError, OperationTimeout


def configuration(tmp_path):
    config = {"token": "a" * 64, "root": tmp_path.as_posix(), "test_character_name": "Test T60"}
    (tmp_path / "bridge-config.json").write_text(json.dumps(config), "utf-8")
    return config


def test_waits_for_matching_response_and_rejects_simulation(tmp_path):
    configuration(tmp_path)
    (tmp_path / "response.json").write_text(json.dumps({"id": "stale", "ok": True}), "utf-8")

    def server():
        while not (tmp_path / "request.ini").exists():
            time.sleep(.005)
        fields = dict(line.split("=", 1) for line in
                      (tmp_path / "request.ini").read_text("utf-8").splitlines())
        (tmp_path / "response.json").write_text(json.dumps({
            "id": fields["id"], "protocol": 1, "ok": True, "simulated": True,
        }), "utf-8")

    thread = threading.Thread(target=server)
    thread.start()
    try:
        with pytest.raises(AdapterError, match="Not a real"):
            LuaBridge(tmp_path).call("status", Deadline(2))
    finally:
        thread.join(timeout=3)
    assert not (tmp_path / "client.lock").exists()


def test_timeout_releases_lock(tmp_path):
    configuration(tmp_path)
    with pytest.raises(OperationTimeout):
        LuaBridge(tmp_path).call("status", Deadline(.1))
    assert not (tmp_path / "client.lock").exists()


def test_rejects_unsafe_movement_before_sending():
    with pytest.raises(ConfigError):
        validate_control("move", "1-2-3", "walk", float("nan"), 0, 10)
    with pytest.raises(ConfigError):
        validate_control("move", "1-2-3", "walk", 65, 0, 10)
    with pytest.raises(ConfigError):
        validate_control("move", "1-2\ncommand=release", "walk", 0, 0, 10)


@pytest.fixture
def lua(tmp_path):
    library = os.environ.get("KENSHI_TEST_LUA51")
    if not library:
        pytest.skip("Set KENSHI_TEST_LUA51 to exercise the installed LuaJIT runtime")
    dll = ctypes.CDLL(library)
    dll.luaL_newstate.restype = ctypes.c_void_p
    dll.luaL_openlibs.argtypes = [ctypes.c_void_p]
    dll.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    dll.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    dll.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    dll.lua_tolstring.restype = ctypes.c_char_p
    dll.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
    dll.lua_close.argtypes = [ctypes.c_void_p]
    state = dll.luaL_newstate()
    dll.luaL_openlibs(state)

    def execute(code):
        dll.lua_settop(state, 0)
        result = dll.luaL_loadstring(state, code.encode("utf-8"))
        if not result:
            result = dll.lua_pcall(state, 0, 0, 0)
        assert result == 0, dll.lua_tolstring(state, -1, None)

    config = configuration(tmp_path)
    module = (Path(__file__).resolve().parents[1] /
              "integration/kenshilua/agent_bridge.lua").as_posix()
    execute("""
      movement={speedOrders=2,halted=false,halt=function(self)self.halted=true end}
      character={movement=movement,
       isPlayerCharacter=function()return true end,
       getHandle=function()return {toString=function()return '1-2-3' end} end,
       getName=function()return 'Test T60' end,
       getPosition=function()return {x=10,y=2,z=20} end,
       getAppearance=function()return {raceData={stringID='visual'}} end,
       getUpperBodyArmour=function()return {data={stringID='test'}} end,
       getMovementSpeed=function()return 0 end,
       getMovementSpeedOrders=function()return movement.speedOrders end,
       setDestination=function(self,p)destination=p end,
       isInCombatMode=function()return false end,
       isHuman=function()return {sheatheWeapon=function()sheathed=true end} end}
      world={player={playerCharacters={character}}}
    """)
    execute("api={world=function()return world end,simulated=true}")
    execute(f"service=dofile({json.dumps(module)}).new(" +
            "{root=" + json.dumps(config["root"]) + ",token='" + config["token"] +
            "',test_character_name='Test T60'}," +
            "api)")

    def request(command="status", **kwargs):
        fields = {"protocol": 1, "token": config["token"], "id": uuid4().hex,
                  "expires": int(time.time()) + 10, "command": command} | kwargs
        (tmp_path / "request.ini").write_text(
            "\n".join(f"{k}={v}" for k, v in fields.items()), "utf-8")
        execute("service.tick(.3)")
        return json.loads((tmp_path / "response.json").read_text("utf-8"))

    try:
        yield execute, request
    finally:
        dll.lua_close(state)


def test_actual_luajit_rpc_control_readback_and_restore(lua):
    execute, request = lua
    status = request()
    assert status["ok"] and status["simulated"]
    session = status["session"]
    result = request("move", owner="1-2-3", session=session, mode=0, duration=2, dx=5, dz=-2)
    assert result["ok"]
    assert result["state"]["characters"]["1-2-3"]["gait_order"] == 0
    execute("assert(destination.x==15 and destination.y==2 and destination.z==18)")
    execute("service.tick(3);assert(movement.speedOrders==2 and movement.halted)")
    result = request("sheathe", owner="1-2-3", session=session)
    assert result["ok"]
    execute("assert(sheathed)")


def test_actual_luajit_rejects_stale_session_bad_owner_and_bad_offset(lua):
    execute, request = lua
    session = request()["session"]
    for kwargs in (
        {"owner": "1-2-3", "session": "old", "dx": 1},
        {"owner": "8-8-8", "session": session, "dx": 1},
        {"owner": "1-2-3", "session": session, "dx": 1000},
    ):
        result = request("move", mode=0, duration=2, dz=0, **kwargs)
        assert not result["ok"]
        execute("assert(movement.speedOrders==2 and destination==nil)")


def test_actual_luajit_restore_respects_new_user_speed(lua):
    execute, request = lua
    session = request()["session"]
    assert request("gait", owner="1-2-3", session=session, mode=0, duration=1)["ok"]
    execute("movement.speedOrders=1;service.tick(2);assert(movement.speedOrders==1)")


def test_new_test_never_replaces_loaded_session_and_runs_only_once(lua):
    execute, request = lua
    execute("api.new_test=function()created=(created or 0)+1 end")
    session = request()["session"]
    assert not request("new_test", session=session)["ok"]
    execute("assert(created==nil);world.player.playerCharacters={}")
    result = request("new_test", session=session)
    assert result["ok"] and result["state"]["phase"] == "test_creation_requested"
    assert not request("new_test", session=session)["ok"]
    execute("assert(created==1)")


def test_standing_orders_are_used_and_restored_when_api_available(lua):
    execute, request = lua
    execute("""
      api.set_gait=function(c,mode)
       standing_calls=(standing_calls or 0)+1;movement.speedOrders=mode
      end
      api.get_gait=function()return movement.speedOrders end
    """)
    session = request()["session"]
    assert request("gait", session=session, owner="1-2-3", mode=1, duration=1)["ok"]
    execute("assert(standing_calls==1);service.tick(2);" +
            "assert(standing_calls==2 and movement.speedOrders==2)")


def test_player_order_api_is_used_instead_of_low_level_destination(lua):
    execute, request = lua
    execute("""
     api.move=function(c,p)player_destination=p end
     api.halt=function()player_halted=true end
     character.setDestination=function()error('Low-level movement must not run')end
    """)
    session = request()["session"]
    assert request("move", session=session, owner="1-2-3", mode=0,
                   duration=1, dx=5, dz=0)["ok"]
    execute("assert(player_destination.x==15);service.tick(2);assert(player_halted)")


@pytest.mark.parametrize('command', ['mounts', 'motion_trace'])
def test_native_diagnostic_requires_explicit_flag_and_exact_owner(lua, command):
    execute, request = lua
    execute(f"api.{command}=function(c,on)mount_calls=(mount_calls or 0)+1;mount_enabled=on end")
    session = request()["session"]
    assert not request(command, session=session, owner="1-2-3", enabled="yes")["ok"]
    assert not request(command, session=session, owner="9-9-9", enabled=1)["ok"]
    execute("assert(mount_calls==nil)")
    assert request(command, session=session, owner="1-2-3", enabled=0)["ok"]
    execute("assert(mount_calls==1 and mount_enabled==false)")
    assert request(command, session=session, owner="1-2-3", enabled=1)["ok"]
    execute("assert(mount_calls==2 and mount_enabled==true)")
