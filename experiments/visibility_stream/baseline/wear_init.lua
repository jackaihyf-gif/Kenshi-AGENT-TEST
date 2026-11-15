local identity=require('character_identity')
local cacheReady,animationCache=pcall(require,'animation_cache_gate')
if not cacheReady then
 print('[JACK T60 CacheGate] Wear controller disabled: '..tostring(animationCache))
 return
end
assert(animationCache.allowed(),'T60 cache gate is closed')
local function log(s) print('[JACK T60 WearLab v0.8.9] '..s) end
local ok,probe=pcall(require,'wear_probe')
if not ok then log('DISABLED: '..tostring(probe));return end
-- Continuous render diagnostics are opt-in; the render-fault log guard remains.
local race,manager
identity.onEpoch('wear visual',function()race=nil;manager=nil end)
local function visualRace()
 if race then return race end
 manager=AppearanceManager.getInstance()
 assert(manager, 'AppearanceManager unavailable')
 local world=getGameWorld()
 -- Database lookup also works if the visual race is not in the playable list.
 race=world.gamedata:getData('670-JACK_T60_WearLab.mod',7)
 assert(race and race.stringID=='670-JACK_T60_WearLab.mod','Restart game to load WearLab visual record')
 -- Race/mesh preprocessing is cached at process startup. The v0.8.2 .mod must
 -- be loaded by a fresh game process; changing GameData maps cannot refresh it.
 return race
end
local cacheOK,cache=pcall(require,'attachment_cache')
if not cacheOK then log('DISABLED: '..tostring(cache));return end
local visibility=require('equipment_visibility')
local persistence=require('original_appearance_save')
local controller=require('wear_controller').new({
 owner=identity.owner,characterKey=identity.key,eligible=identity.eligible,
 visibility=visibility,
 persistence=persistence,
 prepareAnimations=function(a)
  assert(animationCache.allowed(),'T60 cache gate closed before attachment preparation')
 end,
 attachmentCache=cache,bodyKey=function(a)return tostring(require('ffi').cast('void*',a:getBody())) end,
 log=log, world=getGameWorld, bones=probe.bones, visualRace=visualRace,
 makeVisual=function() assert(animationCache.allowed(),'T60 cache gate closed');local r=visualRace();return manager:createAppearanceData(r) end,
})
_G.JACK_T60_WEAR_STATUS=controller.status
identity.onEpoch('wear snapshots',controller.reset)
-- Read only newly appended log lines. Never inspect process memory to detect
-- draw errors. Roll back automatically instead of leaving an invisible body.
local reader,offset,checkAge=nil,0,0
if io and io.open then
 reader=io.open('D:/steam/steamapps/common/Kenshi/kenshi.log','rb')
 if reader then offset=reader:seek('end') or 0;reader:close();reader=nil end
else log('Render log guard unavailable in this Lua environment') end
local cacheFault=false
identity.onFrame('wear',function(dt)
 checkAge=checkAge+(tonumber(dt) or 0)
 if checkAge>=.25 and io and io.open then
  checkAge=0
  local file=io.open('D:/steam/steamapps/common/Kenshi/kenshi.log','rb')
  if file then
   local ending=file:seek('end') or offset
   if ending<offset then offset=0 end
   if ending>offset then
    file:seek('set',math.max(offset,ending-131072))
    local added=file:read('*a') or '';offset=ending
    if added:find('Unable to found a bound vertex',1,true) then controller.renderFault('unbound vertex buffer in engine log') end
   end
   file:close()
  end
 end
 local ok,err=pcall(visibility.scan)
 if not ok then log('VISIBILITY ERROR '..tostring(err))end
 if not cacheFault and not animationCache.allowed() then cacheFault=true;controller.renderFault('animation cache gate closed') end
 controller.tick(dt)
end)
Events.on('InputHandler::keyDownEvent',controller.key)
log('Ready. v0.8.6 post-body attachment refresh; cache follows equip; original slots restored on unequip; source Kenshi keys retained; 61 clips prepartitioned to remove duplicate upper/lower transforms; six engine blend replay cases passed. Live acceptance pending. Single draw, 82 bones / 57 draw palette. BELT component starts EQUIPPED; other clothing is render-hidden and restored on unequip. F7 status / F10 restore+suspend / F11 resume.')
