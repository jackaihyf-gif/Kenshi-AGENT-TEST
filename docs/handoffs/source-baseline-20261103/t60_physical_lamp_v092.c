/* Real Ogre point lights, registered through the game's original lantern query.
 * Ownership/position updates run on Lua's GUI thread. No stat/brightness writes. */
#include "t60_attachment_compat_v083.c"
#include <math.h>
typedef struct{float x,y,z;} LampV3;
typedef struct{float w,x,y,z;} LampQ;
typedef struct{void* vt;unsigned count,capacity;void** data;} LampList;
typedef void(*LampLights)(void*,LampList*);
typedef unsigned char(*LampHas)(void*);
static LampLights originalLampLights;static LampHas originalLampHas;
static void*(*createNativeLight)(void*,void*,unsigned char,int);
static void*(*lightManager)(void*);
static void*(*rootNode)(void*,int);
static void*(*childNode)(void*,int,const LampV3*,const LampQ*);
static void(*attachLight)(void*,void*),(*destroyLight)(void*,void*),(*destroyNode)(void*,void*);
static void(*setNodePosition)(void*,const LampV3*),(*reserveLights)(LampList*,int);
static void(*setLightVisible)(void*,unsigned char);
static void*(*objectCollection)(void*,const Str32*);
static void*(*parentNode)(void*);
static unsigned(*objectId)(void*);
static struct{void* app;void* light;void* manager;void* node;unsigned id;int enabled;} lamps[128];
static int lampHooked;static LONG lampQueries,lampAdds,lampFaults;
static int ownedLamp(int i){
 __try{
  /* Look up the pointer in the current manager before dereferencing it. World
   * reload may have deleted a pooled light; its monotonically assigned ID also
   * prevents an unrelated light at a reused address from being mistaken for it. */
  char* service=*(char**)((char*)GetModuleHandleA(NULL)+0x21322b8);if(!service)return 0;
  void* mgr=*(void**)(service+0x60);if(mgr!=lamps[i].manager)return 0;
  Str32 name={0};memcpy(name.storage.small,"Light",5);name.length=5;name.capacity=15;
  char* collection=objectCollection(mgr,&name);if(!collection)return 0;
  void** begin=*(void***)(collection),**end=*(void***)(collection+8);
  if(!begin||!end||end<begin||end-begin>65536)return 0;
  for(void** p=begin;p<end;p++)if(*p==lamps[i].light)return objectId(*p)==lamps[i].id;
 }__except(EXCEPTION_EXECUTE_HANDLER){InterlockedIncrement(&lampFaults);}
 return 0;
}
static int allocatedLamp(void* app){for(int i=0;i<128;i++)if(lamps[i].app==app&&lamps[i].light)return i;return -1;}
static int findLamp(void* app){int i=allocatedLamp(app);return i>=0&&lamps[i].enabled&&ownedLamp(i)?i:-1;}
static void includeLamp(void* app,LampList* list){
 originalLampLights(app,list);InterlockedIncrement(&lampQueries);int i=findLamp(app);if(i<0)return;
 __try{
  if(list->count>list->capacity||list->capacity>65536){InterlockedIncrement(&lampFaults);return;}
  if(list->count==list->capacity)reserveLights(list,list->capacity?list->capacity*2:10);
  list->data[list->count++]=lamps[i].light;InterlockedIncrement(&lampAdds);
 }__except(EXCEPTION_EXECUTE_HANDLER){InterlockedIncrement(&lampFaults);}
}
static unsigned char hasPhysicalLamp(void* app){return findLamp(app)>=0?1:originalLampHas(app);}
API int T60_physical_lamp_ready(void){
 if(lampHooked)return 1;if(bind()!=1)return -1;char* b=(char*)GetModuleHandleA(NULL);
 if(memcmp(b+0x52c1f0,"\x48\x89\x5c\x24\x10\x57\x48\x83\xec\x20",10)||memcmp(b+0x52c170,"\x40\x53\x48\x83\xec\x20\x48\x83\x79\x30\x00",11)||memcmp(b+0x814850,"\x48\x8b\xc4\x55\x56\x57\x41\x54",8)||memcmp(b+0x7e8110,"\x48\x89\x5c\x24\x10\x57\x48\x83\xec\x20",10))return -2;
 HMODULE og=GetModuleHandleA("OgreMain_x64.dll");
 lightManager=(void*)GetProcAddress(og,"?_getManager@MovableObject@Ogre@@QEBAPEAVSceneManager@2@XZ");
 rootNode=(void*)GetProcAddress(og,"?getRootSceneNode@SceneManager@Ogre@@QEAAPEAVSceneNode@2@W4SceneMemoryMgrTypes@2@@Z");
 childNode=(void*)GetProcAddress(og,"?createChildSceneNode@SceneNode@Ogre@@UEAAPEAV12@W4SceneMemoryMgrTypes@2@AEBVVector3@2@AEBVQuaternion@2@@Z");
 attachLight=(void*)GetProcAddress(og,"?attachObject@SceneNode@Ogre@@QEAAXPEAVMovableObject@2@@Z");
 destroyLight=(void*)GetProcAddress(og,"?destroyLight@SceneManager@Ogre@@UEAAXPEAVLight@2@@Z");
 destroyNode=(void*)GetProcAddress(og,"?destroySceneNode@SceneManager@Ogre@@UEAAXPEAVSceneNode@2@@Z");
 setNodePosition=(void*)GetProcAddress(og,"?setPosition@Node@Ogre@@QEAAXAEBVVector3@2@@Z");
 setLightVisible=(void*)GetProcAddress(og,"?setVisible@MovableObject@Ogre@@QEAAX_N@Z");
 objectCollection=(void*)GetProcAddress(og,"?getMovableObjectCollection@SceneManager@Ogre@@IEBAPEBUMovableObjectCollection@12@AEBV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z");
 objectId=(void*)GetProcAddress(og,"?getId@IdObject@Ogre@@QEBAIXZ");
 parentNode=(void*)GetProcAddress(og,"?getParentSceneNode@MovableObject@Ogre@@QEBAPEAVSceneNode@2@XZ");
 if(!lightManager||!rootNode||!childNode||!attachLight||!destroyLight||!destroyNode||!setNodePosition||!setLightVisible||!objectCollection||!objectId||!parentNode)return -3;
 createNativeLight=(void*)(b+0x814850);reserveLights=(void*)(b+0x7e8110);
 typedef int(*Install)(void*,void*,void**);Install install=(Install)GetProcAddress(GetModuleHandleA("KenshiLib.dll"),"?AddHook@KenshiLib@@YA?AW4HookStatus@1@PEAX0PEAPEAX@Z");if(!install)return -4;
 HMODULE self;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(const char*)&T60_physical_lamp_ready,&self))return -5;
 int result=install(b+0x52c1f0,includeLamp,(void**)&originalLampLights);if(result!=0)return -100-result;
 result=install(b+0x52c170,hasPhysicalLamp,(void**)&originalLampHas);if(result!=0)return -200-result;
 lampHooked=1;return 1;
}
API int T60_physical_lamp_update(void* app,void* data,const LampV3* p,int enabled){
 if(!lampHooked||!app)return -1;int i=allocatedLamp(app);
 __try{
  if(i>=0&&!ownedLamp(i)){memset(&lamps[i],0,sizeof(lamps[i]));i=-1;}
  /* Renderer caches Light pointers across frames. Keep the engine-owned light
   * pooled until scene teardown; never delete it from a live GUI callback. */
  if(!enabled){if(i<0)return 0;lamps[i].enabled=0;setLightVisible(lamps[i].light,0);return 0;}
  if(!data||!p||!isfinite(p->x)||!isfinite(p->y)||!isfinite(p->z))return -2;
  if(i<0){for(i=0;i<128;i++)if(!lamps[i].app)break;if(i==128)return -3;
   void* light=createNativeLight(NULL,data,0,0);if(!light)return -4;void* manager=lightManager(light);if(!manager)return -5;
   LampQ q={1,0,0,0};void* node=childNode(rootNode(manager,0),0,p,&q);if(!node){destroyLight(manager,light);return -6;}
   attachLight(node,light);lamps[i].app=app;lamps[i].light=light;lamps[i].manager=manager;lamps[i].node=node;lamps[i].id=objectId(light);
  }
  if(parentNode(lamps[i].light)!=lamps[i].node){LampQ q={1,0,0,0};lamps[i].node=childNode(rootNode(lamps[i].manager,0),0,p,&q);attachLight(lamps[i].node,lamps[i].light);}
  setNodePosition(lamps[i].node,p);setLightVisible(lamps[i].light,1);lamps[i].enabled=1;return 1;
 }__except(EXCEPTION_EXECUTE_HANDLER){InterlockedIncrement(&lampFaults);return -9;}
}
API void T60_physical_lamp_forget_world(void){
 for(int i=0;i<128;i++)if(lamps[i].light&&ownedLamp(i))setLightVisible(lamps[i].light,0);
 memset(lamps,0,sizeof(lamps));
}
API int T60_physical_lamp_probe(void* app,char* out,size_t cap){
 if(!out||cap<1024)return -1;int i=findLamp(app),count=0;for(int j=0;j<128;j++)count+=lamps[j].light!=NULL&&lamps[j].enabled;
 return snprintf(out,cap,"{\"active\":%s,\"count\":%d,\"queries\":%ld,\"appended\":%ld,\"faults\":%ld,\"brightness_writes\":0,\"stat_writes\":0}",i>=0?"true":"false",count,lampQueries,lampAdds,lampFaults);
}
