-- No Character.setRace, Character.setAppearanceData, stat writes or item moves.
-- Inventory events only request a scan; body rebuilds run on the GUI frame.
local M = {}
local ITEM = '650-JACK_T60_WearLab.mod'
local VISUAL = '670-JACK_T60_WearLab.mod'
local allowed = {['17-gamedata.quack']=true, ['18019-gamedata.base']=true, ['5276-chareditor.mod']=true}
function M.new(api)
 local tracked, blocked, pools = {}, {}, {}
 local enabled, age, now, allocations = true, .25, 0, 0
 local lastWorld, errorText, lastScanInfo
 local lastCandidate={}
 local function log(s) api.log(s) end
 local function owner(c) return api.owner and api.owner(c) or c:getHandle():toString() end
 local function logical(c) return c.myRace and c.myRace.data and c.myRace.data.stringID end
 local function wearing(c)
  local inv=c:getInventory();if not inv then return false end
  local belt=inv:getSectionOfType(14) -- verified AttachSlot.ATTACH_BELT
  local item=belt and belt:getItem()
  return item~=nil and item.isEquipped and item.data and item.data.stringID==ITEM
 end
 local function fingerprint(c)
  local values = {}
  local items = c:getInventory():getAllItems()
  for i=1,#items do
   local item = items[i]
   values[#values+1] = item.data and item.data.stringID or '?'
  end
  table.sort(values)
  return table.concat(values, '|')
 end
 local function inspect(c,a)
  local n = not a.isCreatingBody and a:getBody() and api.bones(a:getBody()) or nil
  return 'owner='..owner(c)..' logical='..tostring(logical(c))..' visual='..tostring(a.raceData and a.raceData.stringID)..
   ' slots='..tostring(a.slots)..' bones='..tostring(n)..' loading='..tostring(a.isCreatingBody)..' mesh='..tostring(a.bodyFilename), n
 end
 local function identity(c,s)
  assert(owner(c)==s.owner, 'Character identity changed')
  assert((api.characterKey and api.characterKey(c) or c)==s.characterIdentity,'Character pointer changed')
  assert(c.myRace==s.logicalRace, 'Logical RaceData pointer changed')
  assert(logical(c)==s.logicalId, 'Logical race changed')
  assert(c:getInventory()==s.inventory, 'Inventory object changed')
  assert(c:getStats()==s.stats, 'Stats object changed')
  -- In the real engine Character.getAppearanceData forwards to AppearanceBase;
  -- it legitimately returns the active visual pointer after this swap.
  -- Keep the saved original alive, but do not mistake that accessor alias for
  -- a mutation of the logical character/race or immediately roll back.
  local exposed=c:getAppearanceData()
  assert(exposed==s.characterData or exposed==s.app.appearanceData, 'Unexpected appearance data replacement')
 end
 local function edit(a,data,race,female,hair,filename,shaved,originalSlots)
  -- Raw pointer setters are confirmed in the binding source. Keep the original
  -- Character-owned data intact; request the engine's regular deferred rebuild.
  a.appearanceData=data
  a.raceData=race
  a.female=female
  a.hairStyle=hair
  a.shaved=shaved
  a.bodyFilename=filename
  if api.attachmentCache then
   if originalSlots then api.attachmentCache.restore(a,originalSlots)
   else api.attachmentCache.select(a) end
  end
  a.updatedAppearanceData=true
  a.updatedAttachments=true
  a.updateBody=true
  a:notifyDirty()
 end
 local function attachmentPass(a,originalSlots)
  if api.attachmentCache then
   if originalSlots then api.attachmentCache.restore(a,originalSlots)
   else api.attachmentCache.select(a) end
  end
  -- Rebuild the actual weapon attachments only after the new body is stable.
  -- The early flag in edit() can be consumed while its old body still exists.
  a.updatedAttachments=true
  a:notifyDirty()
 end
 local function bodyKey(a)return api.bodyKey and api.bodyKey(a) or a:getBody() end
 local function restore(c,s,why)
  s.state='RESTORING'; s.phase='body';s.waitReason=nil;s.waits=0; s.since=now; s.stable=0;s.attachmentPass=false;s.rebound=false
  local o=s.original
  if api.persistence then api.persistence.forget(s.app) end
  if api.visibility then api.visibility.finish(c,s.app) end
  edit(s.app,o.data,o.race,o.female,o.hair,o.filename,o.shaved,o.slots)
  if api.attachmentCache then assert(s.app.slots==o.slots,'Original attachment cache was not restored') end
  identity(c,s)
  log('RESTORE requested reason='..why..' '..inspect(c,s.app))
 end
 local function capture(c,a)
  local info,n=inspect(c,a)
  assert(n and n~=82, 'Original body skeleton unavailable or already T60')
  local s={owner=owner(c),characterIdentity=api.characterKey and api.characterKey(c) or c,app=a,logicalRace=c.myRace,logicalId=logical(c),inventory=c:getInventory(),stats=c:getStats(),
   characterData=c:getAppearanceData(),original={data=a.appearanceData,race=a.raceData,female=a.female,
   hair=a.hairStyle,filename=a.bodyFilename,shaved=a.shaved,bones=n,slots=a.slots},state='ORDINARY'}
  assert(s.original.data and s.characterData and s.original.race, 'Original appearance data missing')
  assert(s.original.race.stringID==s.logicalId, 'Original visual/logical race differ')
  log('CAPTURE '..info)
  return s
 end
 local function apply(c,s)
  local pool=pools[s.owner]
  if pool and (pool.app~=s.app or pool.characterIdentity~=s.characterIdentity or pool.original~=s.original.data) then
   pools[s.owner]=nil;pool=nil -- Discard Lua reference only; never free or refund budget.
  end
  if not pool then
   assert(allocations<16, 'Session appearance allocation limit reached; restart test')
   local data=api.makeVisual()
   if data then allocations=allocations+1 end -- Count factory results before later checks can fail.
   pool={data=data,race=api.visualRace(),app=s.app,characterIdentity=s.characterIdentity,original=s.original.data}
   assert(pool.data and pool.race and pool.race.stringID==VISUAL, 'T60 visual factory failed')
   pools[s.owner]=pool
  end
  s.state='APPLYING';s.phase='body';s.waitReason=nil;s.waits=0;s.since=now;s.stable=0;s.attachmentPass=false;s.rebound=false;s.animationPass=false
  local before=fingerprint(c)
  if api.visibility then api.visibility.begin(c,s.app) end
  edit(s.app,pool.data,pool.race,false,nil,'./mods/JACK_T60_WearLab/meshes/jack_t60_wear_v08.mesh',false)
  if api.persistence then api.persistence.register(c,s.app,s.original.data,pool.data) end
  identity(c,s)
  assert(fingerprint(c)==before, 'Inventory contents changed during visual switch')
  log('EQUIP requested; identity/race/stats/inventory pointers preserved; original appearance snapshot retained '..inspect(c,s.app))
 end
 local function step(c)
  local id=owner(c); local s=tracked[id];local a=c:getAppearance()
  if s and a~=s.app then
   -- Never dereference an appearance retained across unload/recreation.
   if api.persistence then api.persistence.forget(s.app) end
   tracked[id]=nil;pools[id]=nil;s=nil;log('APPEARANCE replaced; old pointers discarded owner='..id)
  end
  if not a then return end
  local wants=enabled and not blocked[id] and wearing(c)
  if s then
   identity(c,s)
   -- Serialize rebuilds: do not start restoring while the armor mesh is loading.
   if not wants and s.state~='RESTORING' and s.state~='RESTORE_FAILED' and not a.isCreatingBody then restore(c,s,'unequip or suspend') end
   local info,n=inspect(c,a)
   if s.state=='APPLYING' or s.state=='RESTORING' then
    local expected=s.state=='APPLYING' and 82 or s.original.bones
    local target=s.state=='APPLYING' and VISUAL or s.original.race.stringID
    local meshOK=s.state~='APPLYING' or (a.bodyFilename and a.bodyFilename:find('jack_t60_wear_v08.mesh',1,true))
    if n==expected and a.raceData and a.raceData.stringID==target and not a.updateBody and meshOK then s.stable=s.stable+1 else s.stable=0 end
    if s.stable>=2 and not s.attachmentPass then
     if s.state=='APPLYING' and not s.animationPass and api.prepareAnimations then
      api.prepareAnimations(a);s.animationPass=true
     end
     attachmentPass(a,s.state=='RESTORING' and s.original.slots or nil)
     s.attachmentPass=true;s.phase='attachment';s.since=now;s.stable=0
     log('POST-BODY attachment rebuild requested '..info)
    elseif s.stable>=2 and a.updatedAttachments then
     s.stable=0
    elseif s.stable>=2 and not s.rebound and api.attachmentCache and api.attachmentCache.rebind then
     local n,reason=api.attachmentCache.rebind(a)
     if n==-12 then s.waitReason=reason;s.waits=(s.waits or 0)+1 else s.waitReason=nil end
     s.stable=0
     if n~=-12 then s.rebound=true;log('POST-BODY weapon entities rebound='..tostring(n)..' '..info) end
    elseif s.stable>=2 then
     if s.state=='RESTORING' then
      assert(a.appearanceData==s.original.data,'Original appearance pointer not restored')
      log('ORDINARY confirmed; original appearance restored '..info)
      tracked[id]=nil
     else s.state='ARMORED';s.phase='ready';s.bodyKey=bodyKey(a);log('ARMORED confirmed; 82-bone body and attachment rebuild ready '..info) end
    elseif now-s.since>12 then
     blocked[id]=true
     if s.state=='APPLYING' then
      log('APPLY timeout; rolling back '..info);restore(c,s,'apply timeout')
     else
      -- Keep the snapshot for F10/retry, rather than losing recovery data.
      s.state='RESTORE_FAILED';s.phase='failed';log('RESTORE timeout; snapshot retained '..info)
     end
    end
   elseif s.state=='ARMORED' and not a.isCreatingBody and not a.updateBody then
    if n~=82 or not a.raceData or a.raceData.stringID~=VISUAL then
     blocked[id]=true;restore(c,s,'engine replaced armored body')
    elseif bodyKey(a)~=s.bodyKey then
     s.state='APPLYING';s.phase='body';s.waitReason=nil;s.waits=0;s.since=now;s.stable=0;s.attachmentPass=false;s.rebound=false;s.animationPass=false
     log('ARMORED body recreated; waiting to refresh attachments owner='..id)
    elseif api.attachmentCache and api.attachmentCache.select(a)==1 then
     s.state='APPLYING';s.phase='body';s.waitReason=nil;s.waits=0;s.since=now;s.stable=0;s.attachmentPass=false;s.rebound=false;s.animationPass=false
     log('ARMORED attachment cache repaired; entity refresh queued owner='..id)
    end
   end
  elseif wants and not a.isCreatingBody and a:getBody() and allowed[logical(c)] then
   s=capture(c,a);tracked[id]=s
   apply(c,s)
  end
 end
 local function scan()
  local world=api.world()
  local summary='world='..tostring(world~=nil)..' resetting='..tostring(world and world.gameResetting)..
   ' player='..tostring(world and world.player~=nil)..' count='..tostring(world and world.player and #world.player.playerCharacters)
  if summary~=lastScanInfo then lastScanInfo=summary;log('SCAN '..summary) end
  if not world or world.gameResetting or not world.player then
   if next(tracked) then log('WORLD unavailable/resetting; raw pointers discarded') end
   if api.persistence then api.persistence.clear() end
   tracked={};blocked={};pools={};lastWorld=nil;return
  end
  if lastWorld and lastWorld~=world then if api.persistence then api.persistence.clear() end;tracked={};blocked={};pools={} end
  lastWorld=world
  local seen={};local list=world.player.playerCharacters
  for i=1,#list do
   local c=list[i]
   if c and (not api.eligible or api.eligible(c)) and c:isPlayerCharacter() and c:isHuman() then
    local id=owner(c);seen[id]=true
    if _G.JACK_T60_DIAGNOSTICS==true then
    local diagnosticOk,diagnostic=pcall(function()
     local inv=c:getInventory();local parts={}
     if inv then
      local items=inv:getAllItems()
      for j=1,#items do
       local item=items[j]
       parts[#parts+1]=tostring(item.data and item.data.stringID)..':equipped='..tostring(item.isEquipped)..':section='..tostring(item.inventorySection)
      end
     end
     local upper=c:getUpperBodyArmour()
     return 'logical='..tostring(logical(c))..' wearing='..tostring(wearing(c))..
      ' upper='..tostring(upper and upper.data and upper.data.stringID)..' items=['..table.concat(parts,',')..']'
    end)
    local detail=diagnosticOk and diagnostic or 'diagnostic error='..tostring(diagnostic)
    if lastCandidate[id]~=detail then lastCandidate[id]=detail;log('CANDIDATE owner='..id..' '..detail) end
    end
    local ok,err=pcall(step,c)
    if not ok then
     local alreadyBlocked=blocked[id]
     blocked[id]=true
     if not alreadyBlocked then log('BLOCKED owner='..id..' error='..tostring(err)) end
     local s=tracked[id]
     if s and s.state~='RESTORING' and s.state~='RESTORE_FAILED' and c:getAppearance()==s.app then
      local restored,reason=pcall(restore,c,s,'error rollback')
      if not restored then log('ROLLBACK ERROR '..tostring(reason)) end
     end
    end
   end
  end
  for id in pairs(tracked) do if not seen[id] then if api.persistence then api.persistence.forget(tracked[id].app) end;tracked[id]=nil;log('UNLOADED owner='..id..'; snapshot released without dereference') end end
 end
 local C={}
 -- Snapshot cached controller metadata only; never dereference game objects.
 function C.status()
  local result={enabled=enabled,allocations=allocations,allocation_limit=16,pool_entries=0,now=now,owners={}}
  for _ in pairs(pools) do result.pool_entries=result.pool_entries+1 end
  for id,s in pairs(tracked) do
   result.owners[id]={state=s.state,blocked=not not blocked[id],attachmentPass=not not s.attachmentPass,
    rebound=not not s.rebound,animationPass=not not s.animationPass,stable=s.stable or 0,phase=s.phase,since=s.since,elapsed=s.since and (now-s.since) or nil,waitReason=s.waitReason,waits=s.waits or 0}
  end
  for id in pairs(blocked) do
   if not result.owners[id] then result.owners[id]={blocked=true} end
  end
  return result
 end
 function C.reset()
  if api.persistence then api.persistence.clear()end
  tracked={};blocked={};pools={};lastWorld=nil;lastCandidate={}
 end
 function C.tick(dt)
  if not C.frameSeen then C.frameSeen=true;log('FRAME callback active dt='..tostring(dt)) end
  now=now+math.max(0,tonumber(dt) or 0);age=age+math.max(0,tonumber(dt) or 0)
  if age<.25 then return end
  age=0
  local ok,err=pcall(scan)
  if not ok and errorText~=tostring(err) then errorText=tostring(err);log('SCAN ERROR '..errorText) end
 end
 function C.pending() age=.25 end
 function C.renderFault(reason)
  if next(tracked) then
   enabled=false;age=.25
   log('RENDER FAULT; restoring live wearers and suspending: '..tostring(reason))
  end
 end
 function C.loaded(c)
  -- Called only for the character being loaded, never clear other wearers.
  local ok,id=pcall(owner,c)
  if ok then if tracked[id]and api.persistence then api.persistence.forget(tracked[id].app) end;tracked[id]=nil;blocked[id]=nil;pools[id]=nil end
  age=.25
 end
 function C.key(_,key)
  if key==68 then
   enabled=false;age=.25
   -- Retry a failed restoration on F10, on the next frame.
   for _,s in pairs(tracked) do if s.state=='RESTORE_FAILED' then s.state='RECOVER' end end
   log('SUSPEND; restore requested for all live wearers')
  elseif key==87 then enabled=true;blocked={};age=.25;log('RESUME')
  elseif key==65 then
   log('STATUS enabled='..tostring(enabled)..' factory allocations='..allocations)
   local world=api.world()
   if world and not world.gameResetting and world.player then
    local list=world.player.playerCharacters
    for i=1,#list do
     local c=list[i];local a=c and c:getAppearance()
     if a and (not api.eligible or api.eligible(c)) then
      local ok,info=pcall(inspect,c,a)
      if ok then log((tracked[owner(c)] and tracked[owner(c)].state or 'UNTRACKED')..' wearing='..tostring(wearing(c))..' '..info) end
     end
    end
   end
  end
 end
 return C
end
return M
