-- GUI-only lifecycle observation. The native hook counts PlayerInterface resets;
-- it never calls Lua and performs no character or resource operations.
local ffi=require('ffi')
ffi.cdef[[
void* GetModuleHandleA(const char*);void* LoadLibraryA(const char*);
void* GetProcAddress(void*,const char*);unsigned long GetCurrentThreadId(void);
]]
local kernel=ffi.load('kernel32')
local module=kernel.GetModuleHandleA('player_epoch_probe.dll')
if module==nil then
 local source=debug.getinfo(1,'S').source:gsub('^@',''):gsub('\\','/')
 local root=source:match('^(.*)/scripts/[^/]+%.lua$')
 assert(root,'Cannot locate T60 lifecycle adapter')
 if not root:match('^%a:/')and not root:match('^/')and not root:match('^%./mods/')and not root:match('^mods/')then root='./mods/'..root end
 module=kernel.LoadLibraryA(root..'/plugin/player_epoch_probe.dll')
end
assert(module~=nil,'T60 lifecycle native module unavailable')
local function resolve(name,signature)
 local p=kernel.GetProcAddress(module,name);assert(p~=nil,'T60 lifecycle export unavailable: '..name)
 return ffi.cast(signature,p)
end
local ready=resolve('T60_player_epoch_probe_ready','int (*)(void)')
local snapshot=resolve('T60_player_epoch_probe_snapshot','int (*)(unsigned long long*,long*,unsigned long*)')
local receiver=resolve('T60_player_epoch_probe_receiver','void* (*)(void)')
assert(ready()==1,'T60 lifecycle exact-build/thread gate unavailable')
local gui=tonumber(kernel.GetCurrentThreadId())
local generation=ffi.new('unsigned long long[1]');local busy=ffi.new('long[1]');local thread=ffi.new('unsigned long[1]')
local priorGeneration,lastPlayer
local M={}
function M.read()
 if tonumber(kernel.GetCurrentThreadId())~=gui then return {guiThread=false}end
 assert(snapshot(generation,busy,thread)==0,'T60 lifecycle observation unavailable')
 local first,active,last=tonumber(generation[0]),tonumber(busy[0]),tonumber(thread[0])
 local owner=receiver()
 assert(snapshot(generation,busy,thread)==0,'T60 lifecycle observation unavailable')
 local value,now,caller=tonumber(generation[0]),tonumber(busy[0]),tonumber(thread[0])
 if caller~=0 and caller~=gui then return {guiThread=false}end
 local stable=first==value and active==0 and now==0 and last==caller
 local loading=false
 if stable then
  if priorGeneration~=nil and value~=priorGeneration then assert(lastPlayer~=nil and owner==lastPlayer,'Reset receiver is not the previously observed player')end
  local w=getGameWorld();local player=w and w.player
  -- This native query dereferences saved-world state absent at the main menu.
  -- Empty player lists also occur during reload; retain the old owner/generation
  -- and keep every consumer deferred until characters are present again.
  loading=not player or #player.playerCharacters==0 or w.gameResetting or w:isLoadingFromASaveGame()
  if not loading and w and w.player then
   lastPlayer=ffi.cast('void**',w.player)[0];priorGeneration=value
  end
 end
 return {generation=value,busy=active~=0 or now~=0,stable=stable,loading=not not loading,guiThread=true,thread=caller,guiThreadId=gui,receiver=owner~=nil and tostring(owner)or nil}
end
_G.JACK_T60_WORLD_EPOCH_STATUS=M.read
return M
