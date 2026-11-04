-- Native crafting fixtures, restricted to the single disposable test session.
local M={}
function M.new(config)
 local ffi=require('ffi');local C={}
 local state=_G.JACK_CRAFT_TEST_STATE or{benches={},events={}}
 _G.JACK_CRAFT_TEST_STATE=state
 local benches,events=state.benches,state.events
 local function raw(o)return o and ffi.cast('void**',o)[0]or nil end
 local function gd(id,t)return assert(getGameWorld().gamedata:getData(id,t),'Missing '..id)end
 local IDs={laser='100-JACK_EnergyWeapons.mod',gauss='110-JACK_EnergyWeapons.mod',fusion='200-JACK_EnergyWeapons.mod',emammo='210-JACK_EnergyWeapons.mod',armour='650-JACK_T60_WearLab.mod',emitter='400-JACK_WastelandCraft.mod',laser_receiver='410-JACK_WastelandCraft.mod',coil='420-JACK_WastelandCraft.mod',accelerator='430-JACK_WastelandCraft.mod',gauss_receiver='440-JACK_WastelandCraft.mod',servo='450-JACK_WastelandCraft.mod',frame='460-JACK_WastelandCraft.mod'}
 local mats={'2288-gamedata.base','579-gamedata.base','42160-gamedata.base','42164-gamedata.base','583-gamedata.base','97089-rebirth.mod'}
 if not state.hooked then
 Events.on('CraftingBuilding::_CONSTRUCTOR',function(self,data,position,rotation,participant,town,handle,layout,indoors,defaultVal)
  if state.pending and data and data.stringID==state.pending.id then state.pending.object=defaultVal or self end
 end)
 Events.on('CraftingBuilding::addFinishedCraftItem',function(self,item)
  if self and self.data and self.data.stringID:match('JACK_WastelandCraft%.mod$')then events[#events+1]={bench=self.data.stringID,item=item and item.data and item.data.stringID or''}end
 end)
 state.hooked=true
 end
 local function guard(c)
  local w=assert(getGameWorld());assert(w.player and #w.player.playerCharacters==1 and w.player.playerCharacters[1]==c and c:getName()==config.test_character_name,'Craft fixture requires isolated actor')
  assert(w.paused and not getOptionsHolder().autosave,'Pause and disable autosave first');assert(not c:isDead()and not c:isUnconcious(),'Actor unavailable');return w
 end
 local function snapshot(b)
  local inv=assert(b:getInventory());local r={bench=b.data.stringID,inputs={},counts={},sections={},items={},events=events,queued=b:hasCraftingQueued(),production=b:getProductionItemData()and b:getProductionItemData().stringID or'',power=b.powerOn,output_full=b:isProductionFull()}
  r.render={position=b:getPosition(),visible=b:getVisible(),entities_loaded=b.entitiesLoaded,entities_to_load=b.entitiesToLoad,floor=b:getFloor(),is_physical=b:isPhysical(),outside=b:getIsOutsideFurniture(),scale=b:getScale(),created=b:isCreated(),root_node=b.rootNode~=nil}
  for _,id in ipairs(mats)do r.counts[id]=inv:countItems(gd(id,4))end
  for key,id in pairs(IDs)do r.counts[id]=inv:countItems(gd(id,key=='armour'and 3 or(key=='laser'or key=='gauss')and 107 or 4))end
  local sections=inv:getAllSections();for i=1,#sections do local s=sections[i];local allowed={};local slots=s.veryLimitedSlot;if slots then for j=1,#slots do allowed[tostring(j)]=slots[j].stringID end end;r.sections[tostring(i)]={name=s.name,width=s.width,height=s.height,stack_min=s.stackingBonusMin,limit=s.itemsLimit,allowed=allowed}end
  local all=inv:getAllItems();for i=1,#all do local it=all[i];r.items[tostring(i)]={id=it.data.stringID,section=it.inventorySection,quality=it.quality}end
  if b.inItems then for i=1,#b.inItems do local it=b.inItems[i];r.inputs[tostring(i)]=it and it.data and it.data.stringID or'null'end end
  if b.partialItems then r.partial_material_credit={};for gd,value in pairs(b.partialItems)do r.partial_material_credit[gd.stringID]=value end end
  local bytes=ffi.cast('uint8_t*',raw(b));local count=tonumber(ffi.cast('uint32_t*',bytes+0x480)[0]);local cap=tonumber(ffi.cast('uint32_t*',bytes+0x484)[0]);r.native_consumption_count=count;r.native_consumption_capacity=cap
  if count>=0 and count<=cap and cap<32 then
   ffi.cdef[[typedef struct{float amount,rate;int capacity,pad;void* item;void* section;} AgentCraftConsumption;]]
   local data=ffi.cast('AgentCraftConsumption*',ffi.cast('void**',bytes+0x488)[0]);r.native_consumption={}
   for i=0,count-1 do r.native_consumption[tostring(i)]={amount=tonumber(data[i].amount),rate=tonumber(data[i].rate),capacity=tonumber(data[i].capacity)}end
  end
  if b:hasCraftingQueued()then local p=b:getCraft(0);if p then local f=ffi.cast('float*',p);r.work_needed=tonumber(f[2]);r.progress=tonumber(f[3])end end
  return r
 end
 local function deliverProduced(b,required,actor)
  local target=assert(benches.armour);local inv=b:getInventory();local dst=target:getInventory();local all=inv:getAllItems();local source
  for i=1,#all do local x=all[i];if x.inventorySection=='out'and(x.data.stringID==IDs.servo or x.data.stringID==IDs.frame)then source=x;break end end
  if not source then assert(not required,'No native-produced component');return end
  local destination;local sections=dst:getAllSections();for i=1,#sections do local x=sections[i];if x.name~='out'and x.veryLimitedSlot and #x.veryLimitedSlot==1 and x.veryLimitedSlot[1].stringID==source.data.stringID then destination=x;break end end
  assert(destination,'Target has no matching ingredient section');local n=source.quantity;local id=source.data.stringID
  local buffered=false
  if not destination:hasRoomForItem(source.data,n)then
   assert(actor,'Fixture stock buffer unavailable');destination=assert(actor:getInventory():getSection('main'));destination.stackingBonusMin=100;buffered=true
  end
  local sec=assert(inv:getSection('out'));assert(sec:removeItem(source))
  if not destination:addItem(source,n)then assert(sec:addItem(source,n),'Transfer rollback failed');error('Destination refused native output')end
  state.deliveries=state.deliveries or{};state.deliveries[#state.deliveries+1]={item=id,quantity=n,native_output=true,buffered=buffered};return n
 end
 function C.select(c,choice)
  local w=guard(c);choice=choice or'status'
  if choice=='supply-gauss'then
   assert(not c:isInCombatMode(true,true),'Supply outside combat only')
   local owner=c:getHandle():toString();state.gauss_handoffs=state.gauss_handoffs or{}
   if state.gauss_handoffs[owner]then return state.gauss_handoffs[owner]end
   local inv=assert(c:getInventory());local bag=assert(inv:getSection('main'))
   local gunData,ammoData=gd(IDs.gauss,107),gd(IDs.emammo,4)
   assert(inv:countItems(gunData)<4 and inv:countItems(ammoData)<=180,'Supply cap reached')
   assert(bag:hasRoomForItem(gunData,1)and bag:hasRoomForItem(ammoData,20),'Make room in the main inventory')
   local gun=assert(w.theFactory:createItem(gunData,nil,nil,nil,95,c:getFaction()))
   assert(raw(c:getHandle():getCharacter())==raw(c)and gun:isCrossbow(),'Fresh gun identity check failed')
   assert(inv:addItem(gun,1,false,false),'Could not add gauss rifle')
   local ammo=assert(w.theFactory:createItem(ammoData,nil,nil,nil,100,c:getFaction()))
   assert(raw(c:getHandle():getCharacter())==raw(c),'Fresh ammo identity check failed')
   assert(inv:addItem(ammo,20,false,false),'Could not add electromagnetic ammo');inv:notifyModified()
   local result={added_gauss=1,added_ammo_packs=20,gun_section=gun.inventorySection,gauss_in_bag=inv:countItems(gunData),ammo_total=inv:countItems(ammoData)}
   state.gauss_handoffs[owner]=result;return result
  end
  if choice=='supply-loadout'then
   -- Fixed, idempotent user handoff loadout; never touches another character.
   assert(not c:isInCombatMode(true,true),'Supply outside combat only')
   local inv=assert(c:getInventory());local bag=assert(inv:getSection('main'))
   assert(bag.width<=20 and bag.height<=20,'Unexpected inventory dimensions')
   if bag.width<20 or bag.height<20 then inv:resizeSection(bag,20,20,false)end
   bag.stackingBonusMin=50
   local function find(id)
    for _,item in pairs({primary=inv:getPrimaryWeapon(),secondary=inv:getSecondaryWeapon()})do if item.data.stringID==id then return item end end
    local all=inv:getAllItems();for i=1,#all do if all[i].data.stringID==id then return all[i]end end
   end
   local function add(id,kind,quantity)
    local data=gd(id,kind);local missing=quantity-inv:countItems(data)
    if missing<=0 then return find(id)end
    assert(missing<=50 and bag:hasRoomForItem(data,missing),'Bounded supply has no room: '..id)
    -- nil requests a fresh item handle. A character handle restores/rebinds an
    -- existing object identity and must never be reused for a new item.
    local item=assert(w.theFactory:createItem(data,nil,nil,nil,95,c:getFaction()),'Supply factory failed')
    assert(raw(c:getHandle():getCharacter())==raw(c),'Supply changed character identity')
    assert(inv:addItem(item,missing,false,false),'Supply inventory refused '..id)
    assert(inv:countItems(data)>=quantity,'Supply quantity readback failed '..id);return find(id)
   end
   local laser=assert(find(IDs.laser),'Use the isolated laser start')
   local gauss=add(IDs.gauss,107,1);assert(gauss:isCrossbow(),'Gauss factory type mismatch')
   local id='100-JACK_ChainswordLab.mod';local chain=find(id)
   if not chain then chain=assert(c:generateWeapon(gd(id,2),gd('661-JACK_T60_WearLab.mod',51)),'Chainsword factory failed')end
   if not find(id)then assert(inv:addItem(chain,1,false,false),'Could not retain chainsword')end
   c:isHuman():sheatheWeapon();local hip=assert(inv:getSection('hip'))
   if chain.inventorySection~='hip'then
    local src=assert(inv:getSection(chain.inventorySection));assert(hip:hasRoomForItem(chain.data,1)and hip:canItemGoHere(chain,0,0),'Chainsword does not fit secondary')
    assert(src:removeItem(chain));if not hip:addItem(chain,1)then assert(src:addItem(chain,1));error('Secondary transfer rolled back')end
   end
   if not laser.isEquipped then assert(inv:equipItem(laser),'Could not equip laser primary')end
   add(IDs.fusion,4,50);add(IDs.emammo,4,50);inv:notifyModified();c:healCompletely()
   local result={weapons={},ammo={},bag={width=bag.width,height=bag.height},primary=inv:getPrimaryWeapon().data.stringID,secondary=inv:getSecondaryWeapon().data.stringID}
   for _,id in ipairs({IDs.laser,IDs.gauss,'100-JACK_ChainswordLab.mod'})do local it=assert(find(id));result.weapons[id]={name=it.data.name,section=it.inventorySection,quantity=it.quantity,quality=it.quality}end
   for _,id in ipairs({IDs.fusion,IDs.emammo})do result.ammo[id]=inv:countItems(gd(id,4))end
   return result
  end
  if choice=='status'then local r={benches={},events=events,deliveries=state.deliveries or{},work_calls=state.work_calls or 0,work_active=state.work~=nil};for k,b in pairs(benches)do r.benches[k]=snapshot(b)end;return r end
  if choice=='create-energy'or choice=='create-armour'then
   local key=choice:sub(8);assert(not benches[key],'Fixture already exists');local id=(key=='energy'and'100-'or'200-')..'JACK_WastelandCraft.mod';state.pending={id=id}
   ffi.cdef[[typedef struct {float x,y,z;} AgentCraftVec;typedef struct {float w,x,y,z;} AgentCraftQuat;]]
   local kernel=ffi.load('kernel32');local lib=kernel.GetModuleHandleA('KenshiLib.dll')
   local address=kernel.GetProcAddress(lib,'?createBuilding@RootObjectFactory@@QEAAPEAVBuilding@@PEAVGameData@@VVector3@Ogre@@PEAVTownBase@@PEAVFaction@@VQuaternion@5@PEAVFactoryCallbackInterface@@PEAVLayout@@PEAV2@PEAVGameSaveState@@7_N99H9@Z');assert(address~=nil,'Factory export missing')
   local create=ffi.cast('void* (*)(void*,void*,const AgentCraftVec*,void*,void*,const AgentCraftQuat*,void*,void*,void*,void*,void*,bool,bool,bool,int,bool)',address)
   -- Exterior factory Y is height above terrain, not actor world elevation.
   local p=c:getPosition();local pos=ffi.new('AgentCraftVec',{p.x+(key=='energy'and 28 or-28),0,p.z+28});local q=ffi.new('AgentCraftQuat',{1,0,0,0})
   local result=create(raw(w.theFactory),raw(gd(id,0)),pos,nil,raw(c:getFaction()),q,nil,nil,nil,nil,nil,false,true,false,0,true);assert(result~=nil,'Factory returned null');assert(state.pending.object,'Craft constructor was not observed')
   local b=state.pending.object;state.pending=nil;benches[key]=b;b:givePower(10000);return snapshot(b)
  end
  local key,action=choice:match('^(energy|armour)%-(.+)$')
  -- Lua patterns do not implement alternation.
  if not key then key,action=choice:match('^(%a+)%-(.+)$')end
  assert(key=='energy'or key=='armour','Unknown fixture');local b=assert(benches[key],'Create fixture first');local inv=b:getInventory()
  if action=='clear-all'then
   assert(not b:hasCraftingQueued(),'Finish existing craft first');inv:clearAll(true,false);return snapshot(b)
  elseif action=='clear-output'then
   local list=inv:getAllItems();local remove={};for i=1,#list do if list[i].inventorySection=='out'then remove[#remove+1]=list[i]end end
   for _,it in ipairs(remove)do assert(inv:removeItemAutoDestroy(it,1000),'Could not clear generated fixture item')end
   return snapshot(b)
  elseif action=='fresh'then
   assert(not b:hasCraftingQueued(),'Finish existing craft first');benches[key]=nil;return {discarded_fixture_reference=true}
  elseif action=='cancel-single'then
   -- Only the one recipe queued by this fixture may be cancelled for A/B
   -- progress sampling. The actor/world/pause guards above remain mandatory.
   local q=assert(state.singleQueue,'No bounded fixture queue proof')
   assert(q.bench==b and q.times==1 and state.work==nil,'Not a single native-operated fixture queue')
   if b:hasCraftingQueued()then b:_removeCraft(0)end
   assert(not b:hasCraftingQueued(),'Fixture cancellation left a queue')
   state.singleQueue=nil;return snapshot(b)
  elseif action:match('^queue:')then
   local what=action:sub(7);local name,number=what:match('^(%a+):(%d+)$');local times=number and tonumber(number)or 1;what=name or what;assert(times>=1 and times<=10,'Batch outside fixture limit');local id=assert(IDs[what],'Unknown product');assert(not b:hasCraftingQueued(),'Queue not empty')
   local t=what=='armour'and 3 or(what=='laser'or what=='gauss')and 107 or 4;local item=gd(id,t);local mat=(what=='laser'or what=='gauss')and gd((what=='laser'and'300-'or'310-')..'JACK_EnergyWeapons.mod',50)or item
   for i=1,times do b:_addCraft(item,mat,0,0)end;b:setProductionItem(item,1,0);state.singleQueue={bench=b,times=times};return snapshot(b)
  elseif action:match('^deliver:')then
   assert(key=='energy','Deliver from energy bench only');local what=action:sub(9);local id=assert(IDs[what]);assert(id==IDs.servo or id==IDs.frame,'Only manufactured armour components')
   local target=assert(benches.armour);local dst=target:getInventory();local destination
   local sections=dst:getAllSections();for i=1,#sections do local sec=sections[i];if sec.name~='out'and sec.veryLimitedSlot and #sec.veryLimitedSlot==1 and sec.veryLimitedSlot[1].stringID==id then destination=sec end end
   assert(destination,'Destination ingredient slot missing');local all=inv:getAllItems();local source
   for i=1,#all do if all[i].inventorySection=='out'and all[i].data.stringID==id then source=all[i];break end end
   assert(source,'No native-crafted component to transfer');local amount=source.quantity;local section=assert(inv:getSection('out'));assert(section:removeItem(source));assert(destination:addItem(source,amount),'Transfer refused')
   return {transferred_native_output=id,quantity=amount,source=snapshot(b),destination=snapshot(target)}
  elseif action:match('^one:')then
   local id=action:sub(5);local item=w.theFactory:createItem(gd(id,4),b:getHandle(),gd(id,4),gd(id,4),100,c:getFaction());local okay=inv:addItem(item,1,false,true);local r=snapshot(b);r.added=okay;return r
  elseif action:match('^fill:')then
   local exclude=action:sub(6);local wanted={};local input=b.inItems;for i=1,#input do wanted[#wanted+1]=input[i].data.stringID end
   for _,id in ipairs(wanted)do if id~=exclude and inv:countItems(gd(id,4))<50 then
    local item=w.theFactory:createItem(gd(id,4),b:getHandle(),gd(id,4),gd(id,4),100,c:getFaction());assert(item,'Material creation failed');local destination
    local sections=inv:getAllSections();for i=1,#sections do local sec=sections[i];local allowed=sec.veryLimitedSlot;if sec.name~='out'and allowed and #allowed==1 and allowed[1].stringID==id then destination=sec;break end end
    assert(destination,'No dedicated section for '..id);destination.stackingBonusMin=100;assert(destination:addItem(item,50-inv:countItems(gd(id,4))),'Material section refused '..id)
   end end;return snapshot(b)
  elseif action=='step'then
   b:givePower(10000);for i=1,10 do if b:hasCraftingQueued()then b:operate(c,.1)end end;return snapshot(b)
  elseif action=='work'or action=='work-deliver'then
   state.work={bench=b,actor=c,owner=c:getHandle():toString(),expires=os.time()+12,autoDeliver=action=='work-deliver'};return snapshot(b)
  elseif action=='operate'then
   c:clearAllAIGoals();c:addGoal(TaskType.OPERATE_MACHINERY,b);return snapshot(b)
  elseif action=='open'then
   local ui=inv:getInventoryGUI()or getForgottenGUI():showInventory(b:getHandle(),true,0,0);assert(ui,'Inventory UI unavailable');ui:show(true);return snapshot(b)
  end
  error('Unsupported craft test action')
 end
 function C.frame()
  local job=state.work;if not job then return end;local w=getGameWorld()
  if not w or w.gameResetting or not w.player or #w.player.playerCharacters~=1 or w.player.playerCharacters[1]:getHandle():toString()~=job.owner then state.work=nil;return end
  if w.paused then return end
  if os.time()>job.expires then state.work=nil;w:userPause(true);return end
  job.bench:givePower(10000)
  if job.autoDeliver then deliverProduced(job.bench,false,job.actor)end
  if job.bench.data.stringID=='200-JACK_WastelandCraft.mod'then
   local bag=job.actor:getInventory();local inv=job.bench:getInventory();local sections=inv:getAllSections()
   for i=1,#sections do local sec=sections[i];local allowed=sec.veryLimitedSlot
    if sec.name~='out'and allowed and #allowed==1 and(allowed[1].stringID==IDs.servo or allowed[1].stringID==IDs.frame)then
     local data=allowed[1]
     for n=1,5 do
      if inv:countItems(data)>=5 or bag:countItems(data)==0 or not sec:hasRoomForItem(data,1)then break end
      local one=assert(bag:takeOneItemOnly(data));if not sec:addItem(one,1)then assert(bag:getSection('main'):addItem(one,1),'Buffer rollback failed');break end
     end
    end
   end
  end
  state.work_calls=(state.work_calls or 0)+1
  if job.bench:hasCraftingQueued()then job.bench:operate(job.actor,10000)else state.work=nil;w:userPause(true)end
 end
 return C
end
return M
