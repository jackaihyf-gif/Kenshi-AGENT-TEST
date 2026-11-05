"Ownership and bounds for temporary isolated-test loadouts in actual LuaJIT."

import ctypes
from pathlib import Path


def test_isolated_weapon_loadout_preserves_original_and_bounds_generation():
    runtime = Path(
        "D:\\JACK\\KenshiArmorMod\\tools\\KenshiLua_research\\distribution\\KenshiLua\\lua51.dll"
    )
    if not runtime.exists():
        import pytest

        pytest.skip("Local LuaJIT is unavailable")
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
        run(
            "\nlocal isolated,paused,auto=true,true,false\nl"
            "ocal world={};local made,removed=0,0;local ma"
            "nufacturer={}\nlocal inv={};local primary;loca"
            "l original\nlocal function item(id,generated)\n"
            " local x={data={stringID=id,name=id},manufact"
            "urerData=manufacturer,isInInventory=false,isE"
            "quipped=false,generated=generated}\n function "
            "x:isWeapon()return self end\n function x:getCa"
            "tegory()return 1 end\n function x:getCategory_"
            "animationOverride()return 1 end\n function x:g"
            "etItemWeight()return 2 end\n function x:getInv"
            "entory()return self.inv end\n return x\nend\nloc"
            "al bag={width=8,height=6};local equipped={}\nf"
            "unction bag:hasRoomForItem()return self.width"
            "==20 end\nfunction inv:resizeSection(section,w"
            ",h,clear)assert(section==bag and clear==false"
            ");section.width=w;section.height=h end\nfuncti"
            "on bag:addItem(x)x.inv=inv;x.isInInventory=tr"
            "ue;x.isEquipped=false;x.inventorySection='mai"
            "n';return true end\nfunction equipped:removeIt"
            "em(x)assert(primary==x);primary=nil;x.isEquip"
            "ped=false;return true end\nfunction equipped:a"
            "ddItem(x)primary=x;x.isEquipped=true;return t"
            "rue end\nfunction inv:getSection(name)return n"
            "ame=='main' and bag or equipped end\nfunction "
            "inv:getPrimaryWeapon()return primary end\nfunc"
            "tion inv:getSecondaryWeapon()return nil end\nf"
            "unction inv:getAllItems()local list={};if ori"
            "ginal and original.inv==self then list[#list+"
            "1]=original end;if primary and primary~=origi"
            "nal then list[#list+1]=primary end;return lis"
            "t end\nfunction inv:equipItem(x)primary=x;x.in"
            "v=self;x.isInInventory=true;x.isEquipped=true"
            ";x.inventorySection='weapon';return true end\n"
            "function inv:addItem(x)bag:addItem(x);primary"
            "=x;return true end\nfunction inv:removeItemAut"
            "oDestroy(x,n)assert(x.generated and x~=origin"
            "al and n==1);removed=removed+1;if primary==x "
            "then primary=nil end;x.inv=nil;return true en"
            "d\nfunction inv:notifyModified()end\nlocal c={}"
            "\nlocal fixtureStats={_strength=50}\nfunction c"
            ":getStats()return fixtureStats end\nfunction c"
            ":getInventory()return inv end\nfunction c:getC"
            "urrentWeapon()return primary end\nfunction c:g"
            "etHandle()return {toString=function()return '"
            "1-2-3' end} end\nfunction c:drawWeapon(x,secti"
            "on)assert(x==primary and section==x.inventory"
            "Section);self.drawn=x;return true end\nfunctio"
            "n c:healCompletely()self.healed=true end\nfunc"
            "tion c:generateWeapon(data,m)assert(m==manufa"
            "cturer);made=made+1;return item(data.stringID"
            ",true) end\noriginal=item('original',false);in"
            "v:equipItem(original)\nlocal ctrl=Controller.n"
            "ew({guard=function()assert(isolated)end,world"
            "=function()return world end,\n paused=function"
            "()return paused end,autosave=function()return"
            " auto end,lookup=function(id)return {stringID"
            "=id,name=id}end})\nassert(not pcall(ctrl.selec"
            "t,c,'arbitrary-id') and made==0 and primary=="
            "original)\nauto=true;assert(not pcall(ctrl.sel"
            "ect,c,'katana') and made==0);auto=false\npause"
            "d=false;assert(not pcall(ctrl.select,c,'katan"
            "a') and made==0);paused=true\nisolated=false;a"
            "ssert(not pcall(ctrl.select,c,'katana') and m"
            "ade==0);isolated=true\nassert(ctrl.select(c,'r"
            "eset-health').fixture_health_reset and c.heal"
            "ed and made==0)\nlocal fixture=ctrl.select(c,'"
            "gait-fixture');assert(fixture.fixture_only an"
            "d fixture.original_strength==50 and fixtureSt"
            "ats._strength==150)\nassert(not pcall(ctrl.sel"
            "ect,c,'gait-fixture'))\nassert(ctrl.select(c,'"
            "gait-restore').restored and fixtureStats._str"
            "ength==50)\nctrl.select(c,'katana');assert(pri"
            "mary.generated and original.inv==inv and not "
            "original.isEquipped)\nctrl.select(c,'draw');as"
            "sert(c.drawn==primary and not original.isEqui"
            "pped)\nctrl.select(c,'polearm');assert(made==2"
            " and removed==1)\nctrl.select(c,'original');as"
            "sert(primary==original and removed==2 and ori"
            "ginal.isEquipped)\nassert(bag.width==8 and bag"
            ".height==6,'Original inventory dimensions mus"
            "t be restored')\nassert(ctrl.select(c,'status'"
            ").primary.id=='original')\nctrl.select(c,'orig"
            "inal');assert(removed==2)\nfor i=1,8 do ctrl.s"
            "elect(c,'heavy')end\nassert(not pcall(ctrl.sel"
            "ect,c,'heavy') and made==10)\nctrl.select(c,'o"
            "riginal');assert(primary==original and origin"
            "al.inv==inv)\n"
        )
    finally:
        lib.lua_close(state)
