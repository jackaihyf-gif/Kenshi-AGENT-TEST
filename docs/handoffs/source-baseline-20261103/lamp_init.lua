local identity=require('character_identity')
-- Real native head light, pooled safely across toggles; eyes use material_native.
local ffi=require('ffi');local clock=require('t60_lighting_clock')
ffi.cdef[[typedef struct {float x,y,z;} T60PhysicalLampVector;
int T60_physical_lamp_ready(void);int T60_physical_lamp_update(void*,void*,const T60PhysicalLampVector*,int);
void T60_physical_lamp_forget_world(void);int T60_physical_lamp_probe(void*,char*,size_t);
int T60_lamp_ready(void);int T60_lamp_probe(void*,int,char*,size_t);]]
local root='D:/steam/steamapps/common/Kenshi/mods/JACK_T60_WearLab/plugin/'
local lamp=ffi.load(root..'T60PhysicalLamp_v092.dll');assert(lamp.T60_physical_lamp_ready()==1,'T60 physical lamp exact-build ABI unavailable')
local diagnostic=ffi.load(root..'T60LampRuntime_v091.dll');assert(diagnostic.T60_lamp_ready()==1,'Native light diagnostics unavailable')
local raw=function(x)return x and ffi.cast('void**',x)[0]or nil end
local headPosition=ffi.new('T60PhysicalLampVector');local lightData;local dataAge=1
local tracked={};local worldTag,playerTag;local epochTag;local enabled,failed=true,false;local created,removed=0,0
local function off(row)
 assert(lamp.T60_physical_lamp_update(row.app,nil,nil,0)>=0,'Lamp pool disable failed');removed=removed+1
end
identity.onEpoch('lamp reset',function()lamp.T60_physical_lamp_forget_world();tracked={};lightData=nil;dataAge=1;worldTag=nil;playerTag=nil;epochTag=nil end)
_G.JACK_T60_LAMP_ENABLE=function(value)enabled=value==true end
_G.JACK_T60_LAMP_PROBE=function(c)
 local a=c:getAppearance();local buffer=ffi.new('char[2048]');assert(lamp.T60_physical_lamp_probe(raw(a),buffer,2048)>=0)
 local text=ffi.string(buffer);local out={cached_light=c:getLightLevel(),active=text:find('"active":true',1,true)~=nil,native=text,created=created,removed=removed,enabled=enabled,failed=failed,night=clock.isNight(getGameWorld()),eyes_night=_G.JACK_T60_EYE_NIGHT_STATE and _G.JACK_T60_EYE_NIGHT_STATE()or false,stats={}}
 for _,stat in ipairs({24,35,36})do local b=ffi.new('char[1024]');assert(diagnostic.T60_lamp_probe(raw(c:getStats().medical),stat,b,1024)>=0);out.stats[tostring(stat)]=ffi.string(b)end
 return out
end
identity.onFrame('lamp',function(dt)
 if failed then return end
 local ok,err=pcall(function()
  local w=getGameWorld();local player=w and w.player
  if not w or w.gameResetting or w~=worldTag or player~=playerTag or epochTag~=identity.epoch() then lamp.T60_physical_lamp_forget_world();tracked={};lightData=nil;dataAge=1;worldTag=w;playerTag=player;epochTag=identity.epoch() end
  if not w or w.gameResetting or not player then return end
  local seen={};local list=player.playerCharacters
  dataAge=dataAge+math.max(0,tonumber(dt)or 0)
  if dataAge>=1 then lightData=w.gamedata:getData('690-JACK_T60_WearLab.mod',88);dataAge=0 end
  local data=lightData;local night=enabled and #list>0 and clock.isNight(w)or false
  for i=1,#list do
   local c=list[i];if identity.eligible(c)then local key=identity.owner(c);seen[key]=true;local row=tracked[key];local a=c:getAppearance();local app=raw(a)
   if row and row.app~=app then off(row);tracked[key]=nil;row=nil end
   local inv=c:getInventory();local slot=inv and inv:getSectionOfType(14);local belt=slot and slot:getItem()
   local wants=enabled and night and not c:isDead()and belt and belt.isEquipped and belt.data and belt.data.stringID=='650-JACK_T60_WearLab.mod'and a and not a.isCreatingBody and not a.updateBody and a.raceData and a.raceData.stringID=='670-JACK_T60_WearLab.mod'
   if wants then
    assert(data,'Restart required for private LIGHT record');local p=a:getBonePosition('Bip01 Head');assert(p.x~=0 or p.y~=0 or p.z~=0,'T60 head bone unavailable')
    headPosition.x=p.x;headPosition.y=p.y;headPosition.z=p.z;assert(lamp.T60_physical_lamp_update(app,raw(data),headPosition,1)==1,'Native headlamp update failed')
    if not row then local b=ffi.new('char[2048]');assert(lamp.T60_physical_lamp_probe(app,b,2048)>=0 and ffi.string(b):find('"active":true',1,true),'Native headlamp ownership validation failed')end
    if not row then tracked[key]={app=app};created=created+1 end
   elseif row then off(row);tracked[key]=nil end
  end
  end
  for key,row in pairs(tracked)do if not seen[key]then off(row);tracked[key]=nil end end
 end)
 if not ok then failed=true;enabled=false;lamp.T60_physical_lamp_forget_world();tracked={};print('[JACK T60 Lamp v0.9.2] DISABLED '..tostring(err))end
end)
Events.on('InputHandler::keyDownEvent',function(_,key)if key==68 then enabled=false elseif key==87 and not failed then enabled=true end end)
print('[JACK T60 Lamp v0.9.2] Real head light through native lantern queries; 20:00-06:00; no brightness/stat overrides')
