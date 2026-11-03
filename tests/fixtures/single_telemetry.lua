local c={getName=function()return 'Single Test' end,getAppearance=function()return app end}
app={isCreatingBody=false,updateBody=false}
local world={paused=true,gameResetting=false,player={playerCharacters={c}}}
local autosave=false
local identity={epoch=7,stopped=false,deferred=false,sourcegeneration=4}
local lifecycle={guiThread=true,stable=true,busy=false,loading=false,generation=4}
local guiLoading=false
local proof={name='T60_LIFE_096_TEST',epoch=7,root='test-root',before_generation=3}
local load={name='T60_LIFE_096_TEST',location='test-root',signal=0,current_game='stale-menu-value'}
local wear={allocations=5,allocation_limit=16,pool_entries=1}
local materialCalls=0
local materials=5
local api={world=function()return world end,autosave=function()return autosave end,
 lifecycle=function()return lifecycle end,gui_loading=function()return guiLoading end,load_proof=function()return proof end,load_status=function()return load end,
 identity=function()return identity end,owner=function(actor)assert(actor==c);return 'token7'end,
 wear=function()return wear end,material_slots=function()materialCalls=materialCalls+1;return materials end}
local config={test_character_name='Single Test'}
local function snap()return Observer.snapshot(c,config,api)end
local function rejected(change,restore)
 local calls=materialCalls;change();assert(not pcall(snap));restore()
 -- All fixture/metadata failures must be rejected before any native counter call.
 assert(materialCalls==calls)
end
local r=snap()
assert(r.appearance_allocations==5 and r.visual_pool_entries==1 and r.material_slots==5)
assert(r.native_total_retained_objects_verified==false and r.production_reclamation_verified==false)
assert(r.epoch==7 and wear.allocations==5 and wear.pool_entries==1 and identity.epoch==7)
r.appearance_allocations=0;assert(snap().appearance_allocations==5)
rejected(function()world.paused=false end,function()world.paused=true end)
rejected(function()autosave=true end,function()autosave=false end)
rejected(function()world.gameResetting=true end,function()world.gameResetting=false end)
rejected(function()lifecycle.loading=true end,function()lifecycle.loading=false end)
rejected(function()lifecycle.busy=true end,function()lifecycle.busy=false end)
rejected(function()lifecycle.stable=false end,function()lifecycle.stable=true end)
rejected(function()lifecycle.guiThread=false end,function()lifecycle.guiThread=true end)
rejected(function()guiLoading=true end,function()guiLoading=false end)
rejected(function()identity.sourcegeneration=3 end,function()identity.sourcegeneration=4 end)
rejected(function()proof.epoch=6 end,function()proof.epoch=7 end)
rejected(function()proof.name='private'end,function()proof.name='T60_LIFE_096_TEST'end)
rejected(function()proof=nil end,function()proof={name='T60_LIFE_096_TEST',epoch=7,root='test-root',before_generation=3}end)
rejected(function()load.name='unrelated-slot'end,function()load.name='T60_LIFE_096_TEST'end)
rejected(function()load.location='private-save-root'end,function()load.location='test-root'end)
rejected(function()load.signal=2 end,function()load.signal=0 end)
rejected(function()lifecycle.generation=3;identity.sourcegeneration=3 end,function()lifecycle.generation=4;identity.sourcegeneration=4 end)
rejected(function()world.player.playerCharacters={}end,function()world.player.playerCharacters={c}end)
rejected(function()world.player.playerCharacters={c,c}end,function()world.player.playerCharacters={c}end)
rejected(function()config.test_character_name='Other'end,function()config.test_character_name='Single Test'end)
rejected(function()app.updateBody=true end,function()app.updateBody=false end)
rejected(function()app.isCreatingBody=true end,function()app.isCreatingBody=false end)
rejected(function()identity.stopped=true end,function()identity.stopped=false end)
rejected(function()identity.deferred=true end,function()identity.deferred=false end)
rejected(function()wear.allocations=nil end,function()wear.allocations=5 end)
rejected(function()wear.allocations=0/0 end,function()wear.allocations=5 end)
rejected(function()wear.allocations=17 end,function()wear.allocations=5 end)
rejected(function()wear.allocations=1.5 end,function()wear.allocations=5 end)
rejected(function()wear.pool_entries=6 end,function()wear.pool_entries=1 end)
rejected(function()wear.allocation_limit=32 end,function()wear.allocation_limit=16 end)
materials=nil;assert(not pcall(snap))
materials=33;assert(not pcall(snap))
materials=0/0;assert(not pcall(snap))
materials=32;wear.allocations=16;wear.pool_entries=16
assert(snap().material_slots==32 and snap().appearance_allocations==16)
