-- KenshiLua caches mod-local require separately in each script sandbox.
-- All init scripts must share this one registry and GUI dispatcher.
local shared=rawget(_G,'JACK_T60_CHARACTER_IDENTITY')
if shared then return shared end
local ffi=require('ffi')
local frames,epochs={},{}
-- Required production adapter contract: read() returns coherent generation/busy/stable/loading/guiThread.
-- The candidate intentionally has no default implementation; absent adapter fails closed.
local lifecycle=require('t60_world_epoch_adapter')
local function pointer(x)
 if x==nil then return nil end
 local p=ffi.cast('void**',x)[0]
 return p~=nil and p or nil
end
local registry=require('character_identity_core').new({
 world=getGameWorld,
 epochState=function()return lifecycle.read()end,
 pointer=pointer,
 worldKey=function(w)
  if not w then return 'nil' end
  return tostring(pointer(w))..'/'..tostring(pointer(w.player))..'/'..tostring(pointer(w.savedata))
 end,
 pause=function(w)w:userPause(true)end,
 log=function(s)print('[JACK T60 Identity] '..s)end,
 onEpoch=function(epoch)for _,row in ipairs(epochs)do row.fn(epoch)end end,
})
-- Loaded before all dependent frame handlers. No worker-event subscriptions.
function registry.onFrame(name,fn)frames[#frames+1]={name=name,fn=fn}end
function registry.onEpoch(name,fn)epochs[#epochs+1]={name=name,fn=fn}end
Events.on('MyGUI::Gui::eventFrameStart',function(dt)
 if not registry.refresh()then return end
 for _,row in ipairs(frames)do
  local ok,err=pcall(row.fn,dt)
  if not ok then registry.stop(row.name..': '..tostring(err));return end
 end
end)
_G.JACK_T60_IDENTITY_STATUS=registry.status
-- The bridge has its own package table; expose a read-only query, never a
-- second require/dispatcher in the test environment.
_G.JACK_T60_IDENTITY_OWNER=function(c)
 return registry.eligible(c)and registry.peek(c)or nil
end
_G.JACK_T60_CHARACTER_IDENTITY=registry
return registry
