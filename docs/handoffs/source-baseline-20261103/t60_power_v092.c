/* Exact-build, read-only strength accessor augmentation. No base skill writes.
 * Resolve the actual equipped belt for every query: no cached actor pointers. */
#include "t60_attachment_compat_v083.c"
#include <math.h>
typedef float(*Strength)(void*);
typedef void*(*Getter)(void*);
typedef void*(*Section)(void*,int);
static Strength originalStrength;
static Getter inventoryOf,itemOf,dataOf;
static Section beltSection;
typedef unsigned char(*Acid)(void*,float);
static Acid originalAcidWater,originalAcidFeet;
static void* targetData;
static int installed;
static volatile LONG calls,boosted,faults;
static int characterWears(void* c){
 if(!c||!targetData)return 0;
 __try{
  void* inv=inventoryOf(c);if(!inv)return 0;
  void* section=beltSection(inv,14);if(!section)return 0;
  void* item=itemOf(section);return item&&dataOf(item)==targetData;
 }__except(EXCEPTION_EXECUTE_HANDLER){InterlockedIncrement(&faults);return 0;}
}
static int wears(void* stats){return stats&&characterWears(*(void**)((char*)stats+0x10));}
static unsigned char powerAcidWater(void* med,float amount){
 if(characterWears(*(void**)((char*)med+0xe0)))return 0;
 return originalAcidWater(med,amount);
}
static unsigned char powerAcidFeet(void* med,float amount){
 if(characterWears(*(void**)((char*)med+0xe0)))return 0;
 return originalAcidFeet(med,amount);
}
static float powerStrength(void* stats){
 float value=originalStrength(stats);InterlockedIncrement(&calls);
 if(wears(stats)){InterlockedIncrement(&boosted);return value*1.5f;}return value;
}
API int T60_power_ready(void){
 if(installed)return 1;
 if(bind()!=1)return -1;
 HMODULE lib=GetModuleHandleA("KenshiLib.dll");char* base=(char*)GetModuleHandleA(NULL);
 const unsigned char signature[]={0xf3,0x0f,0x10,0x81,0x80,0,0,0,0xf3,0x0f,0x59,0x41,0x34,0xc3};
 if(memcmp(base+0x6409f0,signature,sizeof(signature)))return -2;
 if(memcmp(base+0x6461f0,"\x48\x8b\xc4\x55\x57\x41\x54\x48\x8d\x68\x88",11)||
    memcmp(base+0x646580,"\x48\x8b\xc4\x55\x48\x8d\x68\xa8",8))return -5;
 inventoryOf=(Getter)GetProcAddress(lib,"?_NV_getInventory@Character@@QEBAPEAVInventory@@XZ");
 beltSection=(Section)GetProcAddress(lib,"?getSectionOfType@Inventory@@QEAAPEAVInventorySection@@W4AttachSlot@@@Z");
 itemOf=(Getter)GetProcAddress(lib,"?getItem@InventorySection@@QEBAPEAVItem@@XZ");
 dataOf=(Getter)GetProcAddress(lib,"?_NV_getGameData@RootObjectBase@@QEBAPEAVGameData@@XZ");
 typedef int(*Install)(void*,void*,void**);
 Install install=(Install)GetProcAddress(lib,"?AddHook@KenshiLib@@YA?AW4HookStatus@1@PEAX0PEAPEAX@Z");
 if(!inventoryOf||!beltSection||!itemOf||!dataOf||!install)return -3;
 HMODULE self;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(const char*)&T60_power_ready,&self))return -4;
 int result=install(base+0x6409f0,powerStrength,(void**)&originalStrength);
 if(result!=0)return -100-result;
 result=install(base+0x6461f0,powerAcidWater,(void**)&originalAcidWater);if(result!=0)return -200-result;
 result=install(base+0x646580,powerAcidFeet,(void**)&originalAcidFeet);if(result!=0)return -300-result;
 installed=1;return 1;
}
API void T60_power_target(void* data){targetData=data;}
API int T60_power_probe(void* stats,char* out,size_t cap){
 if(!installed||!stats||!out||cap<1024)return -1;
 __try{
  float raw=*(float*)((char*)stats+0x80),base=originalStrength(stats);
  float actual=powerStrength(stats);if(!isfinite(raw)||!isfinite(base)||!isfinite(actual))return -2;
  return snprintf(out,cap,"{\"raw\":%.8f,\"unboosted_base\":%.8f,\"boosted_base\":%.8f,\"equipped\":%s,\"factor\":1.5,\"calls\":%ld,\"boosted_calls\":%ld,\"faults\":%ld,\"base_writes\":0}",raw,base,actual,wears(stats)?"true":"false",calls,boosted,faults);
 }__except(EXCEPTION_EXECUTE_HANDLER){return -3;}
}
