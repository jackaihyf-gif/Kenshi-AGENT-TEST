-- Mutations are confined to the disposable, paused, unsaved single test actor.
local M={}
function M.new(config)
 local C={};local ffi=require('ffi')
 local function snapshot(c)
  local s=c:getStats();local inv=c:getInventory();local belt=inv:getSectionOfType(14):getItem();local a=belt and belt:isArmour()
  local r={native=assert(_G.JACK_T60_POWER_PROBE)(c),strength_raw=s._strength,strength_base=s:strengthBase(),strength_actual=s:strengthActual(),strength_panel=s:getStrength(),weight=c:getTotalCarryWeight(),attack_blunt=s:getAttackBluntPower(),armour={},stats={},weather={}}
  for _,key in ipairs({'skillMultDamage','skillMultRanged','skillBonusPerception','combatSpeedMultiplier','skillMultDexterity','weaponWeightSpeedMult','encumbranceMult','bluntDamageMult','bluntDamageMin'})do local ok,v=pcall(function()return s[key]end);r.stats[key]=ok and v or tostring(v)end
  if a then
   r.item={id=belt.data.stringID,quality=belt.quality,level=belt:getLevel(),weight=belt:getItemWeight(),price=belt:getValueSingle(true)}
   for _,k in ipairs({'cutResistance','bluntResistance','pierceResistance','cutToStun','athleticsMult','combatSpeedMult','stealthMult','perceptionBonus','damageMult','rangedSkillMult','dexterityMult','combatSkillBonusDef','unarmedBonus','weatherProtectionAmount','weatherProtections'})do r.armour[k]=a[k]end
   for _,name in ipairs({'WA_DUSTSTORM','WA_ACID','WA_BURNING','WA_GAS'})do local v=WeatherAffecting[name];r.weather[name]={enum=v,item=a:getWeatherProtection_simple(v),actor=s:getWeatherProtection(v)}end
  end
  if _G.JACK_T60_LAMP_PROBE then r.light=_G.JACK_T60_LAMP_PROBE(c)end
  return r
 end
 function C.select(c,choice)
  choice=choice or'status'
  if choice=='status'then return snapshot(c)end
  local w=getGameWorld();assert(#w.player.playerCharacters==1 and w.player.playerCharacters[1]==c and c:getName()==config.test_character_name,'Isolated power fixture only')
  assert(w.paused and not getOptionsHolder().autosave,'Pause and disable autosave first')
  if choice=='clock-fast'then w:setGameSpeed(10,false);return {test_clock_speed=10}end
  if choice=='light-sample'then c.needsLightLevel=true;return _G.JACK_T60_LAMP_PROBE(c)end
  local s=c:getStats();local state=_G.JACK_POWER_TEST_STATE
  if not state then state={raw=s._strength,actor=c};_G.JACK_POWER_TEST_STATE=state end
  assert(state.actor==c,'Restore old power fixture first')
  local n=choice:match('^strength:(%d+)$')
  if n then n=tonumber(n);assert(n==30 or n==50 or n==51 or n==80);s._strength=n
  elseif choice=='isolate-armour'then
   assert(not state.armours,'Restore existing armor fixture first');local inv=c:getInventory();local main=inv:getSection('main');state.width=main.width;state.height=main.height
   inv:resizeSection(main,20,20,false);state.armours={}
   for _,name in ipairs({'head','armour','shirt','legs','boots','backpack_attach'})do local section=inv:getSection(name);local item=section and section:getItem()
    if item then assert(main:hasRoomForItem(item.data,1));assert(section:removeItem(item));assert(main:addItem(item,1));state.armours[#state.armours+1]=item end
   end
   inv:notifyModified();c:recalculateTotalEquipmentSkillBonus();return snapshot(c)
  elseif choice=='restore'then
   s._strength=state.raw
   if state.armours then local inv=c:getInventory();for _,item in ipairs(state.armours)do assert(inv:equipItem(item),'Could not restore original inner armor')end;inv:resizeSection(inv:getSection('main'),state.width,state.height,false);inv:notifyModified()end
   _G.JACK_POWER_TEST_STATE=nil
  elseif choice=='calculate'then c:recalculateTotalEquipmentSkillBonus();s:_recalculateStats()
  elseif choice=='weight-probes'then
   local r=snapshot(c);r.probes={}
   for _,kg in ipairs({20,30,40,50,60})do s:_calculateWeaponWeightSpeedMultiplier(kg);r.probes[tostring(kg)]={speed=s.weaponWeightSpeedMult,weight_xp=s.weaponWeightXPMult} end
   s:_calculateWeaponWeightSpeedMultiplier(s.weaponWeight);r.encumbrance_calculated=s:_calculateEncumberanceMult();return r
  elseif choice=='weather-probe'or choice=='weather-control'then
   local inv=c:getInventory();local belt=inv:getSectionOfType(14):getItem()
   if choice=='weather-probe'then assert(belt and belt.data.stringID=='650-JACK_T60_WearLab.mod','Wear armor first')else assert(not belt or belt.data.stringID~='650-JACK_T60_WearLab.mod','Unequip power armor for the control')end
   assert(not c:isInjured(false),'Healthy weather test actor required');local med=c:getMedical();local r={}
   local function health()local v={};for gd,p in pairs(med.status)do v[gd.stringID]={flesh=p.flesh,stun=p.fleshStun}end;return v end
   for _,method in ipairs({'gettingAcidRain','gettingGassed','gettingBurnt','gettingWindyface','gettingAcidWater','gettingAcidFeet'})do
    local before=health();local affected=med[method](med,1);local after=health();r[method]={before=before,after=after,affected=affected}
   end
   c:healCompletely();return r
  else error('Unknown power fixture')end
  return snapshot(c)
 end
 return C
end
return M
