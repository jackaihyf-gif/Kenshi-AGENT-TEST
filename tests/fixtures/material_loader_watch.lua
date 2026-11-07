-- Execute the real loader with synthetic FFI libraries; no DLLs or game loaded.
local oldActive=false
local priorActive=false
local loaded={}
local function native(marker,night)
 return {
  T60_material_error=function()return 'mock-error' end,
  T60_material_bind=function()return marker end,
  T60_material_night_state=function()return night end,
  T60_material_night=function()return 0 end,
  T60_material_enable=function()return 0 end,
  T60_material_register=function()return 0 end,
  T60_material_apply=function()return marker end,
  T60_material_restore=function()return 0 end,
  T60_material_binding_status=function(out)
   assert(marker==22 or marker==33,'old DLL must not receive new ABI calls')
   out.value='{"checks":3,"repairs":1,"slots":2,"limit":32,"enabled":1}'
   return #out.value
  end,
 }
end
local old,prior,new=native(11,1),native(22,0),native(33,0)
package.preload.ffi=function()
 return {
  cdef=function()end,
  new=function()return {}end,
  cast=function(_,value)return value end,
  string=function(value)return type(value)=='table' and value.value or value end,
  load=function(path)
   loaded[#loaded+1]=path
   if path=='kernel32' then
    return {GetModuleHandleA=function(name)
     if name=='T60MaterialBridge_v091.dll' then return oldActive and 'old' or nil end
     assert(name=='T60MaterialBridge_v091_bindingfix_20261106.dll')
     return priorActive and 'prior' or nil
    end}
   elseif path:find('isolatednormal_20261107',1,true)then return new
   elseif path:find('bindingfix_20261106',1,true)then return prior
   elseif path:find('T60MaterialBridge_v091.dll',1,true)then return old
   else error('unexpected library: '..path)end
  end,
 }
end
package.preload.t60_lighting_clock=function()return {isNight=function()return false end}end
getGameWorld=function()return {}end
oldActive=true
for _=1,3 do
 local api=assert(loadfile(LOADER_PATH))()
 assert(api.bind()==11 and api.apply({},'mock-owner',false,1,'jack_t60_wear_v08.mesh')==11)
 assert(JACK_T60_EYE_NIGHT_STATE()==true)
 assert(JACK_T60_MATERIAL_BINDING_STATUS():find('"restart_required":true',1,true))
end
for _,path in ipairs(loaded)do assert(not path:find('bindingfix_20261106',1,true))end
oldActive=false;priorActive=true;loaded={}
for _=1,3 do
 local api=assert(loadfile(LOADER_PATH))()
 assert(api.bind()==22 and JACK_T60_EYE_NIGHT_STATE()==false)
 assert(JACK_T60_MATERIAL_BINDING_STATUS():find('"repairs":1',1,true))
end
for _,path in ipairs(loaded)do assert(not path:find('isolatednormal_20261107',1,true))end
priorActive=false;loaded={}
local api=assert(loadfile(LOADER_PATH))()
assert(api.bind()==33 and api.apply({},'mock-owner',false,1,'jack_t60_wear_v08.mesh')==33)
assert(JACK_T60_EYE_NIGHT_STATE()==false)
assert(JACK_T60_MATERIAL_BINDING_STATUS():find('"repairs":1',1,true))
assert(loaded[2]:find('isolatednormal_20261107',1,true))
