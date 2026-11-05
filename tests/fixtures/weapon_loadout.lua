local isolated,paused,auto=true,true,false
local world={};local made,removed=0,0;local manufacturer={}
local inv={};local primary;local original
local function item(id,generated)
 local x={data={stringID=id,name=id},manufacturerData=manufacturer,isInInventory=false,isEquipped=false,generated=generated}
 function x:isWeapon()return self end
 function x:getCategory()return 1 end
 function x:getCategory_animationOverride()return 1 end
 function x:getItemWeight()return 2 end
 function x:getInventory()return self.inv end
 return x
end
local bag={width=8,height=6};local equipped={}
function bag:hasRoomForItem()return self.width==20 end
function inv:resizeSection(section,w,h,clear)assert(section==bag and clear==false);section.width=w;section.height=h end
function bag:addItem(x)x.inv=inv;x.isInInventory=true;x.isEquipped=false;x.inventorySection='main';return true end
function equipped:removeItem(x)assert(primary==x);primary=nil;x.isEquipped=false;return true end
function equipped:addItem(x)primary=x;x.isEquipped=true;return true end
function inv:getSection(name)return name=='main' and bag or equipped end
function inv:getPrimaryWeapon()return primary end
function inv:getSecondaryWeapon()return nil end
function inv:getAllItems()local list={};if original and original.inv==self then list[#list+1]=original end;if primary and primary~=original then list[#list+1]=primary end;return list end
function inv:equipItem(x)primary=x;x.inv=self;x.isInInventory=true;x.isEquipped=true;x.inventorySection='weapon';return true end
function inv:addItem(x)bag:addItem(x);primary=x;return true end
function inv:removeItemAutoDestroy(x,n)assert(x.generated and x~=original and n==1);removed=removed+1;if primary==x then primary=nil end;x.inv=nil;return true end
function inv:notifyModified()end
local c={}
local fixtureStats={_strength=50}
function c:getStats()return fixtureStats end
function c:getInventory()return inv end
function c:getCurrentWeapon()return primary end
function c:getHandle()return {toString=function()return '1-2-3' end} end
function c:drawWeapon(x,section)assert(x==primary and section==x.inventorySection);self.drawn=x;return true end
function c:healCompletely()self.healed=true end
function c:generateWeapon(data,m)assert(m==manufacturer);made=made+1;return item(data.stringID,true) end
original=item('original',false);inv:equipItem(original)
local ctrl=Controller.new({guard=function()assert(isolated)end,world=function()return world end,
 paused=function()return paused end,autosave=function()return auto end,lookup=function(id)return {stringID=id,name=id}end})
assert(not pcall(ctrl.select,c,'arbitrary-id') and made==0 and primary==original)
auto=true;assert(not pcall(ctrl.select,c,'katana') and made==0);auto=false
paused=false;assert(not pcall(ctrl.select,c,'katana') and made==0);paused=true
isolated=false;assert(not pcall(ctrl.select,c,'katana') and made==0);isolated=true
assert(ctrl.select(c,'reset-health').fixture_health_reset and c.healed and made==0)
local fixture=ctrl.select(c,'gait-fixture');assert(fixture.fixture_only and fixture.original_strength==50 and fixtureStats._strength==150)
assert(not pcall(ctrl.select,c,'gait-fixture'))
assert(ctrl.select(c,'gait-restore').restored and fixtureStats._strength==50)
ctrl.select(c,'katana');assert(primary.generated and original.inv==inv and not original.isEquipped)
ctrl.select(c,'draw');assert(c.drawn==primary and not original.isEquipped)
ctrl.select(c,'polearm');assert(made==2 and removed==1)
ctrl.select(c,'original');assert(primary==original and removed==2 and original.isEquipped)
assert(bag.width==8 and bag.height==6,'Original inventory dimensions must be restored')
assert(ctrl.select(c,'status').primary.id=='original')
ctrl.select(c,'original');assert(removed==2)
for i=1,8 do ctrl.select(c,'heavy')end
assert(not pcall(ctrl.select,c,'heavy') and made==10)
ctrl.select(c,'original');assert(primary==original and original.inv==inv)
