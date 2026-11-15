-- Reversible self-aid fixture for the single configured test actor only.
local M={}
function M.new(config)
 local ffi=require('ffi')
 local function worldkey(w)return w and tostring(ffi.cast('void**',w)[0]) or 'nil'end
 local lease
 local C={}
 local function guard(c)
  local w=assert(getGameWorld());assert(#w.player.playerCharacters==1 and c==w.player.playerCharacters[1] and c:getName()==config.test_character_name,'Service fixture requires isolated actor')
  assert(w.paused and not getOptionsHolder().autosave,'Pause and disable autosave first')
  assert(not c:isDead() and not c:isUnconcious() and not c:isInCombatMode(true,true),'Actor must be conscious and out of combat')
  return w
 end
 function C.stop()
  if not lease then return {restored=true}end
  local l=lease;lease=nil;local w=getGameWorld()
  if worldkey(w)~=l.world then return {unloaded=true}end
  local c=l.handle:getCharacter();if not c or c:getName()~=config.test_character_name then return {unloaded=true}end
  c:clearAllAIGoals();c.movement:halt()
  local med=c:getMedical();local arm=med.leftArm
  arm.flesh=l.flesh;arm.fleshStun=l.stun;arm.bandaging=l.bandage;arm:updateDerivedHealths();med.blood=l.blood;med:precalculateFirstAidNeedScore()
  c:getStats().medic=l.medic
  return {restored=true}
 end
 function C.select(c,choice)
  assert(choice=='selfaid' or choice=='status' or choice=='stop','Unknown service fixture')
  if choice=='stop'then guard(c);return C.stop()end
  local med=c:getMedical();local arm=med.leftArm
  if choice=='status'then return {active=lease~=nil,flesh=arm.flesh,bandaging=arm.bandaging,need=med:scoreFirstAidNeed(false)}end
  local w=guard(c);assert(not lease,'Stop previous fixture first');assert(not c:isInjured(false),'Fixture requires a healthy baseline')
  local inv=c:getInventory();local all=inv:getAllItems();local kit
  for i=1,#all do if all[i].data and all[i].data.stringID=='209-gamedata.base' then kit=all[i];break end end
  assert(kit,'The service-test start must supply a basic first aid kit')
  lease={world=worldkey(w),handle=c:getHandle(),flesh=arm.flesh,stun=arm.fleshStun,bandage=arm.bandaging,blood=med.blood,medic=c:getStats().medic,expires=os.time()+20}
  arm.flesh=arm:maxHealth()*.65;arm.fleshStun=0;arm.bandaging=0;arm:updateDerivedHealths();med:precalculateFirstAidNeedScore()
  c:clearAllAIGoals();c:addGoal(TaskType.FIRST_AID_ORDER,c)
  return {fixture='selfaid',maximum_seconds=20,kit='209-gamedata.base',need=med:scoreFirstAidNeed(false)}
 end
 function C.frame()
  if lease and os.time()>=lease.expires then local w=getGameWorld();if w then w:userPause(true)end;C.stop()end
 end
 return C
end
return M
