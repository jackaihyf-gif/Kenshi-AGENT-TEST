/* T60 per-body material bridge. No hooks, automatic injection or DLL attach work.
 * Uses only resolved public Ogre methods. C shims intentionally avoid linking a
 * modern C++ STL against the game's MSVC100 ABI. The two serialized ABI views
 * below are checked against the installed binary and exercised in a child process.
 * Returned engine-owned SharedPtr handles are retained in a bounded process pool;
 * no guessed refcount offset/destructor implementation is used.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wincrypt.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "t60_ogre_symbols.h"

#define API __declspec(dllexport)
#define GROUP "JACK_T60_Eyes_v091"
#define PROGRAM "JACK_T60_YellowEyes_FP_v091"
#define DAY_PROGRAM "JACK_T60_Day_FP_v091"
#define NORMAL "t60_eye_emission_n_v091.dds"
#define LIMIT 32
typedef struct { union { char small[16]; const char* data; } storage; uint64_t length,capacity; } Str32;
typedef struct { void* rep; void* info; } Shared16;
_Static_assert(sizeof(Str32)==32 && offsetof(Str32,length)==16 && offsetof(Str32,capacity)==24,"MSVC100 string view");
_Static_assert(sizeof(Shared16)==16,"Ogre engine SharedPtr return storage");

/* Aggregate C++ member returns use this=RCX, explicit return-storage=RDX.
 * Do not declare these as C functions returning a struct by value. */
typedef void* (*Fn0)(void);
typedef void* (*FnThis)(void*);
typedef void* (*FnCtor)(void*,const Str32*,const Str32*,const Str32*);
typedef void* (*FnAlloc)(size_t);
typedef void (*FnFree)(void*);
typedef Shared16* (*FnCreate)(void*,Shared16*,const Str32*,const Str32*,unsigned char,void*,const void*);
typedef Shared16* (*FnFind)(void*,Shared16*,const Str32*,const Str32*);
typedef Shared16* (*FnClone)(void*,Shared16*,const Str32*,unsigned char,const Str32*);
typedef void (*FnCopy)(void*,Shared16*);
typedef const Str32* (*FnString)(void*);
typedef unsigned short (*FnCount16)(void*);
typedef size_t (*FnCountSize)(void*);
typedef void* (*FnGet16)(void*,unsigned short);
typedef void* (*FnGetSize)(void*,size_t);
typedef void (*FnStringSet)(void*,const Str32*);
typedef void (*FnProgram)(void*,const Str32*,unsigned char);
typedef void (*FnTexture)(void*,const Str32*,int);
typedef void (*FnLoad)(void*,unsigned char);
typedef const Shared16* (*FnMaterial)(void*);
typedef void (*FnSetMaterial)(void*,const Shared16*);
typedef unsigned char (*FnExists)(void*,const Str32*);
typedef unsigned char (*FnSupported)(void*);
typedef void (*FnGroupCreate)(void*,const Str32*,unsigned char);
typedef void (*FnLocation)(void*,const Str32*,const Str32*,const Str32*,unsigned char,unsigned char);

struct Interface {
 FnCtor root_ctor; FnFree root_dtor; Fn0 root_singleton; FnThis root_renderer;
 FnAlloc allocate; FnFree deallocate; Fn0 material_manager;
 FnCreate material_create; FnFind material_find; FnClone material_clone; FnCopy material_copy;
 FnString material_name,material_group; FnLoad material_load;
 FnCount16 tech_count; FnGet16 tech_get; FnThis tech_create;
 FnSupported tech_supported; FnCount16 material_supported;
 FnCount16 pass_count; FnGet16 pass_get; FnThis pass_create;
 FnString pass_vp,pass_fp; FnProgram pass_set_fp;
 FnCount16 unit_count; FnGetSize unit_get; FnThis unit_create;
 FnString unit_name,unit_texture; FnStringSet unit_set_name; FnTexture unit_set_texture;
 FnCountSize entity_count; FnGetSize entity_sub; FnMaterial sub_material; FnSetMaterial sub_set_material;
 Fn0 groups; FnExists group_exists; FnGroupCreate group_create;
 FnStringSet group_destroy,group_initialise; FnLocation group_location;
} og;
typedef struct {
 char owner[160]; unsigned long long generation; int female;
 Shared16 original,modified;
} Slot;
static int night_mode;
static struct {
 DWORD thread; int bound,registered,enabled,slots,applied; char error[512]; char path[1024]; Slot slot[LIMIT];
} state;

static Str32 str(const char* p) {
 Str32 s;memset(&s,0,sizeof(s));size_t n=strlen(p);s.length=n;
 if(n<16){memcpy(s.storage.small,p,n+1);s.capacity=15;}
 else{s.storage.data=p;s.capacity=n;}
 return s;
}
static const char* text(const Str32* s) {
 if(!s || s->length>8192 || s->capacity<s->length)return NULL;
 return s->capacity<16 ? s->storage.small:s->storage.data;
}
static int equal(const Str32* s,const char* p) {
 const char* c=text(s);return c && s->length==strlen(p) && !memcmp(c,p,(size_t)s->length);
}
static int copy_text(const Str32* s,char* p,size_t cap) {
 const char* c=text(s);if(!c || s->length>=cap)return 0;
 memcpy(p,c,(size_t)s->length);p[s->length]=0;return 1;
}
static int fail(const char* message){snprintf(state.error,sizeof(state.error),"%s",message);return -1;}
static int owner_thread(void){return state.thread==GetCurrentThreadId();}
static int hash_module(HMODULE module) {
 char path[MAX_PATH*4]; if(!GetModuleFileNameA(module,path,sizeof(path)))return 0;
 HANDLE file=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_EXISTING,0,NULL);
 if(file==INVALID_HANDLE_VALUE)return 0;
 HCRYPTPROV provider=0;HCRYPTHASH hash=0;int ok=0;BYTE data[65536],digest[32];DWORD n=0,size=32;
 if(!CryptAcquireContextA(&provider,NULL,NULL,PROV_RSA_AES,CRYPT_VERIFYCONTEXT))goto done;
 if(!CryptCreateHash(provider,CALG_SHA_256,0,0,&hash))goto done;
 while(ReadFile(file,data,sizeof(data),&n,NULL) && n){if(!CryptHashData(hash,data,n,0))goto done;}
 if(!CryptGetHashParam(hash,HP_HASHVAL,digest,&size,0) || size!=32)goto done;
 char out[65];for(int i=0;i<32;i++)snprintf(out+i*2,3,"%02x",digest[i]);out[64]=0;
 ok=!strcmp(out,T60_EXPECTED_OGRE_SHA256);
done:if(hash)CryptDestroyHash(hash);if(provider)CryptReleaseContext(provider,0);CloseHandle(file);return ok;
}
#define RESOLVE(name,type) do { og.name=(type)(uintptr_t)GetProcAddress(module,SYM_##name); if(!og.name)return fail("Missing export: " #name); } while(0)
API int T60_material_bind(void) {
 if(GetModuleHandleA("T60MaterialBridge_v091.dll"))return fail("Cold restart required; original material bridge is still loaded");
 if(state.bound)return owner_thread()?0:fail("Main-thread gate");
 HMODULE module=GetModuleHandleA("OgreMain_x64.dll");if(!module)return fail("Ogre DLL not loaded");
 if(!hash_module(module))return fail("Installed Ogre DLL hash differs from the verified ABI");
 RESOLVE(root_ctor,FnCtor);RESOLVE(root_dtor,FnFree);RESOLVE(root_singleton,Fn0);RESOLVE(root_renderer,FnThis);
 RESOLVE(allocate,FnAlloc);RESOLVE(deallocate,FnFree);RESOLVE(material_manager,Fn0);
 RESOLVE(material_create,FnCreate);RESOLVE(material_find,FnFind);RESOLVE(material_clone,FnClone);RESOLVE(material_copy,FnCopy);
 RESOLVE(material_name,FnString);RESOLVE(material_group,FnString);RESOLVE(material_load,FnLoad);
 RESOLVE(tech_count,FnCount16);RESOLVE(tech_get,FnGet16);RESOLVE(tech_create,FnThis);
 RESOLVE(tech_supported,FnSupported);RESOLVE(material_supported,FnCount16);
 RESOLVE(pass_count,FnCount16);RESOLVE(pass_get,FnGet16);RESOLVE(pass_create,FnThis);
 RESOLVE(pass_vp,FnString);RESOLVE(pass_fp,FnString);RESOLVE(pass_set_fp,FnProgram);
 RESOLVE(unit_count,FnCount16);RESOLVE(unit_get,FnGetSize);RESOLVE(unit_create,FnThis);
 RESOLVE(unit_name,FnString);RESOLVE(unit_texture,FnString);RESOLVE(unit_set_name,FnStringSet);RESOLVE(unit_set_texture,FnTexture);
 RESOLVE(entity_count,FnCountSize);RESOLVE(entity_sub,FnGetSize);RESOLVE(sub_material,FnMaterial);RESOLVE(sub_set_material,FnSetMaterial);
 RESOLVE(groups,Fn0);RESOLVE(group_exists,FnExists);RESOLVE(group_create,FnGroupCreate);
 RESOLVE(group_destroy,FnStringSet);RESOLVE(group_initialise,FnStringSet);RESOLVE(group_location,FnLocation);
 state.thread=GetCurrentThreadId();state.bound=1;state.error[0]=0;return 1;
}

API const char* T60_material_error(void){return state.error;}
API int T60_material_enabled(void){return state.enabled;}
API int T60_material_slots(void){return state.slots;}
API int T60_material_applied(void){return state.applied;}
API int T60_material_enable(int enabled) {
 if(!state.bound || !owner_thread())return fail("Bind on the game GUI thread first");
 if(enabled && !state.registered)return fail("Resources not registered");
 state.enabled=enabled!=0;return state.enabled;
}
API int T60_material_register(const char* absolute_path) {
 if(!state.bound || !owner_thread())return fail("Main-thread gate");
 if(state.enabled)return fail("Disable before registration");
 if(!absolute_path || strlen(absolute_path)>=sizeof(state.path) || strlen(absolute_path)<4 || absolute_path[1]!=':')return fail("Absolute resource path required");
 if(state.registered)return !strcmp(state.path,absolute_path)?0:fail("Resource path cannot change within a process");
 char test[1400];snprintf(test,sizeof(test),"%s/%s",absolute_path,"jack_t60_metal.program");
 if(GetFileAttributesA(test)==INVALID_FILE_ATTRIBUTES)return fail("Resource program file missing");
 int result=-1;
 __try {
  void* groups=og.groups();if(!groups)return fail("ResourceGroupManager unavailable");
  Str32 group=str(GROUP),path=str(absolute_path),type=str("FileSystem");
  if(og.group_exists(groups,&group))return fail("Refuse to take over an existing material resource group");
  og.group_create(groups,&group,1);og.group_location(groups,&path,&type,&group,0,1);og.group_initialise(groups,&group);
  strcpy(state.path,absolute_path);state.registered=1;state.error[0]=0;result=1;
 } __except(EXCEPTION_EXECUTE_HANDLER) {
  snprintf(state.error,sizeof(state.error),"Resource registration exception 0x%08lx; candidate disabled",GetExceptionCode());state.enabled=0;
 }
 return result;
}

static int configure(void* source,void* modified) {
 unsigned changed=0;
 if(og.tech_count(source)!=og.tech_count(modified))return fail("Technique count changed");
 for(unsigned short ti=0;ti<og.tech_count(source);ti++) {
  void* st=og.tech_get(source,ti);void* dt=og.tech_get(modified,ti);
  if(og.pass_count(st)!=og.pass_count(dt))return fail("Pass count changed");
  for(unsigned short pi=0;pi<og.pass_count(st);pi++) {
   void* sp=og.pass_get(st,pi);void* dp=og.pass_get(dt,pi);
   const Str32* fp=og.pass_fp(sp);
   if(!equal(fp,"Character_FP") && !equal(fp,"Character_FP_HLSL"))continue;
   char vp[256];if(!copy_text(og.pass_vp(sp),vp,sizeof(vp)) || !equal(og.pass_vp(dp),vp))return fail("Vertex program changed");
   if(og.unit_count(sp)!=og.unit_count(dp))return fail("Texture unit count changed");
   int normal_found=0;
   for(unsigned short ui=0;ui<og.unit_count(sp);ui++) {
    void* su=og.unit_get(sp,ui);void* du=og.unit_get(dp,ui);char n[256],texture[1024];
    if(!copy_text(og.unit_name(su),n,sizeof(n)) || !equal(og.unit_name(du),n))return fail("Texture unit order changed");
    if(!copy_text(og.unit_texture(su),texture,sizeof(texture)) || !equal(og.unit_texture(du),texture))return fail("Cloned texture changed");
    if(!strcmp(n,"normalMap")){Str32 normal=str(NORMAL);og.unit_set_texture(du,&normal,2);normal_found++;}
   }
   if(normal_found!=1)return fail("Expected one normalMap texture unit");
   Str32 program=str(night_mode?PROGRAM:DAY_PROGRAM);og.pass_set_fp(dp,&program,0);changed++;
  }
 }
 if(changed!=1)return fail("Expected exactly one Character main pass");
 og.material_load(modified,0);
 if(!og.material_supported(modified))return fail("Compiled material has no supported technique; original kept");
 return 1;
}

#include "binding_consistency.h"

API int T60_material_apply(void* entity,const char* owner,int female,unsigned long long generation,const char* filename) {
 if(!state.bound || !owner_thread())return fail("Main-thread gate");
 if(!state.enabled || !state.registered)return 0;
 if(!entity || !owner || !*owner || strlen(owner)>=sizeof(state.slot[0].owner))return fail("Invalid body or owner");
 if(!filename || !strstr(filename,"jack_t60_wear_v08.mesh"))return fail("Refuse non-v08 T60 body");
 int result=-1;
 __try {
  if(og.entity_count(entity)!=1)return fail("Single-submesh body required");
  void* sub=og.entity_sub(entity,0);const Shared16* current=og.sub_material(sub);
  if(!current || !current->rep)return fail("Body material unavailable");
  for(int i=0;i<state.slots;i++) {
   Slot* slot=&state.slot[i];
   if(slot->modified.rep==current->rep && slot->female==female && !strcmp(slot->owner,owner)){
    int repaired=repair_private_normal(current->rep);
    if(repaired<0){state.enabled=0;return -1;}
    slot->generation=generation;return repaired; /* no clone, compile, or slot growth */
   }
  }
  char name[256],group_name[256];
  if(!copy_text(og.material_name(current->rep),name,sizeof(name)) || strncmp(name,"Character_",10))return fail("Refuse non-Character body material");
  if(!copy_text(og.material_group(current->rep),group_name,sizeof(group_name)))return fail("Original resource group unavailable");
  /* A wear roundtrip or F10/F9 on the same owner/template must reuse its
   * retained clone instead of spending a slot. Refresh from the current engine
   * material before configuration; no STL ownership/refcount internals touched. */
  for(int i=0;i<state.slots;i++) {
   Slot* slot=&state.slot[i];
   if(slot->original.rep==current->rep && slot->modified.rep && slot->female==female && !strcmp(slot->owner,owner)) {
    og.material_copy(current->rep,&slot->modified);
    if(configure(current->rep,slot->modified.rep)<0){state.enabled=0;return -1;}
    slot->generation=generation;og.sub_set_material(sub,&slot->modified);
    state.applied++;state.error[0]=0;return 1;
   }
  }
  if(state.slots>=LIMIT)return fail("32 material generations retained; restart before another material allocation");
  Slot* slot=&state.slot[state.slots++];memset(slot,0,sizeof(*slot));strcpy(slot->owner,owner);slot->female=female;slot->generation=generation;
  Str32 original_name=str(name),original_group=str(group_name),new_group=str(GROUP);void* mm=og.material_manager();
  og.material_find(mm,&slot->original,&original_name,&original_group);
  if(slot->original.rep!=current->rep)return fail("Original material lookup mismatch");
  snprintf(name,sizeof(name),"JACK_T60_v08_Metal_%d",state.slots);Str32 new_name=str(name);
  og.material_clone(current->rep,&slot->modified,&new_name,1,&new_group);
  /* Retain both returned references through full process exit. Count before any
   * later call can fail, so a failed preparation cannot allocate endlessly. */
  if(!slot->modified.rep || configure(current->rep,slot->modified.rep)<0){state.enabled=0;return -1;}
  og.sub_set_material(sub,&slot->modified);state.applied++;state.error[0]=0;result=1;
 } __except(EXCEPTION_EXECUTE_HANDLER) {
  snprintf(state.error,sizeof(state.error),"Material prepare exception 0x%08lx; candidate disabled",GetExceptionCode());state.enabled=0;
 }
 return result;
}
API int T60_material_restore(void* live_entity) {
 if(!state.bound || !owner_thread())return fail("Main-thread gate");
 if(!live_entity)return 0;int result=0;
 __try {
  if(og.entity_count(live_entity)!=1)return 0;
  void* sub=og.entity_sub(live_entity,0);const Shared16* current=og.sub_material(sub);
  for(int i=0;i<state.slots;i++)if(state.slot[i].modified.rep==current->rep) {
   og.sub_set_material(sub,&state.slot[i].original);result=1;break;
  }
 } __except(EXCEPTION_EXECUTE_HANDLER) {result=fail("Material restore exception; stop candidate");state.enabled=0;}
 return result;
}

API int T60_material_night_state(void){return night_mode;}
API int T60_material_night(int value){
 if(!state.bound || !owner_thread())return fail("Main-thread gate");
 int next=value!=0;if(next==night_mode)return 0;
 __try {
  for(int i=0;i<state.slots;i++){
   void* material=state.slot[i].modified.rep;if(!material)continue;
   for(unsigned short ti=0;ti<og.tech_count(material);ti++){
    void* tech=og.tech_get(material,ti);
    for(unsigned short pi=0;pi<og.pass_count(tech);pi++){
     void* pass=og.pass_get(tech,pi);const Str32* old=og.pass_fp(pass);
     if(equal(old,PROGRAM)||equal(old,DAY_PROGRAM)){Str32 program=str(next?PROGRAM:DAY_PROGRAM);og.pass_set_fp(pass,&program,0);}
    }
   }
   og.material_load(material,0);
   if(!og.material_supported(material))return fail("Night transition unsupported");
  }
  night_mode=next;return 1;
 }__except(EXCEPTION_EXECUTE_HANDLER){state.enabled=0;return fail("Night transition exception");}
}

#ifdef T60_STANDALONE_TEST
/* Separate-process integration test. Does not open or attach to Kenshi. */
#define CHECK(x) do { if(!(x)){fprintf(stderr,"FAIL line %d: %s (%s)\n",__LINE__,#x,state.error);return 1;} } while(0)
static DWORD WINAPI wrong_thread(LPVOID unused) {
 (void)unused;return T60_material_enable(0)==-1 ? 0:1;
}
int main(int argc,char** argv) {
 CHECK(argc==3);SetDllDirectoryA(argv[1]);
 char path[1200];snprintf(path,sizeof(path),"%s/OgreMain_x64.dll",argv[1]);
 CHECK(LoadLibraryExA(path,NULL,LOAD_WITH_ALTERED_SEARCH_PATH)!=NULL);
 CHECK(T60_material_bind()==1);CHECK(T60_material_night_state()==0);CHECK(T60_material_night(1)==1);CHECK(T60_material_night_state()==1);CHECK(T60_material_night(1)==0);CHECK(T60_material_night(0)==1);CHECK(state.enabled==0);CHECK(og.root_singleton()==NULL);
 void* root=og.allocate(T60_ROOT_SIZE);CHECK(root);
 Str32 empty=str(""),log=str(argv[2]);CHECK(og.root_ctor(root,&empty,&empty,&log)==root);
 CHECK(og.root_singleton()==root);CHECK(og.root_renderer(root)==NULL);
 void* mm=og.material_manager();void* groups=og.groups();CHECK(mm && groups);
 Str32 group=str(GROUP);CHECK(!og.group_exists(groups,&group));og.group_create(groups,&group,1);
 Str32 name=str("Character_ABI_Original_Long_Name"),clone_name=str("JACK_T60_ABI_Cloned_Long_Name");
 Shared16 original={0},found={0},copy={0};
 CHECK(og.material_create(mm,&original,&name,&group,0,NULL,NULL)==&original);CHECK(original.rep && original.info);
 CHECK(equal(og.material_name(original.rep),"Character_ABI_Original_Long_Name"));
 int caught_cpp=0;
 __try {og.group_create(groups,&group,1);}
 __except(EXCEPTION_EXECUTE_HANDLER) {caught_cpp=(GetExceptionCode()==0xe06d7363);}
 CHECK(caught_cpp); /* actual Ogre C++ exception, not only a synthetic SEH fault */
 HANDLE thread=CreateThread(NULL,0,wrong_thread,NULL,0,NULL);CHECK(thread);
 CHECK(WaitForSingleObject(thread,5000)==WAIT_OBJECT_0);DWORD thread_result=1;
 CHECK(GetExitCodeThread(thread,&thread_result) && thread_result==0);CloseHandle(thread);
 CHECK(T60_material_enable(1)<0 && state.enabled==0);
 state.registered=1;CHECK(T60_material_enable(1)==1);
 CHECK(T60_material_apply((void*)1,"native-guard-test",0,1,"human_male.mesh")<0);
 CHECK(state.enabled==1); /* wrong body rejected before any entity dereference */
 CHECK(T60_material_apply((void*)1,"native-guard-test",0,1,"jack_t60_wear_v08.mesh")<0);
 CHECK(state.enabled==0 && strstr(state.error,"0xc0000005"));
 CHECK(T60_material_restore((void*)1)<0);
 CHECK(equal(og.material_group(original.rep),GROUP));
 CHECK(og.material_find(mm,&found,&name,&group)==&found && found.rep==original.rep);
 CHECK(og.material_clone(original.rep,&copy,&clone_name,1,&group)==&copy && copy.rep && copy.rep!=original.rep);
 CHECK(equal(og.material_name(copy.rep),"JACK_T60_ABI_Cloned_Long_Name"));
 CHECK(og.tech_count(original.rep)==og.tech_count(copy.rep));
 if(!og.tech_count(original.rep))CHECK(og.tech_create(original.rep));
 void* tech=og.tech_get(original.rep,0);if(!og.pass_count(tech))CHECK(og.pass_create(tech));
 void* pass=og.pass_get(tech,0);CHECK(pass);
 void* unit=og.unit_create(pass);CHECK(unit);Str32 unit_name=str("normalMap");og.unit_set_name(unit,&unit_name);
 CHECK(equal(og.unit_name(unit),"normalMap"));
 Str32 texture=str("T60_ABI_not_loaded_texture.dds");og.unit_set_texture(unit,&texture,2);
 CHECK(equal(og.unit_texture(unit),"T60_ABI_not_loaded_texture.dds"));
 og.material_copy(original.rep,&copy);
 void* cpass=og.pass_get(og.tech_get(copy.rep,0),0);
 CHECK(og.unit_count(cpass)==og.unit_count(pass));
 CHECK(equal(og.unit_texture(og.unit_get(cpass,og.unit_count(cpass)-1)),"T60_ABI_not_loaded_texture.dds"));
 CHECK(equal(og.material_name(original.rep),"Character_ABI_Original_Long_Name"));
 printf("REAL_OGRE_ABI_PASS: exact DLL hash, %u-byte Root, string SSO/heap views, engine allocation, member sret, Material create/find/clone/copy, techniques/passes/texture units, foreign-thread refusal, disabled/body gates, SEH containment; no renderer or game process\n",T60_ROOT_SIZE);
 fflush(stdout);
 /* Returned handles intentionally remain owned until this test process exits;
  * do not tear the engine down while those handles are retained. */
 return 0;
}
#endif
