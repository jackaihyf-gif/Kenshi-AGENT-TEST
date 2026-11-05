local identity=require('character_identity')
-- Automatic render-only suppression. Inventory objects and stats stay with Kenshi.
local ffi=require('ffi')
ffi.cdef[[int T60_visibility_begin(void*,const char*);int T60_visibility_tick(void*,const char*,char*,size_t);int T60_visibility_end(void*,const char*);int T60_visibility_forget(void);int T60_visibility_dirty(void*,const char*);]]
local native=ffi.load('D:/steam/steamapps/common/Kenshi/mods/JACK_T60_WearLab/plugin/T60EquipmentVisibility_indexed.dll')
local M={};local worldTag;local active={};local pending={};local output=ffi.new('char[1024]')
local debug={scans=0,resets=0,seen=0,ticks=0,last=-999,skipped=0}
function M.diagnostic()return debug end
identity.onEpoch('visibility reset',function()assert(native.T60_visibility_forget()==0);worldTag=nil;active={};pending={}end)
local function raw(a)return ffi.cast('void**',a)[0]end
local function id(c)return identity.owner(c)end
local function sync()
 local w=getGameWorld()
 local tag=(w and tostring(raw(w)) or 'nil')..'/'..identity.epoch()
 if tag~=worldTag then assert(native.T60_visibility_forget()==0);worldTag=tag;active={};pending={};debug.resets=debug.resets+1 end
 return w
end
function M.begin(c,a)
 sync();local owner=id(c);assert(native.T60_visibility_begin(raw(a),owner)==0,'Equipment visibility capture failed');active[owner]=true
end
function M.finish(c,a)
 sync();local owner=id(c);local n=native.T60_visibility_end(raw(a),owner)
 assert(n>=0,'Equipment visibility restoration failed '..tostring(n));active[owner]=nil;pending[owner]=nil
end
function M.dirty(c)
 -- Equip callbacks can arrive from an AI worker. Do not call the GUI-thread
 -- native API or retain appearance pointers here; coalesce owner IDs instead.
 if not c then return end;local owner=id(c)
 if active[owner]then pending[owner]=true end
end
function M.scan()
 debug.scans=debug.scans+1
 local w=sync();if not w or w.gameResetting or not w.player then return end
 for i=1,#w.player.playerCharacters do
  local c=w.player.playerCharacters[i];local a=c:getAppearance()
  debug.seen=debug.seen+1
  debug.human=not not c:isHuman();debug.ready=a and not a.isCreatingBody and not a.updateBody or false;debug.race=a and a.raceData and a.raceData.stringID or 'nil'
  if identity.eligible(c) and c:isHuman() and a and not a.isCreatingBody and not a.updateBody then
   local owner=id(c)
   if a.raceData and a.raceData.stringID=='670-JACK_T60_WearLab.mod' then
    if not active[owner] then M.begin(c,a)end
    if pending[owner]then assert(native.T60_visibility_dirty(raw(a),owner)==0,'Equipment visibility refresh failed');pending[owner]=nil end
    local n=native.T60_visibility_tick(raw(a),owner,output,1024)
    debug.ticks=debug.ticks+1;debug.last=tonumber(n)
    assert(n>=0 or n==-12,'Equipment visibility update failed '..tostring(n))
   elseif active[owner] then M.finish(c,a)end
  end
 end
 if debug.ticks>0 and not debug.reported then debug.reported=true;print('[JACK T60 Visibility v0.8.9] Automatic equipment filter active; weapons retained')end
end
return M
