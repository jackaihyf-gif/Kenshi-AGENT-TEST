-- Read-only metadata for one paused, configured test actor. No engine mutation.
local M={}
local function count(value,maximum,label)
 assert(type(value)=='number' and value==value and value>=0 and value<=maximum and value%1==0,label..' unavailable or invalid')
 return value
end
function M.snapshot(c,config,api)
 local w=assert(api.world(),'World unavailable')
 assert(not w.gameResetting and w.player,'World resetting or player unavailable')
 local list=w.player.playerCharacters
 assert(#list==1 and list[1]==c,'Single configured actor required')
 assert(w.paused==true and api.autosave()==false,'Pause isolated actor and disable autosave')
 local lifecycle=assert(api.lifecycle(),'Lifecycle unavailable')
 assert(lifecycle.guiThread==true and lifecycle.stable==true and lifecycle.busy==false and lifecycle.loading==false and api.gui_loading()==false,'Lifecycle not ready')
 local identity=assert(api.identity(),'Identity unavailable')
 assert(identity.stopped==false and identity.deferred==false,'Identity stopped or deferred')
 local epoch=count(identity.epoch,1000000000,'Identity epoch')
 assert(identity.sourcegeneration==lifecycle.generation,'Identity generation not current')
 local proof=assert(api.load_proof(),'No owned isolated load request')
 assert(type(proof.name)=='string' and #proof.name<=64 and proof.name:match('^T60_LIFE_096_[%w_]+$') and proof.epoch==epoch,'Owned load epoch not current')
 local load=assert(api.load_status(),'Save manager request status unavailable')
 assert(load.name==proof.name and load.location==proof.root and load.signal==0 and lifecycle.generation>proof.before_generation,'Isolated load request not completed or replaced')
 assert(c:getName()==config.test_character_name,'Single configured actor required')
 local a=assert(c:getAppearance(),'Appearance unavailable')
 assert(not a.isCreatingBody and not a.updateBody,'Appearance rebuilding')
 local owner=assert(api.owner(c),'Identity owner unavailable')
 local status=assert(api.wear(),'Wear metadata unavailable')
 assert(status.allocation_limit==16,'Unexpected appearance limit')
 local allocations=count(status.allocations,16,'Appearance allocations')
 local entries=count(status.pool_entries,16,'Visual pool entries')
 assert(entries<=allocations,'Visual entries exceed cumulative allocations')
 local materials=count(api.material_slots(),32,'Material slots')
 return {scope='single_actor_paused_cached_metadata',owner=owner,epoch=epoch,requested_test_slot=proof.name,
  save_manager_current_game=load.current_game,load_signal_idle=true,
  appearance_allocations=allocations,appearance_limit=16,visual_pool_entries=entries,
  material_slots=materials,material_limit=32,native_total_retained_objects_verified=false,
  production_reclamation_verified=false}
end
return M
