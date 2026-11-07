-- Pure GUI-thread registry. A handle is a locator, not a lifetime identity.
local M={}
function M.new(api)
 local rows={};local epoch,serial,frame,migrations=0,0,0,0
 local worldKey;local sourcegeneration;local reason;local lastEpochReason;local fault;local running=false;local deferred=false;local gap=0
 local S={}
 local function ptr(x)return x~=nil and api.pointer(x)or nil end
 local function key(x)local p=ptr(x);return p~=nil and tostring(p)or nil end
 local function fail(w,why)
  if not fault then fault=tostring(why);api.log('IDENTITY STOP: '..fault);if w then pcall(api.pause,w)end end
  return false
 end
 local function fingerprint(c)
  return {appearance=ptr(c:getAppearance()),inventory=ptr(c:getInventory()),stats=ptr(c:getStats()),race=ptr(c.myRace)}
 end
 local function complete(f)return f.appearance and f.inventory and f.stats and f.race end
 local function same(a,b)return a.appearance==b.appearance and a.inventory==b.inventory and a.stats==b.stats and a.race==b.race end
 function S.refresh()
  if running then return false end;running=true
  local probeOK,observation=pcall(api.epochState)
  if not probeOK or type(observation)~='table' or observation.guiThread~=true then
   fault=not probeOK and tostring(observation) or 'Unknown or foreign thread / epoch state unavailable';running=false;return false
  end
  local w;local ok,why=pcall(function()
   w=api.world()
   assert(type(observation.generation)=='number' and observation.generation>=0 and observation.generation%1==0,'Invalid native generation')
   assert(type(observation.stable)=='boolean' and type(observation.busy)=='boolean' and type(observation.loading)=='boolean','Incomplete native epoch state')
   if not observation.stable or observation.busy or observation.loading then deferred=true;reason=not observation.stable and 'unstable' or observation.busy and 'busy' or 'loading';return end
   if not w or not w.player then deferred=true;reason='world_unavailable';return end
   local wk=api.worldKey and api.worldKey(w)or key(w)
   if sourcegeneration~=nil and observation.generation<sourcegeneration then error('Native generation regressed')end
   if sourcegeneration==nil or observation.generation~=sourcegeneration then
    lastEpochReason=sourcegeneration==nil and 'initial' or 'native_generation_changed';epoch=epoch+1;rows={};fault=nil;worldKey=wk;gap=0;sourcegeneration=observation.generation;reason='generation_changed'
    if api.onEpoch then api.onEpoch(epoch)end
   elseif wk~=worldKey then error('World fingerprint changed without native generation')end
   if fault then return end
   local nextFrame=frame+1
   deferred=false;reason=nil
   local nextRows,handles,appearances={},{},{}
   local list=w.player.playerCharacters
   -- A transient empty player list alone is not proof of world destruction.
   if #list==0 and next(rows)then deferred=true;gap=gap+1;return end
   local stagedSerial=serial;local changed=0
   for i=1,#list do
    local c=list[i];local k=assert(key(c),'Null player object')
    assert(not nextRows[k],'Duplicate player pointer')
    local handle=c:getHandle():toString();assert(not handles[handle],'Duplicate live handle');handles[handle]=k
    local f=fingerprint(c);local ak=f.appearance and tostring(f.appearance)
    if ak then assert(not appearances[ak],'Shared player Appearance pointer');appearances[ak]=k end
    local old=rows[k];local token
    if old then
     assert(old.last==frame,'Non-contiguous identity observation')
     if old.complete and not complete(f)then deferred=true;gap=gap+1;return end
     if old.complete then assert(same(old.fingerprint,f),'Player fingerprint changed for '..old.handle)end
     if not old.complete then
      for field,value in pairs(old.fingerprint)do assert(f[field]==nil or f[field]==value,'Incomplete player fingerprint changed')end
     end
     token=old.token
     if old.complete and old.handle~=handle then
      assert(gap<=2,'Handle changed after an unobserved interval')
      assert(old.complete and complete(f)and same(old.fingerprint,f),'Unproven handle migration')
      changed=changed+1
     end
    else
     -- Never adopt a different Character that points at an old appearance.
     if ak then for previousKey,previous in pairs(rows)do
      assert(previousKey==k or tostring(previous.fingerprint.appearance)~=ak,'Appearance reused by another Character')
     end end
     stagedSerial=stagedSerial+1;token='T60_'..epoch..'_'..stagedSerial
    end
    nextRows[k]={token=token,handle=handle,fingerprint=f,complete=not not complete(f),last=nextFrame}
   end
   -- Do not retire a live snapshot because a streaming list briefly shrank.
   for k,old in pairs(rows)do
    if old.complete and not nextRows[k]then deferred=true;gap=gap+1;return end
   end
   rows=nextRows;serial=stagedSerial;frame=nextFrame;migrations=migrations+changed;gap=0
   if changed>0 then api.log('Stable identity retained across '..changed..' handle migration(s)')end
  end)
  running=false
  if not ok then return fail(w,why)end
  return not fault and not deferred
 end
 function S.owner(c)
  assert(not fault and not deferred,'Identity registry is stopped/deferred: '..tostring(fault))
  local row=rows[key(c)];assert(row and row.complete and row.last==frame,'Character is outside current validated snapshot')
  return row.token
 end
 function S.peek(c)local row=rows[key(c)];return row and row.token or nil end
 function S.eligible(c)local row=rows[key(c)];return not fault and not deferred and row and row.complete and row.last==frame or false end
 function S.key(c)return key(c)end
 function S.ready()return not fault and not deferred end
 function S.stop(why)return fail(api.world(),why)end
 function S.epoch()return epoch end
 function S.status()
  local count=0;for _ in pairs(rows)do count=count+1 end
  return {epoch=epoch,frame=frame,count=count,migrations=migrations,deferred=deferred,stopped=fault~=nil,error=fault,sourcegeneration=sourcegeneration,reason=reason,lastEpochReason=lastEpochReason}
 end
 return S
end
return M
