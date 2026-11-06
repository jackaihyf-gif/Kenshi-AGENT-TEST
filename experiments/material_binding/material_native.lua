local ffi=require('ffi')
ffi.cdef[[
int T60_material_bind(void);
int T60_material_night(int value);
int T60_material_night_state(void);
const char* T60_material_error(void);
int T60_material_enable(int enabled);
int T60_material_register(const char* absolute_path);
int T60_material_apply(void* entity,const char* owner,int female,unsigned long long generation,const char* filename);
int T60_material_restore(void* current_live_entity);
int T60_material_binding_status(char* output,size_t capacity);
]]
local clock=require('t60_lighting_clock')
local lib=ffi.load('D:/steam/steamapps/common/Kenshi/mods/JACK_T60_WearLab/plugin/T60MaterialBridge_v091_bindingfix_20261106.dll')
local bindingOutput=ffi.new('char[512]')
_G.JACK_T60_MATERIAL_BINDING_STATUS=function()
 local n=lib.T60_material_binding_status(bindingOutput,512)
 assert(n>=0 and n<512,'Material status buffer bound')
 return ffi.string(bindingOutput)
end
_G.JACK_T60_EYE_NIGHT_STATE=function()return lib.T60_material_night_state()==1 end
return {
 error=function()return ffi.string(lib.T60_material_error()) end,
 bind=function()return tonumber(lib.T60_material_bind()) end,
 register=function(path)return tonumber(lib.T60_material_register(path)) end,
 enable=function(value)return tonumber(lib.T60_material_enable(value and 1 or 0)) end,
 apply=function(entity,owner,female,generation,filename)
  assert(lib.T60_material_night(clock.isNight(getGameWorld()) and 1 or 0)>=0,ffi.string(lib.T60_material_error()))
  return tonumber(lib.T60_material_apply(ffi.cast('void*',entity),owner,female and 1 or 0,generation,filename))
 end,
 restore=function(entity)return tonumber(lib.T60_material_restore(ffi.cast('void*',entity))) end,
 valid=function(entity)return entity and ffi.cast('void*',entity)~=nil end,
 key=function(entity)return tostring(ffi.cast('void*',entity)) end,
}
