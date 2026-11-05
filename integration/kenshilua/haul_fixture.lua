-- Disposable single-actor haul fixture. Integration contract is in README.md.
-- No inventory transfers, synthetic work, or production hooks.
local M={}
function M.new(config)
 local ffi=require('ffi')
 local cs=assert(_G.JACK_CRAFT_TEST_STATE,'Create the existing energy fixture first')
 local state=cs.haul or {};cs.haul=state
 local BOX='97243-rebirth.mod';local PART='97089-rebirth.mod';local SPRING='97090-rebirth.mod';local EMITTER='400-JACK_WastelandCraft.mod';local RECEIVER='410-JACK_WastelandCraft.mod'
 local ids={PART,SPRING,EMITTER,RECEIVER}
 local function raw(o)return o and ffi.cast('void**',o)[0]or nil end
 local function gd(id,t)return assert(getGameWorld().gamedata:getData(id,t or 4),'Missing '..id)end
 local function guard(c)
  local w=assert(getGameWorld());assert(w.player and #w.player.playerCharacters==1 and w.player.playerCharacters[1]==c and c:getName()==config.test_character_name,'Isolated actor required')
  assert(w.paused and not getOptionsHolder().autosave,'Pause and disable autosave');assert(not c:isDead() and not c:isUnconcious(),'Actor unavailable');return w
 end
 if not state.hooked then
  Events.on('StorageBuilding::_CONSTRUCTOR',function(self,data,position,rotation,participant,town,handle,layout,indoors,defaultVal)
   if state.pending and data and data.stringID==BOX then state.pending.object=defaultVal or self end
  end)
  state.hooked=true
 end
 local function counts(o)
  local inv=assert(o:getInventory());local r={}
  for _,id in ipairs(ids)do r[id]=inv:countItems(gd(id))end
  return r
 end
 local function pos(o)local p=o:getPosition();return {x=p.x,y=p.y,z=p.z}end
 local function handle(o)return o:getHandle():toString()end
 local function snap(c)
  local b=assert(cs.benches.energy,'Energy bench missing');local box=assert(state.box,'Box missing')
  local inputs={};if b.inItems then for i=1,#b.inItems do local x=b.inItems[i];inputs[tostring(i)]=x and x.data and x.data.stringID or 'null' end end
  local p=b:getProductionItemData()
  return {actor={handle=handle(c),position=pos(c),counts=counts(c)},box={handle=handle(box),id=box.data.stringID,position=pos(box),counts=counts(box)},bench={handle=handle(b),id=b.data.stringID,position=pos(b),counts=counts(b),inputs=inputs,production=p and p.stringID or '',queued=b:hasCraftingQueued()},lease={active=state.active or false,started=state.started,stop_reason=state.stop_reason},work_calls=cs.work_calls or 0}
 end
 local function add(w,c,inv,id,n,section)
  local data=gd(id);assert(inv:countItems(data)==0,'Seed requires empty target '..id)
  local item=assert(w.theFactory:createItem(data,nil,nil,nil,100,c:getFaction()),'Item creation failed')
  assert(section:hasRoomForItem(data,n),'No room for seed '..id)
  assert(section:addItem(item,n),'Seed rejected '..id);assert(inv:countItems(data)==n,'Seed count mismatch '..id)
 end
 function M.select(c,choice)
  local w=guard(c);local b=assert(cs.benches.energy,'Create energy fixture first')
  if choice=='haul-create'then
   assert(not state.box and not state.pending,'Only one haul box per session')
   state.pending={};ffi.cdef[[typedef struct {float x,y,z;} AgentHaulVec;typedef struct {float w,x,y,z;} AgentHaulQuat;]]
   local kernel=ffi.load('kernel32');local lib=kernel.GetModuleHandleA('KenshiLib.dll')
   local address=kernel.GetProcAddress(lib,'?createBuilding@RootObjectFactory@@QEAAPEAVBuilding@@PEAVGameData@@VVector3@Ogre@@PEAVTownBase@@PEAVFaction@@VQuaternion@5@PEAVFactoryCallbackInterface@@PEAVLayout@@PEAV2@PEAVGameSaveState@@7_N99H9@Z');assert(address~=nil,'Factory export missing')
   local create=ffi.cast('void* (*)(void*,void*,const AgentHaulVec*,void*,void*,const AgentHaulQuat*,void*,void*,void*,void*,void*,bool,bool,bool,int,bool)',address)
   local p=b:getPosition();local pos=ffi.new('AgentHaulVec',{p.x+15,0,p.z+15});local q=ffi.new('AgentHaulQuat',{1,0,0,0})
   local result=create(raw(w.theFactory),raw(gd(BOX,0)),pos,nil,raw(c:getFaction()),q,nil,nil,nil,nil,nil,false,true,false,0,true)
   assert(result~=nil and state.pending.object,'Storage constructor not observed; discard session')
   state.box=state.pending.object;state.pending=nil;assert(state.box.data.stringID==BOX,'Wrong box');return snap(c)
  elseif choice=='haul-seed'then
   assert(not state.seeded and not state.active,'Seed only once');local box=assert(state.box,'Create box first');local binv=assert(b:getInventory());local xinv=assert(box:getInventory());local cinv=assert(c:getInventory())
   assert(not cs.work,'Synthetic work active');assert(b:hasCraftingQueued() and b:getProductionItemData() and b:getProductionItemData().stringID==RECEIVER,'Queue 410 first')
   for _,id in ipairs({PART,SPRING,EMITTER})do assert(cinv:countItems(gd(id))==0,'Actor must start empty of '..id)end
   assert(binv:countItems(gd(PART))==0 and binv:countItems(gd(SPRING))==0 and binv:countItems(gd(EMITTER))==50,'Use existing fill excluding parts first')
   local sections=xinv:getAllSections();local section
   for i=1,#sections do local s=sections[i];if s:hasRoomForItem(gd(PART),1) and s:hasRoomForItem(gd(SPRING),7)then section=s;break end end
   assert(section,'Box cannot accept both seed items')
   add(w,c,xinv,PART,1,section);add(w,c,xinv,SPRING,7,section);xinv:notifyModified()
   local bp=b:getPosition();local cp=c:getPosition();assert((cp.x-bp.x)^2+(cp.z-bp.z)^2<=64^2,'Actor outside 64-unit bound')
   state.seeded=true;state.active=true;state.started=nil;state.stop_reason=nil;state.owner=handle(c);state.center={x=bp.x,z=bp.z};state.world=raw(w)
   c:clearAllAIGoals();c:addGoal(TaskType.OPERATE_MACHINERY,b)
   return snap(c)
  elseif choice=='haul-snapshot'then return snap(c) end
  error('Unknown haul action')
 end
 function M.frame()
  if not state.active then return end
  local w=getGameWorld();if not w or raw(w)~=state.world or w.gameResetting or not w.player or #w.player.playerCharacters~=1 then state.active=false;state.stop_reason='world changed';return end
  local c=w.player.playerCharacters[1]
  if not c or handle(c)~=state.owner or c:getName()~=config.test_character_name then state.active=false;state.stop_reason='actor changed';w:userPause(true);return end
  if w.paused then return end
  state.started=state.started or os.time();local p=c:getPosition();local center=state.center
  if getOptionsHolder().autosave or c:isDead() or c:isUnconcious() or (p.x-center.x)^2+(p.z-center.z)^2>64^2 or os.time()-state.started>=30 then
   state.active=false;state.stop_reason='lease limit or guard';w:userPause(true)
  end
 end
 return M
end
return M
