-- Runs on Kenshi's GUI frame; never evaluates commands as Lua code.
local M={}
local function finite(n)return type(n)=='number' and n==n and math.abs(n)<math.huge end
local function quote(s)
 return '"'..tostring(s):gsub('[%z\1-\31\\"]',function(c)
  if c=='"' then return '\\"' elseif c=='\\' then return '\\\\' end
  return string.format('\\u%04x',string.byte(c))
 end)..'"'
end
local function json(v)
 if type(v)=='string' then return quote(v)
 elseif type(v)=='number' then assert(finite(v),'Non-finite observation');return tostring(v)
 elseif type(v)=='boolean' then return tostring(v)
 elseif type(v)=='table' then
  local parts={};for k,value in pairs(v) do parts[#parts+1]=quote(k)..':'..json(value) end
  return '{'..table.concat(parts,',')..'}'
 end
 return 'null'
end
function M.new(config,api)
 local root,token=config.root,config.token
 local session=token:sub(1,8)..'-'..tostring(os.time())..'-'..tostring({}):gsub('[^a-zA-Z0-9]','')
 local leases,seen,history={},{},{};local age,now=0,0
 local world=api and api.world or getGameWorld
 local creation_requested=false
 local function write(name,value)
  local f=assert(io.open(root..'/'..name,'wb'));f:write(json(value));f:close()
 end
 local function characters()
  local w=world();local list={}
  if not w or w.gameResetting or not w.player then return w,list end
  for i=1,#w.player.playerCharacters do
   local c=w.player.playerCharacters[i]
   if c and c:isPlayerCharacter() then list[c:getHandle():toString()]=c end
  end
  return w,list
 end
 local function observe(w,list)
  local result={paused=w and w.paused or false,characters={},session=session}
  if api and api.describe then result.game=api.describe() end
  for id,c in pairs(list) do
   local a=c:getAppearance();local upper=c:getUpperBodyArmour();local p=c:getPosition()
   local row={owner=id,name=c:getName(),position=p,speed=c:getMovementSpeed(),
    gait_order=c:getMovementSpeedOrders(),upper=upper and upper.data and upper.data.stringID or '',
    visual=a and a.raceData and a.raceData.stringID or '',
    loading=not a or a.isCreatingBody or a.updateBody,
    controllable=c:getName()==config.test_character_name}
   if not row.loading and api and api.motion then row.motion=api.motion(a) end
   if not row.loading and api and api.bones then row.bones=api.bones(a) end
   if api and api.detail then row.detail=api.detail(c) end
   result.characters[id]=row
  end
  result.phase=next(list) and 'ready' or 'waiting_for_test_save'
  return result
 end
 local function release(id,list)
  local lease=leases[id];if not lease then return end
  local c=list[id]
  if c and c.movement then
   -- Never overwrite a speed order the user changed after our write.
   local current=api and api.get_gait and api.get_gait(c) or c.movement.speedOrders
   if current==lease.written then
    if api and api.set_gait then api.set_gait(c,lease.original) else c.movement.speedOrders=lease.original end
   end
   if lease.moved then
    if api and api.halt then api.halt(c) else c.movement:halt() end
   end
  end
  leases[id]=nil
 end
 local function control(req,list)
  local c=assert(list[req.owner],'Owner is not a currently loaded player character')
  assert(c:getName()==config.test_character_name,'Control is restricted to the configured test character')
  local a=c:getAppearance();assert(a and not a.isCreatingBody and not a.updateBody,'Body rebuild in progress')
  local command=req.command
  if command=='camera' then assert(api and api.camera,'Camera API unavailable');return api.camera(world(),c,req) end
  if command=='nearby' then assert(api and api.nearby,'Nearby API unavailable');return api.nearby(world(),c) end
  if command=='sources' then assert(api and api.sources,'Sources API unavailable');return api.sources(c) end
  if command=='weapon' then assert(api and api.weapon,'Weapon test API unavailable');return api.weapon(c,req.target) end
  if command=='opponent' then assert(api and api.opponent,'Opponent fixture unavailable');return api.opponent(c,req.target) end
  if command=='pose_capture'then assert(api and api.pose_capture,'Pose capture unavailable');return api.pose_capture(c,req.target)end
  if command=='energy' then assert(api and api.energy,'Energy diagnostic unavailable');return api.energy(c,req.target) end
  if command=='service' then assert(api and api.service,'Service test API unavailable');return api.service(c,req.target) end
  if command=='craft' then assert(api and api.craft,'Craft test API unavailable');return api.craft(c,req.target) end
  if command=='power' then assert(api and api.power,'Power test API unavailable');return api.power(c,req.target) end
  if command=='melee_capture'then assert(api and api.melee_capture,'Melee capture API unavailable');return api.melee_capture(c,req.target)end
  if command=='visibility' then assert(api and api.visibility,'Visibility test unavailable');return api.visibility(c,req.enabled) end
  if command=='mounts' then
   assert(req.enabled=='0' or req.enabled=='1','Invalid attachment flag')
   assert(api and api.mounts,'Attachment API unavailable');return api.mounts(c,req.enabled=='1')
  end
  if command=='motion_trace' then
   assert(req.enabled=='0' or req.enabled=='1','Invalid trace flag')
   assert(api and api.motion_trace,'Motion trace API unavailable');return api.motion_trace(c,req.enabled=='1')
  end
  if command=='spar' then assert(api and api.spar,'Sparring API unavailable');return api.spar(world(),c,req) end
  if command=='end_spar' then assert(api and api.end_spar,'Sparring API unavailable');return api.end_spar() end
  if command=='wear' then
   assert(api and api.wear,'Wear API unavailable')
   assert(req.enabled=='0' or req.enabled=='1','Invalid wear flag');return api.wear(c,req.enabled=='1')
  end
  if command=='release' then release(req.owner,list);return end
  if command=='halt' then
   assert(c.movement,'No movement controller')
   if api and api.halt then api.halt(c) else c.movement:halt() end;return
  end
  if command=='sheathe' then
   assert(not c:isInCombatMode(true,true),'Cannot sheathe during combat')
   local h=assert(c:isHuman(),'No human weapon controller');h:sheatheWeapon();return
  end
  assert(command=='gait' or command=='move','Unsupported action')
  local mode,duration=tonumber(req.mode),tonumber(req.duration)
  assert(mode==0 or mode==1 or mode==2,'Invalid gait')
  assert(finite(duration) and duration>=1 and duration<=30,'Invalid lease duration')
  local dx,dz=tonumber(req.dx),tonumber(req.dz)
  if command=='move' then assert(finite(dx) and finite(dz) and dx*dx+dz*dz<=4096,'Invalid movement offset') end
  assert(c.movement,'No movement controller')
  local lease=leases[req.owner]
  if not lease then
   lease={original=api and api.get_gait and api.get_gait(c) or c.movement.speedOrders};leases[req.owner]=lease
  end
  lease.expires=now+duration;lease.written=mode
  if api and api.set_gait then api.set_gait(c,mode) else c.movement.speedOrders=mode end
  if command=='move' then
   local p=c:getPosition();local destination={x=p.x+dx,y=p.y,z=p.z+dz}
   if api and api.move then api.move(c,destination) else c:setDestination(destination,false) end
   lease.moved=true
  end
 end
 local C={}
 function C.tick(dt)
  if api and api.frame then local ok,e=pcall(api.frame,dt);if not ok then print('[Agent lease] '..tostring(e)) end end
  local d=math.max(0,tonumber(dt) or 0);age=age+d;now=now+d
  if age<.2 then return end;age=0
  local ok,err=pcall(function()
   local w,list=characters()
   for id,lease in pairs(leases) do if now>=lease.expires then release(id,list) end end
   write('heartbeat.json',{protocol=1,session=session,time=os.time(),simulated=api and api.simulated==true or false})
   local f=io.open(root..'/request.ini','rb');if not f then return end
   local raw=f:read(4097);f:close();assert(#raw<=4096,'Oversized request')
   local req={};for line in raw:gmatch('[^\r\n]+') do
    local k,v=line:match('^([a-z_]+)=(.*)$');assert(k and not req[k],'Malformed request');req[k]=v
   end
   if req.token~=token or req.protocol~='1' or not req.id or not req.id:match('^[a-f0-9]+$') or #req.id~=32 then return end
   if seen[req.id] then return end;seen[req.id]=true
   history[#history+1]=req.id
   if #history>256 then seen[table.remove(history,1)]=nil end
   local expires=tonumber(req.expires)
   local result={protocol=1,id=req.id,session=session,simulated=api and api.simulated==true or false}
   local success,errorText=pcall(function()
    assert(expires and expires>=os.time() and expires<=os.time()+35,'Expired request')
    if req.command~='status' then
     assert(req.session==session,'Request belongs to a previous game session')
     assert(w and not w.gameResetting,'Game world not ready')
     if req.command=='new_test' then
      assert(not creation_requested,'Test creation already requested')
      assert(api and api.new_test,'Test-creation API unavailable')
      assert(not next(list),'Cannot replace a loaded session')
      creation_requested=true;api.new_test(w,list,req)
      result.state={phase='test_creation_requested',session=session,characters={}};return
     elseif req.command=='replace_test' then
      assert(api and api.replace_test,'Isolated replacement API unavailable');api.replace_test(w,list,req)
      result.state={phase='test_creation_requested',session=session,characters={}};return
     elseif req.command=='lifecycle'then
      assert(api and api.lifecycle,'Lifecycle test API unavailable');result.action=api.lifecycle(w,list,req)
      if req.target and req.target:match('^load:')then result.state={phase='test_load_requested',session=session,characters={}};return end
     elseif req.command=='stage2_region' then
      assert(api and api.stage2_region,'Region probe unavailable');result.action=api.stage2_region(w,list,req.target)
     elseif req.command=='stage2_team' then
      assert(api and api.stage2_team,'Team fixture unavailable');result.action=api.stage2_team(w,list,req.target,req.owner)
     elseif req.command=='profile_editor' then
      assert(api and api.profile_editor,'Editor profile API unavailable');result.action=api.profile_editor(w,list,req)
     elseif req.command=='finish_editor' then
      assert(api and api.finish_editor,'Editor API unavailable');api.finish_editor(w,list)
     elseif req.command=='capture' then
      assert(api and api.capture,'Screenshot API unavailable');api.capture()
     elseif req.command=='overlays' or req.command=='close_overlay' then
      assert(api and api.overlays,'Overlay API unavailable')
      result.overlays=api.overlays(req.command=='close_overlay')
     elseif req.command=='pause' or req.command=='resume' or req.command=='autosave' then
      assert(api and api.pause,'Pause API unavailable')
      local count=0;for _,c in pairs(list) do
       assert(c:getName()==config.test_character_name,'Pause is restricted to the isolated test')
       count=count+1
      end
      assert(count==1,'Expected exactly one test character')
      if req.command=='autosave' then
       assert(req.enabled=='0' or req.enabled=='1','Invalid autosave flag');api.autosave(req.enabled=='1')
      else api.pause(w,req.command=='pause') end
     else result.action=control(req,list) end
    end
    result.state=observe(w,list)
   end)
   result.ok=success;result.error=not success and tostring(errorText) or nil
   write('response.json',result)
  end)
  if not ok then print('[Kenshi Agent Bridge] '..tostring(err)) end
 end
 return C
end
return M
