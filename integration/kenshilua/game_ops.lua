-- Fixed in-game operations; all engine calls run on the bridge's GUI frame.
local M={}
function M.new(config)
 local ffi=require('ffi')
 ffi.cdef[[int T60_motion_snapshot(void*,char*,size_t);]]
 ffi.cdef[[int T60_motion_sources(void*,char*,size_t);]]
 local ok,motion=pcall(ffi.load,config.motion_dll)
 local buffer=ffi.new('char[16384]')
 local probe=require('wear_probe')
 local plugins=assert(config.motion_dll:match('^(.*)/'),'Motion plugin directory unavailable')
 ffi.cdef[[int EnergyGun_state(void*,char*,size_t);]]
 local auditOK,gunAudit=pcall(ffi.load,'D:/steam/steamapps/common/Kenshi/mods/JACK_EnergyWeapons/plugin/EnergyGunVisual_v013.dll')
 local function gunState(item)
  local crossbow=item:isCrossbow();if not crossbow then return nil end
  if not auditOK then return {available=false}end
  local gun=crossbow.gunClass;if gun==nil then return {ready=false}end
  local out=ffi.new('char[1024]');local n=gunAudit.EnergyGun_state(ffi.cast('void*',gun),out,1024)
  if n<0 then return {ready=false,error=n}end
  return {ready=true,diagnostic=ffi.string(out)}
 end
 -- Lua's generated binding rejects the nullable building/subject arguments of
 -- playerMoveOrderDefault. Use the exported engine method with its exact ABI.
 ffi.cdef[[typedef struct {float x,y,z;} AgentMoveVector;]]
 local kernel=ffi.load('kernel32')
 local lib=kernel.GetModuleHandleA('KenshiLib.dll')
 local address=kernel.GetProcAddress(lib,
  '?playerMoveOrderDefault@Character@@UEAAXPEAVBuilding@@PEAVRootObject@@AEBVVector3@Ogre@@@Z')
 assert(address~=nil,'Player movement engine export unavailable')
 local playerMove=ffi.cast('void (*)(void*,void*,void*,const AgentMoveVector*)',address)
 local A={}
 -- A camera-only probe scoped to the exact isolated fixture. No forced unload.
 local regionProbe
 local singleTelemetryProof
 function A.stage2_region(w,list,choice)
  assert(not getOptionsHolder().autosave,'Disable autosave first')
  if choice=='begin' then
   assert(not regionProbe and w.paused and #w.player.playerCharacters==1,'Expected paused single-actor isolated fixture')
   local c=w.player.playerCharacters[1];local h=c:getHandle():toString()
   assert(h=='1-2804199168-1-2987182592-1' and c:getName()==config.test_character_name,'Unexpected isolated actor')
   local a=assert(c:getAppearance());assert(not a.isCreatingBody and not a.updateBody,'Body busy')
   local p=c:getPosition();local cam=w.player.camera
   regionProbe={world=tostring(ffi.cast('void**',w)[0]),owner=h,home={x=p.x,y=p.y,z=p.z},expires=os.time()+60,samples={}}
   w.player:stopTrackCharacter();cam:stopFollowing();cam:teleport({x=p.x+12000,y=p.y,z=p.z})
   return {started=true,home=regionProbe.home,expires=regionProbe.expires}
  end
  assert(regionProbe and regionProbe.world==tostring(ffi.cast('void**',w)[0]),'Probe unavailable or world changed')
  if choice=='return' then w.player.camera:teleport(regionProbe.home);regionProbe.returned=true
  else assert(choice=='status','Unknown probe operation') end
  return regionProbe
 end
 local meleeCapture
 local startRaceOverride
 function A.melee_capture(c,choice)
  local w=assert(getGameWorld());assert(#w.player.playerCharacters==1 and c:getName()==config.test_character_name,'Melee capture requires isolated test')
  if choice=='status'then return meleeCapture or{active=false}end
  if choice=='cancel'then meleeCapture=nil;return {active=false}end
  assert(w.paused and not getOptionsHolder().autosave,'Pause isolated test and disable autosave first')
  local clip,seconds=assert(choice):match('^([%w _%-]+)@([%d%.]+)$');seconds=tonumber(seconds)
  assert(clip and #clip<=64 and seconds and seconds>=0 and seconds<=4,'Expected clip@seconds')
  meleeCapture={active=true,owner=c:getHandle():toString(),clip=clip,seconds=seconds,expires=os.time()+28,captured=false}
  return meleeCapture
 end
 function A.power(c,choice)return dofile(config.root..'/power_test_controller.lua').new(config).select(c,choice or'status')end
 function A.craft(c,choice)
  if choice and choice:match('^haul%-')then return dofile(config.root..'/haul_fixture.lua').new(config).select(c,choice)end
  return dofile(config.root..'/craft_test_controller.lua').new(config).select(c,choice or'status')
 end
 local serviceTests=dofile(config.root..'/service_test_controller.lua').new(config)
 function A.service(c,choice)return serviceTests.select(c,choice or 'status')end
 local weaponTests=dofile(config.root..'/weapon_test_controller.lua').new({
  gunState=gunState,
  guard=function(c)
   local w=assert(getGameWorld());local list=w.player.playerCharacters
   assert(#list==1 and list[1]==c and c:getName()==config.test_character_name,'Weapon loadout requires the isolated test')
   local a=assert(c:getAppearance());assert(not a.isCreatingBody and not a.updateBody,'Body busy')
  end,
  active=function(c)assert(not c:isDead() and not c:isUnconcious(),'Test actor must be conscious and alive')end,
  fighting=function(c)return c:isInCombatMode(true,true)end,
  sheathe=function(c)local h=assert(c:isHuman());h:sheatheWeapon()end,
  world=getGameWorld,paused=function()return getGameWorld().paused end,
  same=function(a,b)return a~=nil and b~=nil and ffi.cast('void**',a)[0]==ffi.cast('void**',b)[0] end,
  autosave=function()return getOptionsHolder().autosave end,
  lookup=function(id)return getGameWorld().gamedata:getData(id,itemType.WEAPON) end,
  manufacturer=function()return getGameWorld().gamedata:getData('661-JACK_T60_WearLab.mod',51)end,
 })
 function A.weapon(c,choice)return weaponTests.select(c,choice or 'status')end
 function A.energy(c,choice)
  assert(_G.JACK_ENERGY_STATUS,'Energy helper unavailable')
  if choice=='arm-flight'then
   local w=getGameWorld();assert(#w.player.playerCharacters==1 and c:getName()==config.test_character_name and w.paused and not getOptionsHolder().autosave,'Laser capture requires paused isolated test')
   local it=c:getInventory():getPrimaryWeapon();assert(it and it.data.stringID=='100-JACK_EnergyWeapons.mod','Laser weapon required')
   assert(_G.JACK_ENERGY_ARM)();
  else assert(choice==nil or choice=='status','Unknown energy diagnostic')end
  return {diagnostic=_G.JACK_ENERGY_STATUS()}
 end
 function A.visibility(c,enabled)
  assert((enabled~='0' and enabled~='1') or not _G.JACK_T60_CHARACTER_IDENTITY,'Automatic visibility owns this actor; use read-only diagnostics')
  local w=assert(getGameWorld());assert(#w.player.playerCharacters==1 and c:getName()==config.test_character_name,'Visibility test requires isolated actor')
  assert(w.paused and not getOptionsHolder().autosave,'Pause and disable autosave first')
  local a=assert(c:getAppearance());assert(not a.isCreatingBody and not a.updateBody,'Body busy')
  local native=ffi.load(plugins..'/T60EquipmentVisibility_indexed.dll');ffi.cdef[[int T60_visibility_ready(void);int T60_visibility_begin(void*,const char*);int T60_visibility_tick(void*,const char*,char*,size_t);int T60_visibility_end(void*,const char*);int T60_visibility_status(void*,char*,size_t);]]
  assert(native.T60_visibility_ready()==0,'Native visibility API unavailable')
  local raw=ffi.cast('void**',a)[0];local owner=c:getHandle():toString();local output=ffi.new('char[16384]')
  local n
  if enabled=='1' then assert(native.T60_visibility_begin(raw,owner)==0);n=native.T60_visibility_tick(raw,owner,output,16384)
  elseif enabled=='0' then n=native.T60_visibility_end(raw,owner)
  else assert(enabled==nil or enabled=='read','Invalid visibility test flag');n=0 end
  assert(n>=0,'Native visibility operation failed '..tostring(n));local count=native.T60_visibility_status(raw,output,16384);assert(count>=0,'Visibility read failed '..tostring(count))
  local bytes=ffi.cast('unsigned char*',raw)
  return {entities=count,diagnostic=ffi.string(output),busy={creating=tonumber(bytes[0xe8]),rebuild=tonumber(bytes[0x143]),body=tostring(ffi.cast('void**',bytes+0xd8)[0])}}
 end
 local combatLease
 local trace
 local poseCapture
 function A.pose_capture(c,choice)
  local w=assert(getGameWorld());assert(#w.player.playerCharacters==1 and c:getName()==config.test_character_name and not getOptionsHolder().autosave,'Capture requires the isolated test')
  if choice=='status'then return poseCapture or {active=false}end
  assert(choice=='aim'or choice=='secondary','Unknown pose capture')
  assert(w.paused,'Arm pose capture while paused')
  local item=choice=='aim'and c:getInventory():getPrimaryWeapon()or c:getInventory():getSecondaryWeapon()
  local id=item and item.data.stringID
  assert(choice=='aim'and(id=='100-JACK_EnergyWeapons.mod'or id=='110-JACK_EnergyWeapons.mod')or choice=='secondary'and id=='100-JACK_ChainswordLab.mod','Unexpected test weapon')
  poseCapture={active=true,owner=c:getHandle():toString(),weapon=id,kind=choice,expires=os.time()+20,captured=false}
  return poseCapture
 end
 local observedNPC={}
 -- One disposable opponent, owned by a new nonpersistent platoon. This never
 -- borrows or edits a town NPC and is available only in the no-autosave test.
 local opponentLease
 local function raw(o)return o and ffi.cast('void**',o)[0]end
 local function fixtureWorld(w)return w and tostring(raw(w))end
 local team
 local clockLease
 function A.stage2_team(w,list,choice,owner)
  assert(w.paused and not getOptionsHolder().autosave,'Pause isolated world and disable autosave')
  if not team then
   local base='1-2804199168-1-2987182592-1'
   assert(list[base] and list[base]:getName()==config.test_character_name,'Unexpected test origin')
   team={world=fixtureWorld(w),members={[base]=config.test_character_name},created=0}
   local fixed={['2-2411865344-1-2987182592-1']={'human_female','17-gamedata.quack'},['3-1676391552-1-2987182592-1']={'shek_male','5276-chareditor.mod'},['4-3972167936-1-2987182592-1']={'shek_female','5276-chareditor.mod'},['5-3988769536-1-2987182592-1']={'human_male','17-gamedata.quack'}}
   for id,profile in pairs(fixed)do if list[id]then local c=list[id];assert(c:getName()=='T60_STAGE2_'..profile[1] and c.myRace.data.stringID==profile[2],'Unexpected recovered fixture');team.members[id]=c:getName();team.created=team.created+1 end end
   assert(#w.player.playerCharacters==1+team.created,'Unexpected fixture count')
  end
  assert(team.world==fixtureWorld(w),'Fixture world changed')
  for id,c in pairs(list)do assert(team.members[id]==c:getName(),'Unexpected character in isolated world')end
  local templates={['human_female']='53242-Dialogue.mod',['shek_male']='47755-Dialogue.mod',['shek_female']='58280-Dialogue.mod',['human_male']='2249-gamedata.base'}
  if choice and choice:match('^create:')then
   local profile=choice:sub(8);local templateId=assert(templates[profile],'Unknown fixed profile')
   assert(not team.pending and team.created<4,'Fixture count exceeded or creation pending')
   ffi.cdef[[int T60_attachment_ready(void);]];assert(ffi.load(plugins..'/T60AttachmentCompat_v083b.dll').T60_attachment_ready()==1,'Unsupported engine build')
   local method=assert(kernel.GetProcAddress(lib,'?createRandomCharacter@RootObjectFactory@@QEAAPEAVRootObject@@PEAVFaction@@VVector3@Ogre@@PEAVRootObjectContainer@@PEAVGameData@@PEAVBuilding@@M@Z'))
   local create=ffi.cast('void* (*)(void*,void*,const AgentMoveVector*,void*,void*,void*,float)',method)
   local base=w.player.playerCharacters[1];local p=base:getPosition();local pos={x=p.x+20+team.created*4,y=p.y,z=p.z}
   local faction=assert(w.factionMgr:getOrCreateFaction(assert(w.gamedata:getData('200-gamedata.base',10))))
   local platoon=assert(faction:createNewEmptyActivePlatoon(assert(w.gamedata:getData('663-JACK_T60_WearLab.mod',52)),false,pos))
   team.pending={platoon=platoon,faction=faction,profile=profile,template=templateId}
   local ptr=create(raw(w.theFactory),raw(faction),ffi.new('AgentMoveVector',pos),raw(platoon.activePlatoon),raw(assert(w.gamedata:getData(templateId,1))),nil,1)
   assert(ptr~=nil,'Fixture creation returned null');team.pending.character=ptr
   return {created=true,profile=profile,template=templateId}
  elseif choice=='recruit'then
   local pending=assert(team.pending,'No pending fixture');local things=pending.platoon.activePlatoon:getThings();local c
   for i=1,#things do if raw(things[i])==pending.character then c=things[i]:getHandle():getCharacter()end end
   assert(c,'Fixture not yet available');local id=c:getHandle():toString();local name='T60_STAGE2_'..pending.profile
   c:setName(name)
   local ok=w.player:recruit(c,false);assert(ok,'Engine refused fixture recruitment')
   id=c:getHandle():toString();team.members[id]=name
   team.created=team.created+1;team.pending=nil
   return {owner=id,name=name,profile=pending.profile,recruited=ok}
  elseif choice=='status'then
   local rows={};for id,c in pairs(list)do local a=c:getAppearance();local s=c:getStats();local all=c:getInventory():getAllItems();local items={};for i=1,#all do local it=all[i];items[#items+1]={id=it.data.stringID,quantity=it.quantity,section=it.inventorySection,equipped=it.isEquipped}end;rows[id]={name=c:getName(),logical=c.myRace.data.stringID,visual=a.raceData.stringID,female=a.female,appearance=tostring(raw(a)),appearance_data=tostring(raw(a.appearanceData)),hair=a.hairStyle and a.hairStyle.stringID or '',body=a:getBody()and tostring(ffi.cast('void*',a:getBody()))or nil,bones=not a.isCreatingBody and not a.updateBody and a:getBody()and A.bones(a)or nil,raw_strength=s._strength,strength=s:strengthActual(),wardrobe=A.detail(c).wardrobe,items=items}end
   return {members=rows,created=team.created,pending=team.pending and team.pending.profile or nil,save_runtime=_G.JACK_T60_SAVE_STATUS and _G.JACK_T60_SAVE_STATUS()or nil}
  elseif choice=='sheathe'then
   local c=assert(list[owner],'Fixture owner not loaded');assert(team.members[owner]==c:getName(),'Fixture identity mismatch');assert(c:isHuman(),'Human required')
   c:isHuman():sheatheWeapon();return {owner=owner,requested=true}
  elseif choice=='identity-snapshot'then
   local rows={};for id,c in pairs(list)do local a=c:getAppearance();local s=c:getStats();rows[id]={name=c:getName(),character=tostring(raw(c)),appearance=tostring(raw(a)),appearance_data=tostring(raw(a.appearanceData)),logical=c.myRace.data.stringID,visual=a.raceData.stringID,female=a.female,raw_strength=s._strength,strength=s:strengthActual()}end;return {members=rows}
  elseif choice=='ui-drag-fixture'then
   local panels={};local function visit(widget,depth)
    if not widget or depth>8 or not widget:getVisible()then return end
    if widget:getName():match('PortraitsPanel$')then panels[#panels+1]=widget end
    for i=0,math.min(widget:getChildCount(),200)-1 do visit(widget:getChildAt(i),depth+1)end
   end
   local e=MyGUI.Gui.getInstance():getEnumerator();while e:next()do visit(e:current(),0)end
   assert(#panels==2,'Expected exactly two squad panels');table.sort(panels,function(a,b)local _,ay=a:getAbsoluteCoord();local _,by=b:getAbsoluteCoord();return ay<by end)
   assert(panels[1]:getChildCount()==5 and panels[2]:getChildCount()==0,'Unexpected squad contents')
   local src=panels[1]:getChildAt(4);local sx,sy,sw,sh=src:getAbsoluteCoord();local dx,dy,dw,dh=panels[2]:getAbsoluteCoord();sx=math.floor(sx+sw/2);sy=math.floor(sy+sh/2);dx=math.floor(dx+math.min(53,dw/2));dy=math.floor(dy+math.min(53,dh/2))
   local m=MyGUI.InputManager.getInstance();m.injectMouseMove(sx,sy,0);m.injectMousePress(sx,sy,0);for i=1,12 do m.injectMouseMove(math.floor(sx+(dx-sx)*i/12),math.floor(sy+(dy-sy)*i/12),0)end;m.injectMouseRelease(dx,dy,0)
   return {from={x=sx,y=sy},to={x=dx,y=dy}}
  elseif choice=='ui-open-squad'or choice=='ui-add-squad'then
   local found;local function visit(widget,depth)
    if not widget or depth>8 or not widget:getVisible()then return end
    local suffix=choice=='ui-open-squad'and'ShortcutSquadButton$'or'NewSquadButton$'
    if widget:getName():match(suffix)then assert(not found,'Multiple squad buttons');found=widget end
    for i=0,math.min(widget:getChildCount(),200)-1 do visit(widget:getChildAt(i),depth+1)end
   end
   local e=MyGUI.Gui.getInstance():getEnumerator();while e:next()do visit(e:current(),0)end;assert(found,'Squad button unavailable')
   local x,y,width,height=found:getAbsoluteCoord();local mx,my=math.floor(x+width/2),math.floor(y+height/2);local manager=MyGUI.InputManager.getInstance()
   manager.injectMouseMove(mx,my,0);manager.injectMousePress(mx,my,0);manager.injectMouseRelease(mx,my,0);return {x=mx,y=my,button=found:getName()}
  elseif choice=='ui-dump'then
   local rows={};local function visit(widget,depth)
    if not widget or depth>8 or #rows>=1500 then return end
    local ok,visible=pcall(function()return widget:getVisible()end);if not ok or not visible then return end
    local x,y,width,height=widget:getAbsoluteCoord();rows[#rows+1]={name=widget:getName(),x=x,y=y,width=width,height=height,depth=depth}
    for i=0,math.min(widget:getChildCount(),200)-1 do visit(widget:getChildAt(i),depth+1)end
   end
   local e=MyGUI.Gui.getInstance():getEnumerator();while e:next()do visit(e:current(),0)end;return {widgets=rows}
  elseif choice=='clock-result'then
   return clockLease or {available=false}
  elseif choice=='clock-day-test'or choice=='clock-night-test'then
   assert((not clockLease or clockLease.done) and _G.JACK_T60_LAMP_PROBE,'Clock test unavailable')
   local c=assert(list[owner],'Fixture owner not loaded');assert(team.members[owner]==c:getName(),'Fixture identity mismatch')
   clockLease={world=fixtureWorld(w),owner=owner,expires=os.time()+(choice=='clock-night-test' and 300 or 120),targetNight=choice=='clock-night-test',daySeen=nil}
   w:setGameSpeed(10,false);A.pause(w,false);return {started=true,expires=clockLease.expires}
  elseif choice=='lamp-on'or choice=='lamp-off'then
   assert(_G.JACK_T60_LAMP_ENABLE,'Lamp control unavailable');_G.JACK_T60_LAMP_ENABLE(choice=='lamp-on');return {enabled=choice=='lamp-on'}
  elseif choice=='perf-start'then
   if not _G.JACK_T60_PERF_START then dofile('D:/JACK/KenshiArmorMod/research/performance_20261101/perf_sample.lua')end
   return _G.JACK_T60_PERF_START(30)
  elseif choice=='perf-status'then
   assert(_G.JACK_T60_PERF_RESULT,'Sampler not started');return _G.JACK_T60_PERF_RESULT()
  elseif choice=='inspect'then
   local c=assert(list[owner],'Fixture owner not loaded');assert(team.members[owner]==c:getName(),'Fixture identity mismatch')
   local app=assert(c:getAppearance());local pointer=raw(app)
   local probe=ffi.load(plugins..'/T60VisibilityProbe_v089d.dll');ffi.cdef[[int T60_visibility_probe(void*,char*,size_t);]]
   local out=ffi.new('char[16384]');local n=probe.T60_visibility_probe(pointer,out,16384);assert(n>=0,'Visibility probe failed')
   local native=ffi.load(plugins..'/T60EquipmentVisibility_indexed.dll');ffi.cdef[[int T60_visibility_status(void*,char*,size_t);]]
   local indexed=ffi.new('char[16384]');local count=native.T60_visibility_status(pointer,indexed,16384);assert(count>=0,'Visibility status failed')
   return {owner=owner,visibility=ffi.string(out),indexed=ffi.string(indexed),power=A.power(c,'status')}
  elseif choice=='strength50'then
   local c=assert(list[owner],'Fixture owner not loaded');assert(owner~='1-2804199168-1-2987182592-1' and team.members[owner]==c:getName(),'Only created test fixtures')
   local s=c:getStats();local old=s._strength;s._strength=50;return {owner=owner,old=old,new=s._strength}
  elseif choice and choice:match('^gear:')then
   local c=assert(list[owner],'Fixture owner not loaded');assert(owner=='2-2411865344-1-2987182592-1','Gear changes confined to female fixture')
   local a=c:getAppearance();assert(not a.isCreatingBody and not a.updateBody,'Body busy')
   local fixed={shirt={'1167-gamedata.base',3,8},head={'2145-gamedata.base',3,3},armour={'2148-gamedata.base',3,5},boots={'549-gamedata.base',3,9},backpack={'576-gamedata.base',46,12}}
   local spec=assert(fixed[choice:sub(6)],'Unknown fixed gear');local inv=c:getInventory();local main=assert(inv:getSection('main'));local data=assert(w.gamedata:getData(spec[1],spec[2]));local item
   local all=inv:getAllItems();for i=1,#all do if all[i].data.stringID==spec[1]and not all[i].isEquipped then item=all[i];break end end
   if not item then assert(main:hasRoomForItem(data,1),'No legal space for gear');item=assert(w.theFactory:createItem(data,nil,nil,nil,95,c:getFaction()));assert(main:addItem(item,1),'Native gear supply refused')end
   local slot=assert(inv:getSectionOfType(spec[3]));local old=slot:getItem()
   if old then assert(main:hasRoomForItem(old.data,1),'No legal space for old gear');assert(slot:removeItem(old));if not main:addItem(old,1)then assert(slot:addItem(old,1));error('Old gear move rolled back')end end
   local equipped=inv:equipItem(item);if not equipped and old then assert(inv:equipItem(old),'Old gear rollback failed')end
   inv:notifyModified();return {owner=owner,item=spec[1],equipped=equipped,wardrobe=A.detail(c).wardrobe}
  elseif choice=='save:baseline'or choice=='save:armored'or choice=='save:ordinary'or choice=='save:cold1'or choice=='save:cold2'or choice=='save:gated1'then
   assert(team.created==4 and not team.pending and #w.player.playerCharacters==5,'Complete fixture required')
   for _,c in pairs(list)do local a=c:getAppearance();assert(a and not a.isCreatingBody and not a.updateBody,'Wait for body rebuild')end
   local root='D:/JACK/KenshiArmorMod/research/lifecycle_stage2_20261030/saves/';local name='T60_STAGE2_'..choice:sub(6):upper()
   local f=io.open(root..name..'/quick.save','rb');if f then f:close();error('Refuse to overwrite test slot')end
   return {operation='save',root=root,name=name,result=SaveManager.getSingleton():saveGame(root,name)}
  elseif choice=='supply'or choice=='wear'or choice=='unwear'or (choice and choice:match('^transfer:'))then
   local c=assert(list[owner],'Fixture owner not loaded');assert(team.members[owner]==c:getName(),'Fixture identity mismatch')
   local app=assert(c:getAppearance());assert(not app.isCreatingBody and not app.updateBody,'Body busy')
   local inv=c:getInventory();local main=assert(inv:getSection('main'));local data=assert(w.gamedata:getData('650-JACK_T60_WearLab.mod',3));local belt=inv:getSectionOfType(14);local item=belt and belt:getItem()
   if item and item.data.stringID~='650-JACK_T60_WearLab.mod'then item=nil end
   if choice:match('^transfer:')then item=nil end
   if not item then local all=inv:getAllItems();for i=1,#all do if all[i].data.stringID=='650-JACK_T60_WearLab.mod' and (not choice:match('^transfer:') or not all[i].isEquipped)then assert(not item,'Multiple components');item=all[i]end end end
   if choice=='supply'then
    assert(not item and main:hasRoomForItem(data,1),'Existing component or no legal inventory space')
    item=assert(w.theFactory:createItem(data,nil,nil,nil,95,c:getFaction()));assert(main:addItem(item,1),'Native inventory refused supply')
   elseif choice=='wear'then assert(item and not item.isEquipped,'Unequipped component required');assert(inv:equipItem(item),'Native equip refused')
   elseif choice=='unwear'then
    assert(item and item.isEquipped and main:hasRoomForItem(item.data,1),'Equipped component and legal space required')
    local source=assert(inv:getSection(item.inventorySection));assert(source:removeItem(item));if not main:addItem(item,1)then assert(source:addItem(item,1));error('Unequip rolled back')end
   else
    local destid=choice:sub(10);local dst=assert(list[destid],'Destination not loaded');assert(team.members[destid]==dst:getName()and destid~=owner,'Destination is not fixture')
    assert(item and not item.isEquipped,'Unequipped component required');local bag=assert(dst:getInventory():getSection('main'));assert(bag:hasRoomForItem(item.data,1),'Destination has no legal space')
    local source=assert(inv:getSection(item.inventorySection));assert(source:removeItem(item));if not bag:addItem(item,1)then assert(source:addItem(item,1));error('Transfer rolled back')end;dst:getInventory():notifyModified()
   end
   inv:notifyModified();return {operation=choice,owner=owner}
  end
  error('Unknown team operation')
 end
 local function fixtureCharacter()
  if not opponentLease then return end
  local w=getGameWorld()
  if fixtureWorld(w)~=opponentLease.world then opponentLease=nil;return end
  local things=opponentLease.platoon.activePlatoon:getThings()
  for i=1,#things do
   if raw(things[i])==opponentLease.character then return things[i]:getHandle():getCharacter()end
  end
 end
 local function removeOpponent()
  if not opponentLease then return {removed=true}end
  local l=opponentLease
  if fixtureWorld(getGameWorld())~=l.world then opponentLease=nil;return {unloaded=true}end
  local c=fixtureCharacter()
  if c then c:clearAllAIGoals();c:endCombatMode()end
  opponentLease=nil;l.faction:destroyPlatoon(l.platoon)
  return {removed=true}
 end
 function A.opponent(c,choice)
  local w=assert(getGameWorld());local list=w.player.playerCharacters
  assert(#list==1 and list[1]==c and c:getName()==config.test_character_name,'Opponent requires isolated test')
  assert(w.paused and not getOptionsHolder().autosave,'Pause and disable autosave first')
  if choice=='remove'then assert(not combatLease,'End sparring first');return removeOpponent()end
  if choice=='create'or choice=='create_far'or choice=='create_close'or choice=='create_magazine'then
   assert(not opponentLease and not combatLease,'Existing fixture must be removed first')
   assert(not c:isInCombatMode(true,true) and not c:isDead() and not c:isUnconcious(),'Actor must be ready')
   ffi.cdef[[int T60_attachment_ready(void);]]
   local verified=ffi.load(plugins..'/T60AttachmentCompat_v083b.dll')
   assert(verified.T60_attachment_ready()==1,'Unsupported engine build')
   local method=kernel.GetProcAddress(lib,'?createRandomCharacter@RootObjectFactory@@QEAAPEAVRootObject@@PEAVFaction@@VVector3@Ogre@@PEAVRootObjectContainer@@PEAVGameData@@PEAVBuilding@@M@Z')
   assert(method~=nil,'Character factory export unavailable')
   -- MSVC x64 passes the 12-byte by-value Vector3 indirectly. Nullable home is
   -- intentionally null; the generated Lua binding cannot represent it.
   local create=ffi.cast('void* (*)(void*,void*,const AgentMoveVector*,void*,void*,void*,float)',method)
   local gd=w.gamedata;local template=assert(gd:getData(choice=='create_magazine'and'701-JACK_EnergyWeapons.mod'or'1227-gamedata.base',1))
   local squad=assert(gd:getData('663-JACK_T60_WearLab.mod',52))
   local faction=assert(w.factionMgr:getOrCreateFaction(gd:getData('200-gamedata.base',10)))
   local p=c:getPosition();local distance=(choice=='create_far'or choice=='create_magazine')and 140 or(choice=='create_close'and 8 or 42)
   local pos={x=p.x+distance,y=p.y,z=p.z}
   local platoon=assert(faction:createNewEmptyActivePlatoon(squad,false,pos))
   opponentLease={world=fixtureWorld(w),platoon=platoon,faction=faction,expires=os.time()+(choice=='create_magazine'and 300 or 90),magazine=choice=='create_magazine'}
   local vector=ffi.new('AgentMoveVector',pos)
   opponentLease.character=create(raw(w.theFactory),raw(faction),vector,raw(platoon.activePlatoon),raw(template),nil,1)
   assert(opponentLease.character~=nil,'Opponent factory returned null; remove fixture')
  elseif choice=='hide'or choice=='show'then
   local other=assert(fixtureCharacter(),'No owned disposable opponent');local app=assert(other:getAppearance());assert(not app.isCreatingBody and not app.updateBody,'Opponent body busy')
   local og=kernel.GetModuleHandleA('OgreMain_x64.dll')
   local set=ffi.cast('void(*)(void*,unsigned int)',assert(kernel.GetProcAddress(og,'?setVisibilityFlags@MovableObject@Ogre@@QEAAXI@Z')))
   local get=ffi.cast('unsigned int(*)(void*)',assert(kernel.GetProcAddress(og,'?getVisibilityFlags@MovableObject@Ogre@@QEBAIXZ')))
   local entities={};if app:getBody()then entities[#entities+1]=ffi.cast('void*',app:getBody())end
   local bytes=ffi.cast('uint8_t*',raw(app));local n=tonumber(ffi.cast('uint64_t*',bytes+0x30)[0]);local index=tonumber(ffi.cast('uint64_t*',bytes+0x28)[0]);assert(n<=128 and(n==0 or index<4096),'Unexpected live attachment map '..tostring(n)..' / '..tostring(index))
   local buckets=ffi.cast('void***',bytes+0x48)[0];local node=n>0 and buckets[index]or nil;local visited=0
   while node~=nil do visited=visited+1;assert(visited<=128);local p=ffi.cast('uint8_t*',node);local obj=ffi.cast('uint8_t**',p+0x38)[0];local kind=tonumber(ffi.cast('int*',obj+8)[0]);local entity=ffi.cast('void**',obj+0x80)[0];if(kind==0 or kind==1)and entity~=nil then entities[#entities+1]=entity end;node=ffi.cast('void**',p)[0]end
   local saved=opponentLease.visibility or{};opponentLease.visibility=saved
   for _,entity in ipairs(entities)do local key=tostring(entity);if saved[key]==nil then saved[key]=tonumber(get(entity))end;set(entity,choice=='hide'and 0 or saved[key])end
   opponentLease.visibilityState={method='visibility_flags',hidden=choice=='hide',entities=#entities}
  else assert(choice=='status','Unknown opponent operation')end
  local other=fixtureCharacter()
  if not other then return {active=opponentLease~=nil,loading=true}end
  local h=other:getHandle();observedNPC[h:toString()]={handle=h,expires=os.time()+90}
  return {active=true,owner=h:toString(),name=other:getName(),position=other:getPosition(),
   dead=other:isDead(),unconscious=other:isUnconcious(),visibility=opponentLease.visibilityState,maximum_seconds=opponentLease.magazine and 300 or 90,template=opponentLease.magazine and'701-JACK_EnergyWeapons.mod'or'1227-gamedata.base'}
 end
 local function gui()return assert(getForgottenGUI(),'Game GUI unavailable')end
 local function manager()return assert(SaveManager.getSingleton(),'Save manager unavailable')end
 local migrationFixture
 local loadSignalTrace
 local worldEpochProbe
 local function migrationAction(w,list,choice)
  if choice=='epoch-status'then return worldEpochProbe and worldEpochProbe.sample()or(_G.JACK_T60_WORLD_EPOCH_STATUS and _G.JACK_T60_WORLD_EPOCH_STATUS()or{available=false})end
  if choice=='trace-state'then return loadSignalTrace and loadSignalTrace.status()or{available=false}end
  if choice=='pause-owned-reload'or choice=='trace-owned-load'or choice=='epoch-probe'or choice=='player-probe'or choice=='epoch-resolve'or choice=='epoch-adapter'then
   assert(not getOptionsHolder().autosave and #w.player.playerCharacters==5 and not gui():isLoading(),'Owned reload is not ready')
   local proof=dofile('D:/JACK/KenshiArmorMod/research/identity_20261101/owned_reload_fixture.lua');local count=0
   for id,c in pairs(list)do local p=assert(proof.members[c:getName()],'Unexpected loaded name');assert(id==p.handle and c.myRace.data.stringID==p.logical,'Unexpected saved actor');count=count+1 end;assert(count==5,'Five owned saved actors required')
   A.pause(w,true)
   if choice=='epoch-adapter'then return dofile('D:/JACK/KenshiArmorMod/research/identity_epoch_20261101/scripts/t60_world_epoch_adapter.lua').read()end
   if choice=='epoch-resolve'then return dofile('D:/JACK/KenshiArmorMod/research/world_epoch_20261101/native_entrypoints.lua').scan()end
   if choice=='epoch-probe'or choice=='player-probe'then worldEpochProbe=dofile('D:/JACK/KenshiArmorMod/research/world_epoch_20261101/epoch_probe.lua').new(choice=='player-probe'and'player'or nil);return worldEpochProbe.sample()end
   if choice=='trace-owned-load'then
    loadSignalTrace=dofile('D:/JACK/KenshiArmorMod/research/identity_20261101/load_signal_trace.lua').new(worldEpochProbe and worldEpochProbe.sample);loadSignalTrace.start(w)
    local path='D:/JACK/KenshiArmorMod/research/lifecycle_stage2_20261030/saves/';local name='T60_STAGE2_MIGRATION1';local f=assert(io.open(path..name..'/quick.save','rb'),'Owned save absent');f:close();local sm=manager();sm:load(name);sm.location=path;return {tracing=true,operation='load',name=name,root=path,deferred=true}
   end
   return {paused=w.paused,identity=assert(_G.JACK_T60_IDENTITY_STATUS)(),world=fixtureWorld(w),player=tostring(raw(w.player)),savedata=tostring(raw(w.savedata)),loading_from_save=w:isLoadingFromASaveGame(),resetting=w.gameResetting}
  end
  if choice=='pause-reloaded'or choice=='bind-reloaded'then
   assert(migrationFixture and migrationFixture.reloadRequested,'No owned reload requested')
   assert(not getOptionsHolder().autosave and #w.player.playerCharacters==5 and not gui():isLoading(),'Wait for five loaded actors without autosave')
   assert(migrationFixture.reloadRequested.name=='T60_STAGE2_MIGRATION1','Wrong owned reload request')
   local state=assert(_G.JACK_T60_IDENTITY_STATUS)();assert(state.epoch~=migrationFixture.reloadRequested.epoch and not state.stopped and not state.deferred,'Identity has not crossed a clean world boundary')
   local members={};for id,c in pairs(list)do local name=c:getName();local previous=assert(migrationFixture.members[name],'Unexpected loaded actor');assert(not members[name]and c.myRace.data.stringID==previous.race,'Loaded fixture race/name mismatch');members[name]={character=tostring(raw(c)),appearance=tostring(raw(c:getAppearance())),inventory=tostring(raw(c:getInventory())),stats=tostring(raw(c:getStats())),race=previous.race,initial_handle=id}end
   local n=0;for _ in pairs(members)do n=n+1 end;assert(n==5,'Five unique loaded actors required')
   A.pause(w,true)
   if choice=='bind-reloaded'then migrationFixture={world=fixtureWorld(w),members=members}end
   return {paused=w.paused,bound=choice=='bind-reloaded',identity=state}
  end
  assert(w.paused and not getOptionsHolder().autosave,'Pause isolated world and disable autosave')
  local fixed={['1-2804199168-1-2987182592-1']=config.test_character_name,['2-2411865344-1-2987182592-1']='T60_STAGE2_human_female',['3-1676391552-1-2987182592-1']='T60_STAGE2_shek_male',['4-3972167936-1-2987182592-1']='T60_STAGE2_shek_female',['5-3988769536-1-2987182592-1']='T60_STAGE2_human_male'}
  if choice=='recover'then
   assert(not migrationFixture and #w.player.playerCharacters==5,'Recovery requires fresh bridge and five actors')
   local proof=dofile('D:/JACK/KenshiArmorMod/research/identity_20261101/bridge_recovery_fixture.lua')
   local state=assert(_G.JACK_T60_IDENTITY_STATUS)();assert(state.epoch==proof.epoch and not state.stopped and not state.deferred,'Recovery world changed')
   local members={};for id,c in pairs(list)do local name=c:getName();local p=assert(proof.members[name],'Recovery name mismatch');assert(not members[name]and id==p.handle and tostring(raw(c))==p.character and tostring(raw(c:getAppearance()))==p.appearance and tostring(raw(c:getInventory()))==p.inventory and tostring(raw(c:getStats()))==p.stats and c.myRace.data.stringID==p.logical and assert(_G.JACK_T60_IDENTITY_OWNER)(c)==p.token,'Recovery fingerprint mismatch');members[name]={character=p.character,appearance=p.appearance,inventory=p.inventory,stats=p.stats,race=p.logical,initial_handle=id}end
   local n=0;for _ in pairs(members)do n=n+1 end;assert(n==5,'Incomplete recovery');migrationFixture={world=fixtureWorld(w),members=members};return {bound=true,recovered=true,identity=state}
  end
  if choice=='bind'then
   assert(not migrationFixture and #w.player.playerCharacters==5,'Fixture already bound or wrong count')
   local members={};for id,c in pairs(list)do local name=c:getName();assert(fixed[id]==name and not members[name],'Unexpected original fixture identity');members[name]={character=tostring(raw(c)),appearance=tostring(raw(c:getAppearance())),inventory=tostring(raw(c:getInventory())),stats=tostring(raw(c:getStats())),race=c.myRace.data.stringID,initial_handle=id} end
   local n=0;for _ in pairs(members)do n=n+1 end;assert(n==5,'Five fixture actors required');migrationFixture={world=fixtureWorld(w),members=members};return {bound=true,members=members}
  end
  assert(migrationFixture and migrationFixture.world==fixtureWorld(w) and #w.player.playerCharacters==5,'Fixture not bound or world changed')
  local current={};for id,c in pairs(list)do local name=c:getName();local expected=assert(migrationFixture.members[name],'Unexpected fixture name');assert(not current[name] and tostring(raw(c))==expected.character and tostring(raw(c:getAppearance()))==expected.appearance and tostring(raw(c:getInventory()))==expected.inventory and tostring(raw(c:getStats()))==expected.stats and c.myRace.data.stringID==expected.race,'Fixture identity changed');current[name]={handle=id,actor=c} end
  local n=0;for _ in pairs(current)do n=n+1 end;assert(n==5,'Missing fixture actor')
  if choice=='private-snapshot-resolve'then
   return dofile('D:/JACK/KenshiArmorMod/research/appearance_ownership_20261102/resolve_entrypoints.lua').scan()
  end
  if choice=='private-release-human-male'or choice=='private-release-human-female'then
   local key=choice=='private-release-human-female'and'T60_STAGE2_human_female'or'T60_STAGE2_human_male'
   local c=assert(current[key],'Missing fixed test actor').actor;local a=assert(c:getAppearance())
   assert(not a.isCreatingBody and not a.updateBody and A.bones(a)==30,'Stable ordinary actor required')
   local state=assert(_G.JACK_T60_IDENTITY_STATUS)();assert(not state.stopped and not state.deferred,'Identity unavailable')
   local module=_G.JACK_T60_PRIVATE_RELEASE or dofile('D:/JACK/KenshiArmorMod/research/private_snapshot_release_20261103/probe.lua').start()
   return module.trial(c,a,state.sourcegeneration)
  end
  if choice=='private-snapshot-human-male'or choice=='private-complete-human-male'or choice=='private-complete-human-female'then
   local key=choice=='private-complete-human-female'and'T60_STAGE2_human_female'or'T60_STAGE2_human_male'
   local c=assert(current[key],'Missing fixed test actor').actor;local a=assert(c:getAppearance())
   assert(not a.isCreatingBody and not a.updateBody and A.bones(a)==30,'Stable ordinary actor required')
   local state=assert(_G.JACK_T60_IDENTITY_STATUS)();assert(not state.stopped and not state.deferred,'Identity unavailable')
   local module;if choice=='private-snapshot-human-male'then module=_G.JACK_T60_PRIVATE_SNAPSHOT else module=_G.JACK_T60_PRIVATE_COMPLETE end
   return assert(module,'Initialize private research at empty menu').capture(c,a,state.sourcegeneration)
  end
  if choice=='drag'or choice=='ui-state'then
   local panels={};local function visit(widget,depth)if not widget or depth>8 or not widget:getVisible()then return end;if widget:getName():match('PortraitsPanel$')then panels[#panels+1]=widget end;for i=0,math.min(widget:getChildCount(),200)-1 do visit(widget:getChildAt(i),depth+1)end end
   local e=MyGUI.Gui.getInstance():getEnumerator();while e:next()do visit(e:current(),0)end;assert(#panels==2,'Expected two visible squad panels');table.sort(panels,function(a,b)local _,ay=a:getAbsoluteCoord();local _,by=b:getAbsoluteCoord();return ay<by end)
   local itemRows,seenNames={},{};local sourceIndex,sourceWidget;local total=0
   for pi,panel in ipairs(panels)do
    local count=panel:getItemCount();assert(count>=0 and count<=5,'Unexpected squad data count');total=total+count;itemRows[pi]={}
    for i=0,count-1 do
     local widget=assert(panel:getWidgetByIndex(i),'Squad item not instantiated');assert(widget:getInheritedVisible(),'Squad item hidden')
     local name;local function label(node,depth)
      if depth>6 then return end
      if node:getName():match('NameText$')then assert(not name,'Ambiguous portrait labels');name=node:getCaption()end
      for j=0,node:getChildCount()-1 do label(node:getChildAt(j),depth+1)end
     end;label(widget,0)
     assert(name and current[name]and not seenNames[name],'Portrait does not match bound fixture: '..tostring(name));seenNames[name]=true
     itemRows[pi][#itemRows[pi]+1]={index=i,name=name}
     if name=='T60_STAGE2_human_male'then assert(not sourceWidget,'Duplicate target portrait');sourceIndex=pi;sourceWidget=widget end
    end
   end
   assert(total==5 and sourceWidget,'Five unique bound portrait items required')
   if choice=='ui-state'then
    local result={};for pi,panel in ipairs(panels)do local row={name=panel:getName(),children={},items=itemRows[pi],itemCountMethod=type(panel.getItemCount)};local ok,count=pcall(function()return panel:getItemCount()end);if ok then row.item_count=count else row.item_error=tostring(count)end
     for i=0,panel:getChildCount()-1 do local widget=panel:getChildAt(i);local x,y,width,height=widget:getAbsoluteCoord();local child={index=i,name=widget:getName(),visible=widget:getVisible(),x=x,y=y,width=width,height=height,children={}};local ok,cap=pcall(function()return widget:getCaption()end);if ok then child.caption=cap end
      for j=0,math.min(widget:getChildCount(),8)-1 do local sub=widget:getChildAt(j);local ok,caption=pcall(function()return sub:getCaption()end);child.children[#child.children+1]={name=sub:getName(),visible=sub:getVisible(),caption=ok and caption or nil}end
      row.children[#row.children+1]=child
     end;result[#result+1]=row
    end;return {panels=result}
   end
   local ac,bc=panels[1]:getItemCount(),panels[2]:getItemCount();assert(ac==5 and bc==0 or ac==4 and bc==1,'Unexpected squad data contents');local dest=panels[3-sourceIndex];assert(#itemRows[sourceIndex]==5 or #itemRows[sourceIndex]==1,'Target is in unexpected squad')
   local sx,sy,sw,sh=sourceWidget:getAbsoluteCoord();local dx,dy,dw,dh=dest:getAbsoluteCoord();local offset=#itemRows[3-sourceIndex]*sw+sw/2;assert(offset<dw,'No visible empty drop cell');sx=math.floor(sx+sw/2);sy=math.floor(sy+sh/2);dx=math.floor(dx+offset);dy=math.floor(dy+math.min(sh/2,dh/2));local m=MyGUI.InputManager.getInstance();m.injectMouseMove(sx,sy,0);m.injectMousePress(sx,sy,0);for i=1,12 do m.injectMouseMove(math.floor(sx+(dx-sx)*i/12),math.floor(sy+(dy-sy)*i/12),0)end;m.injectMouseRelease(dx,dy,0);return {from={x=sx,y=sy},to={x=dx,y=dy},before_counts={ac,bc},target='T60_STAGE2_human_male'}
  end
  if choice=='save'or choice=='save2'or choice=='save3'or choice=='save4'or choice=='save5'or choice=='save6'then
   for _,v in pairs(current)do local a=v.actor:getAppearance();assert(a and not a.isCreatingBody and not a.updateBody,'Wait for body rebuild')end
   local path='D:/JACK/KenshiArmorMod/research/lifecycle_stage2_20261030/saves/';local name=choice=='save6'and'T60_STAGE2_MIGRATION6'or choice=='save5'and'T60_STAGE2_MIGRATION5'or choice=='save4'and'T60_STAGE2_MIGRATION4'or choice=='save3'and'T60_STAGE2_MIGRATION3'or choice=='save2'and'T60_STAGE2_MIGRATION2'or'T60_STAGE2_MIGRATION1';local f=io.open(path..name..'/quick.save','rb');if f then f:close();error('Refuse to overwrite test slot')end
   return {operation='save',name=name,root=path,result=SaveManager.getSingleton():saveGame(path,name)}
  end
  if choice=='reload'then
   local path='D:/JACK/KenshiArmorMod/research/lifecycle_stage2_20261030/saves/';local name='T60_STAGE2_MIGRATION1'
   local f=assert(io.open(path..name..'/quick.save','rb'),'Owned test save absent');f:close()
   migrationFixture.reloadRequested={name=name,epoch=assert(_G.JACK_T60_IDENTITY_STATUS)().epoch}
   local sm=manager();sm:load(name);sm.location=path;return {operation='load',name=name,root=path,deferred=true}
  end
  if choice=='status'then local status=assert(_G.JACK_T60_IDENTITY_STATUS,'Identity status unavailable');local owner=assert(_G.JACK_T60_IDENTITY_OWNER,'Identity owner unavailable');local state=status();assert(not state.stopped and not state.deferred,'Identity stopped/deferred');local rows={};for name,v in pairs(current)do local c=v.actor;local a=c:getAppearance();local s=c:getStats();local token=assert(owner(c),'Actor not eligible');rows[name]={token=token,handle=v.handle,character=tostring(raw(c)),inventory=tostring(raw(c:getInventory())),stats=tostring(raw(s)),appearance=tostring(raw(a)),appearance_data=tostring(raw(a.appearanceData)),logical=c.myRace.data.stringID,visual=a.raceData.stringID,female=a.female,raw_strength=s._strength,strength=s:strengthActual(),bones=not a.isCreatingBody and not a.updateBody and a:getBody() and A.bones(a) or nil,wardrobe=A.detail(c).wardrobe}end;ffi.cdef[[int T60_material_slots(void);]];local material=ffi.load(plugins..'/T60MaterialBridge_v091.dll');return {members=rows,identity=state,material_slots=material.T60_material_slots(),wear_controller=_G.JACK_T60_WEAR_STATUS and _G.JACK_T60_WEAR_STATUS()or nil,attachment_trace=_G.JACK_T60_ATTACHMENT_TRACE and _G.JACK_T60_ATTACHMENT_TRACE()or nil}end
  local op,profile=choice:match('^(%a+):([%w_]+)$');local name=profile and ('T60_STAGE2_'..profile);local v=name and assert(current[name],'Unknown fixture profile');assert(v and (op=='wear'or op=='unwear'),'Unknown migration operation')
  local c=v.actor;local app=assert(c:getAppearance());assert(not app.isCreatingBody and not app.updateBody,'Body busy');local inv=c:getInventory();local main=assert(inv:getSection('main'));local belt=inv:getSectionOfType(14);local item=belt and belt:getItem();if item and item.data.stringID~='650-JACK_T60_WearLab.mod'then item=nil end
  if not item then local all=inv:getAllItems();for i=1,#all do if all[i].data.stringID=='650-JACK_T60_WearLab.mod'then assert(not item,'Multiple components');item=all[i]end end end
  if op=='wear'then assert(item and not item.isEquipped,'Unequipped component required');assert(inv:equipItem(item),'Native equip refused')
  else assert(item and item.isEquipped and main:hasRoomForItem(item.data,1),'Equipped component and legal space required');local source=assert(inv:getSection(item.inventorySection));assert(source:removeItem(item));if not main:addItem(item,1)then assert(source:addItem(item,1));error('Unequip rolled back')end end
  inv:notifyModified();return {operation=op,name=name,handle=v.handle}
 end
 local visibilityRebuilds=0
 function A.lifecycle(w,list,req)
  local sm=manager();local root='D:/JACK/KenshiArmorMod/research/lifecycle_v096/saves/'
  if req.target=='ownership:entrypoints'then
   assert(#w.player.playerCharacters==0,'Resolve ownership entrypoints only at empty menu')
   return dofile('D:/JACK/KenshiArmorMod/research/appearance_ownership_20261102/resolve_entrypoints.lua').scan()
  end
  if req.target=='ownership:probe-start'then
   assert(#w.player.playerCharacters==0,'Install observation only at empty menu')
   return dofile('D:/JACK/KenshiArmorMod/research/appearance_ownership_20261102/probe.lua').start()
  end
  if req.target=='ownership:private-snapshot-start'then
   assert(#w.player.playerCharacters==0,'Initialize private research only at empty menu')
   return dofile('D:/JACK/KenshiArmorMod/research/private_snapshot_20261103/probe.lua').start()
  end
  if req.target=='ownership:private-complete-start'then
   assert(#w.player.playerCharacters==0,'Initialize private research only at empty menu')
   return dofile('D:/JACK/KenshiArmorMod/research/private_snapshot_complete_20261103/probe.lua').start()
  end
  if req.target=='ownership:lifetime-status'then return assert(_G.JACK_T60_LIFETIME_STATUS,'Lifetime ledger unavailable')()end
  if req.target=='ownership:save-status'then if _G.JACK_T60_SAVE_READER_STATUS then return _G.JACK_T60_SAVE_READER_STATUS()end;return {native=assert(_G.JACK_T60_SAVE_STATUS)(),reader_status_available=false}end
  if req.target=='ownership:probe-status'then return assert(_G.JACK_T60_OWNERSHIP_STATUS,'Ownership observer unavailable')()end
  if req.target=='identity-status' then local fn=_G.JACK_T60_IDENTITY_STATUS;return {available=not not fn,status=fn and fn()or nil}end
  if req.target and req.target:match('^migration:')then return migrationAction(w,list,req.target:sub(11))end
  if req.target=='stage2-identity' then
   assert(w.paused and not getOptionsHolder().autosave,'Pause isolated world and disable autosave')
   local names={[config.test_character_name]=true,T60_STAGE2_human_female=true,T60_STAGE2_shek_male=true,T60_STAGE2_shek_female=true,T60_STAGE2_human_male=true};local rows={};local count=0
   for id,c in pairs(list)do local name=c:getName();assert(names[name] and not rows[name],'Unexpected actor');local a=c:getAppearance();local s=c:getStats();rows[name]={handle=id,character=tostring(raw(c)),appearance=tostring(raw(a)),appearance_data=tostring(raw(a.appearanceData)),logical=c.myRace.data.stringID,visual=a.raceData.stringID,female=a.female,raw_strength=s._strength,strength=s:strengthActual()};count=count+1 end
   assert(count==5 and #w.player.playerCharacters==5,'Five fixture actors required');return {members=rows}
  end
  if req.target=='stage2-warm-status' then
   assert(_G.JACK_T60_CACHE_WARM,'Candidate warm hook not installed')
   return {warm=_G.JACK_T60_CACHE_WARM()}
  end
  if req.target=='stage2-pause' then
   assert(not getOptionsHolder().autosave,'Autosave must be disabled')
   local expected={['1-2804199168-1-2987182592-1']=config.test_character_name,['2-2411865344-1-2987182592-1']='T60_STAGE2_human_female',['3-1676391552-1-2987182592-1']='T60_STAGE2_shek_male',['4-3972167936-1-2987182592-1']='T60_STAGE2_shek_female',['5-3988769536-1-2987182592-1']='T60_STAGE2_human_male'}
   local count=0;for id,c in pairs(list)do assert(expected[id]==c:getName(),'Unexpected fixture');count=count+1 end
   assert(count==5 and #w.player.playerCharacters==5,'Five fixture actors required')
   A.pause(w,true);return {paused=w.paused,actors=count}
  end
  if req.target=='worker-status' then
   ffi.cdef[[typedef struct { char text[16]; size_t size; size_t capacity; } AgentSmallString;]]
   local og=assert(kernel.GetModuleHandleA('OgreMain_x64.dll'))
   local singleton=ffi.cast('void* (*)()',assert(kernel.GetProcAddress(og,'?getSingleton@Root@Ogre@@SAAEAV12@XZ')))
   local lookup=ffi.cast('void* (*)(void*,const AgentSmallString*)',assert(kernel.GetProcAddress(og,'?getSceneManager@Root@Ogre@@QEBAPEAVSceneManager@2@AEBV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z')))
   local count=ffi.cast('size_t (*)(void*)',assert(kernel.GetProcAddress(og,'?getNumWorkerThreads@SceneManager@Ogre@@QEBA_KXZ')))
   local name=ffi.new('AgentSmallString');ffi.copy(name.text,'scenemanager',12);name.size=12;name.capacity=15
   local scene=assert(lookup(singleton(),name),'Scene unavailable');return {worker_threads=tonumber(count(scene))}
  end
  if req.target=='load:STAGE2_ARMORED' or req.target=='load:STAGE2_COLD1' or req.target=='load:STAGE2_COLD2' or req.target=='load:STAGE2_GATED1' then
   assert(#w.player.playerCharacters==0,'Stage2 load only from empty menu')
   getOptionsHolder().autosave=false
   assert(not getOptionsHolder().autosave,'Could not disable autosave')
   local path='D:/JACK/KenshiArmorMod/research/lifecycle_stage2_20261030/saves/'
   local name='T60_'..req.target:sub(6);local f=assert(io.open(path..name..'/quick.save','rb'),'Stage2 save missing');f:close()
   sm:load(name);sm.location=path;return {operation='load',root=path,name=name,deferred=true}
  end
  if req.target=='single-visibility-rebuild'then
   -- Reuse the full fixed-load/GUI/epoch/single-actor admission proof.
   local proof=A.lifecycle(w,list,{target='single-telemetry'})
   assert(proof and visibilityRebuilds<2,'Visibility rebuild fixture budget exhausted')
   local c=w.player.playerCharacters[1];local a=assert(c:getAppearance())
   assert(w.paused and not a.isCreatingBody and not a.updateBody,'Pause stable fixture first')
   visibilityRebuilds=visibilityRebuilds+1;a:reload()
   return {requested=true,ordinal=visibilityRebuilds,maximum=2,native_reload=true,real_zone_unload=false}
  end
  if req.target=='single-telemetry'then
   return dofile(config.root..'/single_telemetry.lua').snapshot(w.player and w.player.playerCharacters[1],config,{
    world=function()return w end,autosave=function()return getOptionsHolder().autosave end,
    lifecycle=function()return assert(_G.JACK_T60_WORLD_EPOCH_STATUS,'Lifecycle status unavailable')()end,
    gui_loading=function()return gui():isLoading()end,
    load_proof=function()return singleTelemetryProof end,
    load_status=function()return {name=sm.name,location=sm.location,signal=sm.signal,current_game=sm:getCurrentGame()}end,
    identity=function()return assert(_G.JACK_T60_IDENTITY_STATUS,'Identity status unavailable')()end,
    owner=function(c)return assert(_G.JACK_T60_IDENTITY_OWNER,'Identity owner unavailable')(c)end,
    wear=function()return assert(_G.JACK_T60_WEAR_STATUS,'Wear metadata unavailable')()end,
    material_slots=function()
     -- Inspect an already loaded, exact-path production module; never LoadLibrary.
     ffi.cdef[[unsigned long GetModuleFileNameA(void*,char*,unsigned long);]]
     local path=(plugins..'/T60MaterialBridge_v091.dll'):gsub('/','\\')
     local module=kernel.GetModuleHandleA(path);assert(module~=nil,'Material module not already loaded')
     local filename=ffi.new('char[32768]');local n=tonumber(kernel.GetModuleFileNameA(module,filename,32768))
     assert(n>0 and n<32768 and ffi.string(filename):lower()==path:lower(),'Material module path mismatch')
     local address=kernel.GetProcAddress(module,'T60_material_slots');assert(address~=nil,'Material counter export unavailable')
     return tonumber(ffi.cast('int (*)(void)',address)())
    end})
  end
  local count=0;local actor
  for _,c in pairs(list)do assert(c:getName()==config.test_character_name,'Lifecycle limited to isolated actor');actor=c;count=count+1 end
  assert(count<=1,'Lifecycle requires single actor or empty menu')
  local choice=req.target or'status'
  if choice=='normalize-inventory'then
   assert(count==1 and w.paused and not getOptionsHolder().autosave,'Pause isolated actor first')
   local inv=actor:getInventory();local main=assert(inv:getSection('main'));local backpack=assert(actor:hasABackpackOn(),'Real backpack required');local dst=assert(backpack:getInventory())
   -- Root getAllItems includes backpack descendants whose local section is also main.
   -- Read this actual section's members, never infer ownership from section name.
   local all=main:getItems();local items={}
   for i=1,#all do local it=all[i].item;if it and it.data.stringID~='650-JACK_T60_WearLab.mod'then items[#items+1]=it end end
   local moved={}
   for _,it in ipairs(items)do
    local n=it.quantity;if not dst:hasRoomForItem(it.data)then break end;assert(main:removeItem(it))
    if not dst:addItem(it,n,false,false)then assert(main:addItem(it,n));error('Backpack transfer rolled back')end
    moved[#moved+1]={id=it.data.stringID,quantity=n}
   end
   main:autoArrange();inv:notifyModified();dst:notifyModified();local remaining={};local members=main:getItems();for i=1,#members do local m=members[i];remaining[#remaining+1]={id=m.item.data.stringID,x=m.x,y=m.y,w=m.w,h=m.h}end;return {moved=moved,main={width=main.width,height=main.height,items=remaining}}
  end
  if choice=='drop-test-overflow'then
   assert(count==1 and w.paused and not getOptionsHolder().autosave,'Pause isolated actor first')
   local inv=actor:getInventory();local main=assert(inv:getSection('main'));local all=main:getItems();local selected={}
   for i=1,#all do local it=all[i].item;if it.data.stringID=='210-JACK_EnergyWeapons.mod'and #selected<4 then selected[#selected+1]=it end end
   local dropped={};for _,it in ipairs(selected)do dropped[#dropped+1]={id=it.data.stringID,quantity=it.quantity};inv:dropItem(it)end
   main:autoArrange();inv:notifyModified();return {dropped_to_ground=dropped,destroyed=0}
  end
  if choice=='status'then
   local r={root=root,current=sm:getCurrentGame(),local_path=sm.localSavePath,user_path=sm.userSavePath,
    save_method=type(sm.save),save_game_method=type(sm.saveGame),load_method=type(sm.load),signal=sm.signal,
    save_original_runtime=_G.JACK_T60_SAVE_STATUS and _G.JACK_T60_SAVE_STATUS()or nil}
   if actor then
    local stats=actor:getStats();local a=actor:getAppearance()
    r.actor={name=actor:getName(),logical=actor.myRace.data.stringID,visual=a.raceData.stringID,female=a.female,raw_strength=stats._strength,raw_dexterity=stats._dexterity,
     appearance=tostring(a.appearanceData),hair=a.hairStyle and a.hairStyle.stringID or'',shaved=a.shaved,body=a.bodyFilename}
   end
   return r
  end
  local action,name=choice:match('^(%a+):([%w_]+)$')
  assert((action=='save'or action=='load')and name and name:match('^T60_LIFE_096_[%w_]+$')and #name<=64,'Invalid isolated test slot')
  if action=='save'then
   assert(count==1 and w.paused and not getOptionsHolder().autosave and not combatLease and not opponentLease,'Pause isolated actor, disable autosave, remove fixtures first')
   local a=assert(actor:getAppearance());assert(not a.isCreatingBody and not a.updateBody,'Wait for appearance rebuild')
   local f=io.open(root..name..'/quick.save','rb');if f then f:close();error('Refuse to overwrite existing test slot')end
   local result=sm:saveGame(root,name);return {operation=action,root=root,name=name,result=result}
  end
  assert(count==0 or w.paused and not getOptionsHolder().autosave and not combatLease and not opponentLease,'Pause isolated session before load')
  local f=assert(io.open(root..name..'/quick.save','rb'),'Isolated slot absent');f:close()
  -- loadGame executes world teardown synchronously and must not run inside a
  -- GUI-frame observer. Use the engine's normal deferred load request, then
  -- route that request to our fixed test-only location before execute() runs.
  local before=assert(_G.JACK_T60_IDENTITY_STATUS,'Identity status unavailable')()
  local boundary=assert(_G.JACK_T60_WORLD_EPOCH_STATUS,'Lifecycle status unavailable')()
  assert(not before.stopped and type(before.epoch)=='number' and before.epoch>=0,'Identity epoch unavailable or stopped')
  assert(boundary.guiThread==true and boundary.stable==true and boundary.busy==false,'Lifecycle busy')
  assert(count==0 or not before.deferred and not boundary.loading and before.sourcegeneration==boundary.generation,'Loaded world not stable')
  singleTelemetryProof=nil
  sm:load(name);sm.location=root
  singleTelemetryProof={name=name,root=root,epoch=before.epoch+1,before_generation=boundary.generation}
  return {operation=action,root=root,name=name,deferred=true,signal=sm.signal}
 end
 function A.describe()
  local g=gui();local sm=manager()
  local e=g:isCharacterEditorMode() and g.characterEditor
  local w=getGameWorld();local cam=w and w.player and w.player.camera
  return {editor=g:isCharacterEditorMode(),loading=g:isLoading(),
   editor_name=e and e.character and e.character:getName() or '',
   editor_midgame=e and e.isMidGame or false,
   editor_count=e and #e.characters or 0,
   active_save=sm:getCurrentGame(),autosave_paused=sm.pauseAutoSaveTimer,
   autosave_enabled=getOptionsHolder().autosave,
   camera=cam and {yaw=cam.yaw,pitch=cam.pitch,center=cam:getCenter(),
    position=cam:getCameraPos(),facing=cam:getFacingDirection()} or {}}
 end
 function A.bones(a)return probe.bones(a:getBody())end
 function A.motion(a)
  if not ok then return 'Motion DLL unavailable' end
  local body=ffi.cast('void*',a:getBody());if body==nil then return '' end
  local n=motion.T60_motion_snapshot(body,buffer,16384)
  assert(n>=0,'Native motion read failed '..tostring(n));return ffi.string(buffer)
 end
 function A.sources(c)
  assert(ok,'Motion DLL unavailable')
  local out=ffi.new('char[65536]')
  local n=motion.T60_motion_sources(ffi.cast('void*',c:getAppearance():getBody()),out,65536)
  assert(n>=0,'Source read failed '..tostring(n))
  local result={count=n,sources=ffi.string(out)}
  local auditOK,audit=pcall(ffi.load,plugins..'/T60ClipAudit_v090.dll')
  if auditOK then
   ffi.cdef[[int T60_clip_audit(void*,char*,size_t);]]
   local data=ffi.new('char[1048576]');local count=audit.T60_clip_audit(ffi.cast('void*',c:getAppearance():getBody()),data,1048576)
   assert(count>=0,'Read-only clip audit failed '..tostring(count));result.clip_audit=ffi.string(data)
  end
  ffi.cdef[[int T60_alias_names(void*,char*,size_t);]]
  local available,aliases=pcall(ffi.load,plugins..'/T60AnimationCompat_v083a.dll')
  if available then
   local names=ffi.new('char[65536]')
   local count=aliases.T60_alias_names(ffi.cast('void*',c:getAppearance():getBody()),names,65536)
   assert(count>=0,'Animation name read failed '..tostring(count))
   result.names=ffi.string(names)
  else result.names_error='Optional animation-name helper unavailable' end
  local poseOK,poses=pcall(ffi.load,plugins..'/T60BonePose_v084.dll')
  if poseOK then
   ffi.cdef[[int T60_bone_pose(void*,char*,size_t);]]
   local data=ffi.new('char[65536]')
   local count=poses.T60_bone_pose(ffi.cast('void*',c:getAppearance():getBody()),data,65536)
   assert(count>=0,'Bone pose read failed '..tostring(count))
   result.bone_pose=ffi.string(data)
  end
  return result
 end
 function A.mounts(c,enabled)
  -- Exact single-actor test only. The helper refuses unrecognized executables.
  local w=assert(getGameWorld());local list=w.player.playerCharacters
  assert(#list==1 and list[1]==c and c:getName()==config.test_character_name,
   'Attachment experiment requires the isolated test')
  local a=assert(c:getAppearance());assert(not a.isCreatingBody and not a.updateBody,'Body busy')
  ffi.cdef[[int T60_attachment_read(void*,char*,size_t);int T60_attachment_sync(void*,char*,size_t);]]
  local native=ffi.load(plugins..'/T60AttachmentCompat_v083b.dll')
  local out=ffi.new('char[4096]');local raw=ffi.cast('void**',a)[0]
  local n
  if enabled then
   n=native.T60_attachment_sync(raw,out,4096)
   if n>=0 then a.updatedAttachments=true;a:notifyDirty() end
  else n=native.T60_attachment_read(raw,out,4096) end
  assert(n>=0,'Attachment helper refused operation '..tostring(n))
  local result={changed=enabled and n==1 or false,diagnostic=ffi.string(out)}
  if enabled then
   local loaded,rebind=pcall(ffi.load,plugins..'/T60AttachmentRebind_v086c.dll')
   if loaded then
    ffi.cdef[[int T60_attachment_rebind(void*);]]
    local count=rebind.T60_attachment_rebind(raw)
    assert(count>=0 or count==-12,'Native attachment rebind failed '..tostring(count))
    result.rebound=count;result.rebind_pending=count==-12
   end
  end
  -- Optional read-only geometry helper: compare the real body/bone and weapon
  -- transforms, rather than treating a matching cache address as acceptance.
  local loaded,geometry=pcall(ffi.load,plugins..'/T60MountGeometry_v086d.dll')
  if loaded then
   ffi.cdef[[int T60_mount_geometry_read(void*,char*,size_t);]]
   local data=ffi.new('char[8192]');local code=geometry.T60_mount_geometry_read(raw,data,8192)
   if code==0 then result.geometry=ffi.string(data) else result.geometry_error=code end
  end
  local probeOK,visibility=pcall(ffi.load,plugins..'/T60VisibilityProbe_v089d.dll')
  if probeOK then
   ffi.cdef[[int T60_visibility_probe(void*,char*,size_t);]]
   local data=ffi.new('char[16384]');local n=visibility.T60_visibility_probe(raw,data,16384)
   if n>=0 then result.visibility=ffi.string(data) else result.visibility_error=n end
  end
  if _G.JACK_CHAIN_MATERIALS then result.weapon_materials=_G.JACK_CHAIN_MATERIALS(a) end
  return result
 end
 function A.motion_trace(c,enabled)
  assert(c:getName()==config.test_character_name,'Not the test actor')
  assert(#getGameWorld().player.playerCharacters==1,'Trace requires the isolated test')
  if enabled then
   assert(not trace or not trace.active,'Trace already active')
   ffi.cdef[[int T60_bone_pose(void*,char*,size_t);]]
   trace={active=true,owner=c:getHandle():toString(),elapsed=0,rows={},
    native=ffi.load(plugins..'/T60BonePose_v084.dll'),buffer=ffi.new('char[65536]')}
   return {active=true,maximum_seconds=6,maximum_frames=300}
  end
  assert(trace,'No trace has been requested')
  return {active=trace.active,elapsed=trace.elapsed,rows=trace.rows,error=trace.error}
 end
 function A.set_gait(c,mode)
  local orders=MessageForB.StandingOrder
  local map={[0]=orders.M_SET_ORDER_WALK,[1]=orders.M_SET_ORDER_JOG,[2]=orders.M_SET_ORDER_RUN}
  c:setStandingOrder(assert(map[mode],'Missing gait enum'),true)
 end
 function A.get_gait(c)return c:getMovementSpeedOrders()end
 function A.move(c,p)
  assert(c:isPlayerCharacter() and c:getName()==config.test_character_name,'Not the test actor')
  -- BindingHelpers.pushObject allocates one void* of userdata, not the object itself.
  local actor=ffi.cast('void**',c)[0];assert(actor~=nil,'Character pointer unavailable')
  local v=ffi.new('AgentMoveVector[1]');v[0].x=p.x;v[0].y=p.y;v[0].z=p.z
  playerMove(actor,nil,nil,v)
 end
 function A.halt(c)c:clearAllAIGoals();c.movement:halt()end
 function A.wear(c,enabled)
  assert(c:getName()==config.test_character_name,'Not the test actor')
  -- Never synthesize F9: the engine also binds it to quickload.
  local inv=assert(c:getInventory(),'Inventory unavailable')
  local belt=inv:getSectionOfType(14)
  local item=belt and belt:getItem() or c:getUpperBodyArmour()
  if item and item.data.stringID~='650-JACK_T60_WearLab.mod' then item=nil end
  if not item then
   local all=inv:getAllItems()
   for i=1,#all do
    if all[i].data and all[i].data.stringID=='650-JACK_T60_WearLab.mod' then
     assert(not item,'Multiple test components');item=all[i]
    end
   end
  end
  assert(item,'Test component missing')
  if enabled then
   if item.isEquipped then return end
   assert(inv:equipItem(item),'Engine refused to equip component')
  else
   if not item.isEquipped then return end
   local source=assert(inv:getSection(item.inventorySection),'Source slot unavailable')
   local bag=assert(inv:getSection('main'),'Main bag unavailable')
   assert(bag:hasRoomForItem(item.data,1),'No room to unequip component')
   assert(source:removeItem(item),'Engine refused to remove component')
   if not bag:addItem(item,1) then
    assert(source:addItem(item,1),'Component rollback failed')
    error('Engine refused the bag transfer; original slot restored')
   end
  end
  inv:notifyModified()
 end
 function A.detail(c)
  local h=c:isHuman();local combat=c:getCombatClass()
  local weapon=c:getCurrentWeapon()
  local med=c:getMedical();local health={}
  local movement={};pcall(function()local m=c.movement;movement={orders=tonumber(m:getSpeedOrders()),desired=m.desiredSpeed,maximum=m.maxSpeed,walk=m.walkSpeed}end)
  if med then
   local ok,values=pcall(function()return {left_leg=med.leftLeg.derivedFleshHealthPercent,right_leg=med.rightLeg.derivedFleshHealthPercent,
    movement_multiplier=med:getMovementSpeedInjuryMultiplier()}end)
   if ok then health=values end
  end
  local wardrobe={};local inv=c:getInventory()
  for _,slot in ipairs({0,1,3,5,6,8,9,12,14}) do
   local sec=inv and inv:getSectionOfType(slot);local it=sec and sec:getItem()
   if it then wardrobe[tostring(slot)]={id=it.data.stringID,equipped=it.isEquipped,section=it.inventorySection}end
  end
  local ammo={};if inv then local items=inv:getAllItems();for i=1,#items do local it=items[i];local id=it.data and it.data.stringID
   if id=='200-JACK_EnergyWeapons.mod' or id=='210-JACK_EnergyWeapons.mod' or id=='95781-rebirth.mod'then ammo[#ammo+1]={id=id,quantity=it.quantity,charges=it.chargesLeft,full=it.originalFullChargeAmount}end
  end end
  local identity={}
  pcall(function()local race=c:getRace();identity.logical_race=race and race.data and race.data.stringID;identity.logical_name=race and race.data and race.data.name end)
  pcall(function()local a=c:getAppearance();identity.visual_race=a:getRace().stringID;identity.female=a:isFemale();identity.height=a:getCharacterHeight()end)
  return {identity=identity,ammo=ammo,energy=_G.JACK_ENERGY_STATUS and _G.JACK_ENERGY_STATUS()or nil,wardrobe=wardrobe,held=h and h.weaponInHands~=nil or false,combat=c:isInCombatMode(true,true),
   attacking=combat and combat._isAttacking or 0,injured=c:isInjured(),
   dead=c:isDead(),unconscious=c:isUnconcious(),health=health,fleeing=c:isFleeing(),movement=movement,
   weapon=weapon and weapon.data and weapon.data.stringID or '',
   weapon_category=weapon and tonumber(weapon:getCategory_animationOverride()) or -1,
   chain_routing=_G.JACK_CHAIN_STATUS and _G.JACK_CHAIN_STATUS() or nil}
 end
 function A.new_test(w,list,req)
  assert(not next(list),'New test can only start from an empty main menu')
  assert(not gui():isCharacterEditorMode(),'A new-game editor is already open')
  assert(not w.gameResetting,'World reset in progress')
  local sm=manager();sm.pauseAutoSaveTimer=true
  local starts={laser='602-JACK_EnergyWeapons.mod',gauss='612-JACK_EnergyWeapons.mod',control=config.test_start_id}
  local start=req and req.target and assert(starts[req.target],'Unknown isolated test start')or config.test_start_id
  if req and req.profile and req.profile:match('^shek_')then
   assert(start==config.test_start_id,'Race override limited to configured isolated start')
   local data=assert(w.gamedata:getData(start,64));assert(not startRaceOverride,'Previous test race override not restored')
   assert(data:getListSize('force race')==1 and data:getFromList('force race',0)=='17-gamedata.quack','Unexpected original test race restriction');local refs={{id='17-gamedata.quack',v=0,v2=0,v3=0}}
   startRaceOverride={data=data,refs=refs};data:clearList('force race');data:addToList('force race','5276-chareditor.mod',0,0,0)
  end
  sm:newGame(start)
 end
 function A.replace_test(w,list,req)
  local all=w.player.playerCharacters
  assert(#all==1 and all[1]:getName()==config.test_character_name,'Only the isolated test may be replaced')
  assert(w.paused and not getOptionsHolder().autosave and not combatLease and not opponentLease,'Pause, disable autosave and remove all fixtures first')
  local c=all[1];local appearance=c:getAppearance()
  assert(appearance and not appearance.isCreatingBody and not appearance.updateBody and A.bones(appearance)==30,'Restore the original human body before replacing the test')
  assert(not weaponTests.select(c,'status').leased and not serviceTests.select(c,'status').active,'Restore temporary fixtures first')
  A.new_test(w,{},req)
 end
 function A.profile_editor(w,list,req)
  assert(not next(list),'Profiles can only change in the new-game editor')
  local g=gui();assert(g:isCharacterEditorMode(),'New-game editor is not active')
  local e=assert(g.characterEditor);assert(not e.isMidGame and #e.characters==1,'Not the isolated new-game editor')
  local c=assert(e.character,'No editor preview character');assert(c:getName()==config.test_character_name,'Unexpected editor character')
  local profiles={human_male={'17-gamedata.quack',false},human_female={'17-gamedata.quack',true},
   scorch_male={'18019-gamedata.base',false},scorch_female={'18019-gamedata.base',true},
   shek_male={'5276-chareditor.mod',false},shek_female={'5276-chareditor.mod',true}}
  local wanted=assert(profiles[req.target],'Unknown bounded test profile')
  local function info()
   local a=c:getAppearance();return {selected_race=e.raceData and e.raceData.stringID or '',visual_race=a and a:getRace().stringID or '',
    female=a and a:isFemale() or false,gender_index=e.currentGender,group_index=e.currentRaceGroupIndex,subrace_index=e.currentSubRaceIndex}
  end
  local before=info();local changed='none'
  if before.selected_race~=wanted[1] then
   local human={['17-gamedata.quack']=true,['18019-gamedata.base']=true}
   if human[before.selected_race] and human[wanted[1]] then e:nextSubRace(e.btnNextSubRace);changed='subrace'
   else e:nextRace(e.btnNextRace);changed='race'end
  elseif before.female~=wanted[2] then e:changeGender(e.btnNextGender);changed='gender'end
  local after=info();after.changed=changed;after.requested=req.target
  after.ready=after.selected_race==wanted[1] and after.visual_race==wanted[1] and after.female==wanted[2]
  return after
 end
 function A.finish_editor(w,list)
  local g=gui();assert(g:isCharacterEditorMode(),'Character editor is not active')
  local editor=assert(g.characterEditor,'Character editor missing')
  -- New-game preview actors are not player members until confirmation.
  assert(not editor.isMidGame and #editor.characters==1,'Not the isolated new-game editor')
  assert(editor.character,'No editor preview character')
  assert(editor.character:getName()==config.test_character_name,'Unexpected test character')
  editor:confirmButton(editor.txtName)
  if startRaceOverride then
   local old=startRaceOverride;old.data:clearList('force race');for _,v in ipairs(old.refs)do old.data:addToList('force race',v.id,v.v,v.v2,v.v3)end;startRaceOverride=nil
  end
  manager().pauseAutoSaveTimer=true
 end
 function A.capture()getInputHandler():sendEvent('screenshot')end
 function A.pause(w,on)manager().pauseAutoSaveTimer=true;w:userPause(on)end
 function A.autosave(on)getOptionsHolder().autosave=on end
 function A.overlays(close)
  local found={};local e=MyGUI.Gui.getInstance():getEnumerator()
  while e:next() do
   local widget=e:current()
   if widget:getVisible() and widget:getCaption()=='RE_Kenshi Menu' then
    found[widget:getName()]='RE_Kenshi Menu'
    if close then widget:setVisible(false) end
   end
  end
  return found
 end
 function A.camera(w,c,req)
  local camera=assert(w.player.camera,'Camera unavailable')
  local zoom=tonumber(req.zoom or 55);assert(zoom and zoom>=25 and zoom<=150,'Invalid camera distance')
  w.player:_selectPlayerCharacter(c,false,true)
  camera:setFreeCameraMode(false);camera:reset()
  local focus=c;local offset={x=0,y=0,z=0}
  if req.target=='opponent' then
   assert(#w.player.playerCharacters==1 and c:getName()==config.test_character_name and not getOptionsHolder().autosave,'Fixture camera requires isolated test')
   focus=assert(fixtureCharacter(),'No owned opponent fixture')
  elseif req.target=='midpoint' then
   assert(#w.player.playerCharacters==1 and c:getName()==config.test_character_name and not getOptionsHolder().autosave,'Fixture camera requires isolated test')
   local other=assert(fixtureCharacter(),'No owned opponent fixture');local a,b=c:getPosition(),other:getPosition()
   assert((a.x-b.x)^2+(a.z-b.z)^2<300^2,'Fixture camera distance exceeded')
   offset={x=(b.x-a.x)/2,y=(b.y-a.y)/2,z=(b.z-a.z)/2}
  else assert(req.target==nil or req.target=='' or req.target=='actor','Unknown camera target')end
  camera:focusCameraOnObject(focus,offset,true)
  camera:setZoomDist(zoom)
  local yaw,pitch=tonumber(req.yaw or 0),tonumber(req.pitch or 0)
  assert(yaw and pitch and yaw==yaw and pitch==pitch and math.abs(yaw)<=3.15 and math.abs(pitch)<=1.5,'Invalid bounded camera orbit')
  -- Native pitch/yaw fields are mouse deltas, consumed by rotationUpdate.
  -- Local 1-count sample changed the view by about 0.002 radians.
  -- Orbit requests are absolute: repeated inspection must not accumulate a
  -- low-angle tilt. Measure the actual camera vector before each correction.
  local desiredAz=math.pi+yaw;local desiredEl=math.max(.12,math.min(1.35,math.pi/6+pitch))
  -- Camera position is published on a later frame. Never iterate against the
  -- same stale vector here; separate RPCs can converge across GUI frames.
  for _=1,1 do
   local pos,center=camera:getCameraPos(),camera:getCenter()
   local dx,dy,dz=pos.x-center.x,pos.y-center.y,pos.z-center.z
   local az=math.atan2(dx,dz);local el=math.atan2(dy,math.sqrt(dx*dx+dz*dz))
   local da=(desiredAz-az+math.pi)%(2*math.pi)-math.pi;local de=desiredEl-el
   if math.abs(da)<.015 and math.abs(de)<.015 then break end
   camera.yaw=-math.max(-1,math.min(1,da))*500
   camera.pitch=-math.max(-.5,math.min(.5,de))*500;camera:rotationUpdate()
  end
  return {zoom=zoom,yaw=camera.yaw,pitch=camera.pitch,center=camera:getCenter(),position=camera:getCameraPos()}
 end
 function A.nearby(w,c)
  local result={};local p=c:getPosition()
  if lektor and lektor.new then
   local objects=lektor.new('RootObject*')
   w:getCharactersWithinSphere(objects,p,250,250,250,128,128,c)
   for i=1,#objects do
    local h=objects[i]:getHandle()
    observedNPC[h:toString()]={handle=h,expires=os.time()+60}
   end
  end
  for other in pairs(w:getCharacterUpdateList()) do
   if not other:isPlayerCharacter() then
    -- HandBinding::push owns a copied handle, not a character pointer.
    local h=other:getHandle();observedNPC[h:toString()]={handle=h,expires=os.time()+60}
   end
  end
  for id,entry in pairs(observedNPC) do
   local other=entry.expires>=os.time() and entry.handle:getCharacter()
   if other and not other:isPlayerCharacter() then
    local q=other:getPosition();local d=(p.x-q.x)^2+(p.z-q.z)^2
    if d<=250^2 then
     result[id]={name=other:getName(),distance=math.sqrt(d),position=q,
      enemy=c:isEnemy(other,true),dead=other:isDead(),unconscious=other:isUnconcious()}
     local ok,medical=pcall(function()
      local med=other:getMedical();local parts={}
      for data,part in pairs(med.status)do parts[data.stringID]={name=data.name,flesh=part.flesh,stun=part.fleshStun,max=part:maxHealth()}end
      return {blood=med.blood,parts=parts}
     end)
     if ok then result[id].medical=medical else result[id].medical_error=tostring(medical)end
    else observedNPC[id]=nil end
   else observedNPC[id]=nil end
  end
  return result
 end
 function A.spar(w,c,req)
  assert(#w.player.playerCharacters==1,'Sparring is restricted to the isolated test')
  assert(not combatLease,'Finish the current sparring lease first')
  local entry=observedNPC[req.target]
  local target=entry and entry.expires>=os.time() and entry.handle:getCharacter()
  assert(target and not target:isPlayerCharacter() and target:isHuman(),'Expected a loaded human NPC')
  assert(not target:isDead() and not target:isUnconcious(),'Target cannot fight')
  local p,q=c:getPosition(),target:getPosition()
  assert((p.x-q.x)^2+(p.z-q.z)^2<=250^2,'Target is too far away')
  local order=MessageForB.StandingOrder.M_SET_ORDER_DEFENSIVE_COMBAT
  local mode=tonumber(req.mode or 0);assert(mode==0 or mode==1 or mode==2 or mode==3,'Invalid sparring mode')
  if mode==3 then assert(target==fixtureCharacter(),'Stationary aim requires the owned disposable fixture')end
  local rangedOrder=MessageForB.StandingOrder.M_SET_ORDER_RANGED
  local maximum=opponentLease and opponentLease.magazine and target==fixtureCharacter()and 240 or 30
  if meleeCapture and meleeCapture.active then maximum=90 end
  combatLease={actor=c:getHandle(),target=target:getHandle(),original=c:getStandingOrder(order),expires=os.time()+maximum}
  if mode==2 or mode==3 then combatLease.ranged=c:getStandingOrder(rangedOrder)end
  c:setStandingOrder(order,mode==0)
  if mode==2 or mode==3 then c:setStandingOrder(rangedOrder,true)end
  if mode==3 then
   local hold=MessageForB.StandingOrder.M_SET_ORDER_HOLD
   combatLease.targetHold=target:getStandingOrder(hold);target:setStandingOrder(hold,true)
  end
  c:attackTarget(target);target:attackTarget(c)
  c:addGoal((mode==2 or mode==3)and TaskType.RANGED_ATTACK or TaskType.MELEE_ATTACK,target);target:addGoal(TaskType.MELEE_ATTACK,c)
  return {target=req.target,name=target:getName(),maximum_seconds=maximum}
 end
 function A.end_spar()
  if not combatLease then return end
  local l=combatLease;combatLease=nil
  local actor,target=l.actor:getCharacter(),l.target:getCharacter()
  if actor and actor:isPlayerCharacter() and actor:getName()==config.test_character_name then
   actor:setStandingOrder(MessageForB.StandingOrder.M_SET_ORDER_DEFENSIVE_COMBAT,l.original)
   if l.ranged~=nil then actor:setStandingOrder(MessageForB.StandingOrder.M_SET_ORDER_RANGED,l.ranged)end
   actor:clearAllAIGoals();actor.movement:halt();actor:endCombatMode()
  end
  if target and not target:isPlayerCharacter() then
   if l.targetHold~=nil then target:setStandingOrder(MessageForB.StandingOrder.M_SET_ORDER_HOLD,l.targetHold)end
   target:clearAllAIGoals();target:endCombatMode()
  end
 end
 function A.frame(dt)
  if loadSignalTrace then loadSignalTrace.tick(dt)end
  if clockLease and not clockLease.done then
   local w=getGameWorld();local l=clockLease
   if not w or fixtureWorld(w)~=l.world then l.done=true;l.error='world changed'
   else
    local c;for i=1,#w.player.playerCharacters do local x=w.player.playerCharacters[i];if x:getHandle():toString()==l.owner then c=x end end
    if c and _G.JACK_T60_LAMP_PROBE then local ok,p=pcall(_G.JACK_T60_LAMP_PROBE,c);if ok and p and p.night==l.targetNight and not l.daySeen then l.daySeen=os.time() end end
    if (l.daySeen and os.time()-l.daySeen>=3) or os.time()>=l.expires then
     w:setGameSpeed(1,false);A.pause(w,true);l.done=true;l.timed_out=not l.daySeen
     if c then local ok,p=pcall(_G.JACK_T60_LAMP_PROBE,c);if ok then l.probe=p end end
    end
   end
  end
  if regionProbe then
   local w=getGameWorld();local rp=regionProbe
   if not w or w.gameResetting or tostring(ffi.cast('void**',w)[0])~=rp.world then regionProbe=nil
   else
    if os.time()>rp.expires and not rp.returned then w.player.camera:teleport(rp.home);rp.returned=true;rp.expired=true end
    if not rp.last or os.time()>rp.last then
     rp.last=os.time();local row={time=rp.last,center=w.player.camera:getCenter(),present=false}
     for i=1,#w.player.playerCharacters do local c=w.player.playerCharacters[i];if c:getHandle():toString()==rp.owner then
      local a=c:getAppearance();row.present=true;row.character=tostring(ffi.cast('void**',c)[0]);row.appearance=a and tostring(ffi.cast('void**',a)[0])or nil
      if a and not a.isCreatingBody and not a.updateBody and a:getBody()then row.body=tostring(ffi.cast('void*',a:getBody()));row.bones=A.bones(a)end
      local pl=c:getPlatoon();row.platoon_loaded=pl and pl:isLoaded()or false
     end end
     rp.samples[#rp.samples+1]=row;if #rp.samples>90 then table.remove(rp.samples,1)end
    end
   end
  end
  if _G.JACK_CRAFT_TEST_STATE and _G.JACK_CRAFT_TEST_STATE.work then dofile(config.root..'/craft_test_controller.lua').new(config).frame()end
  if _G.JACK_CRAFT_TEST_STATE and _G.JACK_CRAFT_TEST_STATE.haul and _G.JACK_CRAFT_TEST_STATE.haul.active then
   dofile(config.root..'/haul_fixture.lua').new(config).frame()
  end
  serviceTests.frame()
  if meleeCapture and meleeCapture.active then
   local mc=meleeCapture;local w=getGameWorld()
   if os.time()>mc.expires then mc.active=false;mc.error='Requested attack phase was not observed'
   elseif w and not w.gameResetting and not w.paused and w.player and #w.player.playerCharacters==1 then
    local c=w.player.playerCharacters[1];local a=c:getAppearance()
    if c:getHandle():toString()==mc.owner and a and not a.isCreatingBody and not a.updateBody then
     local playing=A.motion(a)
     for name,weight,time in playing:gmatch('([^;]+)%[w=([%d%.]+),t=([%d%.]+)%]')do
      name=name:gsub('^%s+','');local base=name:gsub('%-%d+$','')
      if(base==mc.clip or name==mc.clip)and tonumber(weight)>=.65 and tonumber(time)>=mc.seconds and tonumber(time)<=mc.seconds+.10 then
       mc.motion=playing;mc.actual_clip=name;mc.actual_time=tonumber(time);mc.weight=tonumber(weight);mc.captured=true;mc.active=false;mc.weapon=c:getCurrentWeapon()and c:getCurrentWeapon().data.stringID or'';mc.position=c:getPosition();w:userPause(true);break
      end
     end
    end
   end
  end
  if opponentLease and os.time()>opponentLease.expires then
   local w=getGameWorld()
   if fixtureWorld(w)==opponentLease.world then w:userPause(true);A.end_spar()end
   removeOpponent()
  end
  local currentWorld=getGameWorld()
  if not currentWorld or currentWorld.gameResetting then combatLease=nil;observedNPC={};weaponTests.reset();poseCapture=nil end
  if poseCapture and poseCapture.active then
   local pc=poseCapture;local all=currentWorld and currentWorld.player and currentWorld.player.playerCharacters
   if not all or #all~=1 or all[1]:getHandle():toString()~=pc.owner or os.time()>pc.expires then pc.active=false;pc.error='Pose capture expired or owner changed'
   elseif not currentWorld.paused then
    local c=all[1];local a=c:getAppearance()
    if a and not a.isCreatingBody and not a.updateBody then
     local item=c:getCurrentWeapon();local human=c:isHuman();local playing=A.motion(a)
     local ready=pc.kind=='secondary'or playing:match('aimshoot%[w=1%.000')or playing:match('aimshoot%[w=0%.9[5-9]')
     if ready and human and human.weaponInHands~=nil and item and item.data.stringID==pc.weapon then
      pc.motion=playing;pc.body_bones=A.bones(a);pc.captured=true;pc.active=false;pc.paused_in_frame=true
      currentWorld:userPause(true);getInputHandler():sendEvent('screenshot')
     end
    end
   end
  end
  if trace and trace.active then
   local tr=trace;tr.elapsed=tr.elapsed+math.max(0,tonumber(dt) or 0)
   local success,problem=pcall(function()
    local w=assert(getGameWorld());assert(not w.gameResetting and w.player,'World unloading')
    local all=w.player.playerCharacters
    assert(#all==1 and all[1]:getHandle():toString()==tr.owner,'Trace owner changed')
    local c=all[1];local a=assert(c:getAppearance())
    assert(not a.isCreatingBody and not a.updateBody,'Body rebuilding during trace')
    local n=tr.native.T60_bone_pose(ffi.cast('void*',a:getBody()),tr.buffer,65536)
    assert(n==82 or n==30,'Native bone read failed')
    tr.rows[#tr.rows+1]={t=tr.elapsed,motion=A.motion(a),bones=ffi.string(tr.buffer),speed=c:getMovementSpeed()}
   end)
   if not success then tr.active=false;tr.error=tostring(problem) end
   if tr.elapsed>=6 or #tr.rows>=300 then tr.active=false end
  end
  if combatLease and os.time()>combatLease.expires then
   getGameWorld():userPause(true);A.end_spar()
  end
 end
 return A
end
return M
