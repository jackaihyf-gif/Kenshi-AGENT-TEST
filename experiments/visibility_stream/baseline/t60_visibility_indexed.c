/* Exact-build GUI-thread clothing suppression; preserves item ownership/stats.
 * Map node layout and category/entity fields audited in buildAttachments and
 * AppearanceHuman::setAttachmentsVisible. No retained pointer is dereferenced
 * unless it is present in the current live attachment map. */
#include "../../runtime/t60_attachment_compat_v083.c"
typedef void (*BoolSet)(void*,unsigned char);
typedef unsigned char (*BoolGet)(void*);
typedef struct {void* object;void* entity;int category;unsigned char visible;} Snap;
typedef struct {char owner[160];void* appearance;void* body;unsigned char parts,hide;int count;Snap snaps[128];} Record;
static Record records[16];static DWORD thread_id;
static BoolSet visible_set,clothes_set,parts_set;static BoolGet visible_get;
static int ready_api;
typedef int (*InstallHook)(void*,void*,void**);
typedef void (*QueueUpdate)(void*,void*,void*,const void*);
static QueueUpdate queue_update;
static volatile LONG64 suppressed_draws;
static SRWLOCK filter_lock=SRWLOCK_INIT;
typedef struct {void* appearance;void* hidden[128];int n;ULONGLONG expires;} Filter;
static Filter filters[16];
static int weapon_category(int n){return n==2||n==107;}
/* GUI writes and render readers share the original filter_lock. No entity
 * pointer is dereferenced. Membership changes rebuild; TTL refreshes do not. */
typedef struct {void* entity;unsigned short owners;} FilterIndex;
static FilterIndex filter_index[8192];
static unsigned index_slot(void* entity){
 uintptr_t key=(uintptr_t)entity;key^=key>>33;key*=0xff51afd7ed558ccdULL;key^=key>>33;
 return (unsigned)key&8191;
}
static void rebuild_index(void){
 memset(filter_index,0,sizeof(filter_index));
 for(unsigned owner=0;owner<16;owner++)if(filters[owner].appearance)
  for(int i=0;i<filters[owner].n;i++){
   void* entity=filters[owner].hidden[i];if(!entity)continue;
   unsigned slot=index_slot(entity);
   while(filter_index[slot].entity&&filter_index[slot].entity!=entity)slot=(slot+1)&8191;
   filter_index[slot].entity=entity;filter_index[slot].owners|=(unsigned short)(1u<<owner);
  }
}
static int suppressed(void* entity){
 int result=0;if(!entity)return 0;AcquireSRWLockShared(&filter_lock);
 unsigned slot=index_slot(entity),mask=0;
 for(unsigned steps=0;steps<8192;steps++){
  if(!filter_index[slot].entity)break;
  if(filter_index[slot].entity==entity){mask=filter_index[slot].owners;break;}
  slot=(slot+1)&8191;
 }
 if(mask){ULONGLONG now=GetTickCount64();
  for(unsigned owner=0;owner<16;owner++)if((mask&(1u<<owner))&&filters[owner].appearance&&now<filters[owner].expires){result=1;break;}
 }
 ReleaseSRWLockShared(&filter_lock);return result;
}
static void filtered_queue(void* entity,void* queue,void* camera,const void* lod_camera){
 if(suppressed(entity)){InterlockedIncrement64(&suppressed_draws);return;}
 queue_update(entity,queue,camera,lod_camera);
}
static void* implementation(void* p){
 for(int i=0;p&&i<8;i++){
  unsigned char* q=p;
  if(q[0]==0xff&&q[1]==0x25)p=*(void**)(q+6+*(int32_t*)(q+2));
  else if(q[0]==0xe9)p=q+5+*(int32_t*)(q+1);
  else break;
 }
 return p;
}
static void cache_filter(Record* r,int clear){
 Filter replacement={0};
 if(!clear){replacement.appearance=r->appearance;replacement.expires=GetTickCount64()+2000;
  for(int i=0;i<r->count;i++)if(!weapon_category(r->snaps[i].category))replacement.hidden[replacement.n++]=r->snaps[i].entity;
 }
 AcquireSRWLockExclusive(&filter_lock);
 Filter* f=&filters[r-records];
 int changed=f->appearance!=replacement.appearance||f->n!=replacement.n||memcmp(f->hidden,replacement.hidden,(size_t)replacement.n*sizeof(void*));
 *f=replacement;if(changed)rebuild_index();
 ReleaseSRWLockExclusive(&filter_lock);
}
static void filtered_visible(void* entity,unsigned char show){
 if(show&&suppressed(entity))show=0;
 visible_set(entity,show);
}
static int setup(void){
 if(bind()!=1)return -2;
 if(!thread_id)thread_id=GetCurrentThreadId();if(thread_id!=GetCurrentThreadId())return -3;
 if(ready_api)return 0;
 HMODULE og=GetModuleHandleA("OgreMain_x64.dll"),lib=GetModuleHandleA("KenshiLib.dll");
 visible_set=(BoolSet)(uintptr_t)GetProcAddress(og,"?setVisible@MovableObject@Ogre@@QEAAX_N@Z");
 visible_get=(BoolGet)(uintptr_t)GetProcAddress(og,"?getVisible@MovableObject@Ogre@@QEBA_NXZ");
 clothes_set=(BoolSet)(uintptr_t)GetProcAddress(lib,"?_NV_setAttachmentsVisible@AppearanceHuman@@QEAAX_N@Z");
 parts_set=(BoolSet)(uintptr_t)GetProcAddress(lib,"?setHiddenPartsEnabled@AppearanceHuman@@QEAAX_N@Z");
 if(!visible_set||!visible_get||!clothes_set||!parts_set)return -4;
 InstallHook hook=(InstallHook)(uintptr_t)GetProcAddress(lib,"?AddHook@KenshiLib@@YA?AW4HookStatus@1@PEAX0PEAPEAX@Z");
 if(!hook)return -13;
 HMODULE self;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(const char*)&setup,&self))return -14;
 if(hook(implementation((void*)visible_set),(void*)&filtered_visible,(void**)&visible_set)!=0)return -15;
 void* queue=(void*)(uintptr_t)GetProcAddress(og,"?_updateRenderQueue@Entity@Ogre@@UEAAXPEAVRenderQueue@2@PEAVCamera@2@PEBV42@@Z");
 if(!queue||hook(implementation(queue),(void*)&filtered_queue,(void**)&queue_update)!=0)return -16;
 ready_api=1;return 0;
}
static int collect(char* a,Snap* out){
 size_t bucket_count=*(size_t*)(a+0x30),index=*(size_t*)(a+0x28);void** buckets=*(void***)(a+0x48);
 char* node=bucket_count&&buckets?buckets[index]:NULL;int count=0,visited=0;
 while(node){
  if(++visited>128)return -5;char* obj=*(char**)(node+0x38);if(!obj)return -6;
  int type=*(int*)(obj+8);void* entity=*(void**)(obj+0x80);
  if((type==0||type==1)&&entity){out[count++]=(Snap){obj,entity,*(int*)(obj+0x60),visible_get(entity)};}
  node=*(char**)node;
 }
 return count;
}
static Record* record(void* a,const char* owner,int create){
 Record* empty=NULL;for(int i=0;i<16;i++){
  if(records[i].appearance==a&&!strcmp(records[i].owner,owner))return &records[i];
  if(!records[i].appearance&&!empty)empty=&records[i];
 }
 if(create&&empty){memset(empty,0,sizeof(*empty));snprintf(empty->owner,sizeof(empty->owner),"%s",owner);empty->appearance=a;empty->parts=((unsigned char*)a)[0x1b8];empty->hide=((unsigned char*)a)[0x181];return empty;}
 return NULL;
}
API int T60_visibility_begin(void* a,const char* owner){
 if(!a||!owner||strlen(owner)>=160)return -1;
 __try{int e=setup();if(e)return e;Record* r=record(a,owner,1);if(!r)return -7;cache_filter(r,0);parts_set(a,0);return 0;}
 __except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
API int T60_visibility_tick(void* appearance,const char* owner,char* output,size_t capacity){
 if(!appearance||!owner||!output||capacity<256)return -1;
 __try{
  int e=setup();if(e)return e;char* a=appearance;if(a[0xe8]||a[0x143]||!*(void**)(a+0xd8))return -12;
  Record* r=record(a,owner,0);if(!r)return -9;
  Snap live[128];int n=collect(a,live);if(n<0)return n;int refresh=r->body!=*(void**)(a+0xd8);
  Snap keep[128];int keep_n=0;
  for(int i=0;i<n;i++){
   int found=-1;for(int j=0;j<r->count;j++)if(live[i].object==r->snaps[j].object&&live[i].entity==r->snaps[j].entity){found=j;break;}
   keep[keep_n++]=found>=0?r->snaps[found]:live[i];if(found<0&&!weapon_category(live[i].category))refresh=1;
  }
  memcpy(r->snaps,keep,keep_n*sizeof(Snap));r->count=keep_n;r->body=*(void**)(a+0xd8);
  cache_filter(r,0);
  /* T60's private shader ignores vest/hair layers. Leave the engine's global
   * attachment flag and all weapon textures untouched. */
  parts_set(a,0);int hidden=0,weapons=0;
  for(int i=0;i<n;i++){
   if(weapon_category(live[i].category)){weapons+=visible_get(live[i].entity)!=0;continue;}
   visible_set(live[i].entity,0);hidden++;
  }
  snprintf(output,capacity,"hidden=%d visibleWeapons=%d hiddenParts=%u refresh=%d tracked=%d",hidden,weapons,(unsigned char)a[0x1b8],refresh,r->count);
  return hidden;
 }__except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
API int T60_visibility_end(void* appearance,const char* owner){
 if(!appearance||!owner)return -1;
 __try{
  int e=setup();if(e)return e;Record* r=record(appearance,owner,0);if(!r)return 0;
  char* a=appearance;if(a[0xe8]||a[0x143])return -12;
  cache_filter(r,1);
  clothes_set(a,r->hide?0:1);a[0x181]=r->hide;parts_set(a,r->parts);
  Snap live[128];int n=collect(a,live);if(n<0)return n;
  for(int i=0;i<n;i++)for(int j=0;j<r->count;j++)if(live[i].object==r->snaps[j].object&&live[i].entity==r->snaps[j].entity){visible_set(live[i].entity,r->snaps[j].visible);break;}
  memset(r,0,sizeof(*r));return 0;
 }__except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
API int T60_visibility_forget(void){int e=setup();if(e)return e;AcquireSRWLockExclusive(&filter_lock);memset(filters,0,sizeof(filters));rebuild_index();ReleaseSRWLockExclusive(&filter_lock);memset(records,0,sizeof(records));return 0;}
API int T60_visibility_ready(void){return setup();}
API int T60_visibility_dirty(void* a,const char* owner){int e=setup();if(e)return e;Record* r=record(a,owner,0);if(r)r->body=NULL;return 0;}
API int T60_visibility_status(void* a,char* output,size_t capacity){
 if(!a||!output||capacity<16384)return -1;
 __try{int e=setup();if(e)return e;Snap live[128];int n=collect(a,live);if(n<0)return n;
  size_t u=snprintf(output,capacity,"{\"hidden_parts\":%u,\"hide_attachments\":%u,\"suppressed_draws\":%llu,\"entities\":[",((unsigned char*)a)[0x1b8],((unsigned char*)a)[0x181],(unsigned long long)InterlockedCompareExchange64(&suppressed_draws,0,0));
  for(int i=0;i<n;i++)u+=snprintf(output+u,capacity-u,"%s{\"object\":\"%p\",\"entity\":\"%p\",\"category\":%d,\"visible\":%s,\"render_suppressed\":%s}",i?",":"",live[i].object,live[i].entity,live[i].category,live[i].visible?"true":"false",suppressed(live[i].entity)?"true":"false");
  snprintf(output+u,capacity-u,"]}");return n;
 }__except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
