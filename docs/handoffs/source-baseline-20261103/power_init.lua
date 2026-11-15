local identity=require('character_identity')
-- Event-driven instance calibration; original effective-strength native hook.
local ffi=require('ffi')
ffi.cdef[[int T60_power_ready(void);void T60_power_target(void*);int T60_power_probe(void*,char*,size_t);]]
local dll=ffi.load('D:/steam/steamapps/common/Kenshi/mods/JACK_T60_WearLab/plugin/T60PowerRuntime_v092.dll')
assert(dll.T60_power_ready()==1,'T60 power exact-build hook unavailable; restart required')
local raw=function(x)return x and ffi.cast('void**',x)[0]or nil end
local previousWorld,previousData
local pending={};local sweepAge=2;local dataAge=.25;local beltAge=.25;local belts={};local epochTag
identity.onEpoch('power reset',function()dll.T60_power_target(nil);previousWorld=nil;previousData=nil;pending={};belts={};epochTag=nil end)
local properties={weight=18,combatSpeedMult=1.10,athleticsMult=.95,stealthMult=.60}
local work={inventories=0,items=0,full_sweeps=0,event_sweeps=0}
_G.JACK_T60_POWER_WORK=function()return work end
local function normalizeInventory(c)
 local inv=c:getInventory();if not inv then return end
 work.inventories=work.inventories+1
 local changed=false
 local function normalize(item)
  work.items=work.items+1
  if item and item.data and item.data.stringID=='650-JACK_T60_WearLab.mod' then
   local armour=item:isArmour()
   if armour then
    for key,value in pairs(properties)do
     local object=key=='weight'and item or armour
     if math.abs(object[key]-value)>.0001 then object[key]=value;changed=true end
    end
   end
  end
 end
 local items=inv:getAllItems();for i=1,#items do normalize(items[i])end
 local belt=inv:getSectionOfType(14);if belt then normalize(belt:getItem())end
 if changed then inv:recalculateTotalWeight();c:recalculateTotalEquipmentSkillBonus()end
end
local function sync(dt,force)
 local w=getGameWorld()
 if not w or w.gameResetting then
  if previousWorld or previousData then dll.T60_power_target(nil)end
  previousWorld=nil;previousData=nil;pending={};sweepAge=2;dataAge=.25;return
 end
 if w~=previousWorld or epochTag~=identity.epoch() then
  previousWorld=w;previousData=nil;pending={};belts={};beltAge=.25;sweepAge=2;dataAge=.25;epochTag=identity.epoch()
 end
 dataAge=dataAge+math.max(0,tonumber(dt)or 0)
 if force or dataAge>=.25 then
  dataAge=0
  local data=w.gamedata and w.gamedata:getData('650-JACK_T60_WearLab.mod',3)
  if data~=previousData then dll.T60_power_target(raw(data));previousData=data end
 end
 beltAge=beltAge+math.max(0,tonumber(dt)or 0)
 if w.player and (force or beltAge>=.25)then
  beltAge=0;local current={};local players=w.player.playerCharacters
  for i=1,#players do local c=players[i];if identity.eligible(c)then local id=identity.owner(c)
   local inv=c:getInventory();local section=inv and inv:getSectionOfType(14);local item=section and section:getItem()
   local pointer=raw(item);current[id]=pointer
   if pointer~=belts[id]then pending[id]=true end end
  end
  belts=current
 end
 sweepAge=sweepAge+math.max(0,tonumber(dt)or 0)
 if not w.player or(sweepAge<2 and not next(pending))then return end
 local full=sweepAge>=2
 if full then sweepAge=0;work.full_sweeps=work.full_sweeps+1 else work.event_sweeps=work.event_sweeps+1 end
 local list=w.player.playerCharacters
 for i=1,#list do local c=list[i];if identity.eligible(c)and(full or pending[identity.owner(c)])then normalizeInventory(c)end end
 pending={}
end
identity.onFrame('power',sync)
_G.JACK_T60_POWER_PROBE=function(c)
 sync(0,true);normalizeInventory(c);local out=ffi.new('char[2048]');local n=dll.T60_power_probe(raw(c:getStats()),out,2048)
 assert(n>=0,'Strength probe failed '..tonumber(n));return ffi.string(out)
end
print('[JACK T60 Power] Effective strength x1.50; GUI belt-change calibration, 2-second elapsed-time fallback')
