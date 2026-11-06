/* Experimental lifecycle filter. Not game verified. */
#include "t60_attachment_compat_v083.c"
typedef void (*BoolSet)(void*,unsigned char); typedef unsigned char (*BoolGet)(void*);
typedef void (*Unary)(void*); typedef void (*Attach)(void*,void*);
typedef void (*QueueUpdate)(void*,void*,void*,const void*); typedef int (*InstallHook)(void*,void*,void**);
typedef struct {void* object;void* entity;int category;unsigned char visible;uint64_t serial;} Snap;
typedef struct {char owner[160];void* appearance;void* body;unsigned char parts,hide,active,fault,dirty;int count;Snap snaps[128];} Record;
typedef struct {void* entity;unsigned short owners;} FilterIndex;
static Record records[16];static FilterIndex filter_index[8192];static SRWLOCK filter_lock=SRWLOCK_INIT;
static volatile LONG64 registration_count,unregistration_count,fault_count,rebuild_calls;static uint64_t next_serial;static DWORD thread_id;static int setup_state;static volatile LONG64 suppressed_draws;
static BoolSet visible_set,clothes_set,parts_set;static BoolGet visible_get;static QueueUpdate queue_update;
static Attach attach_original;static Unary entity_dtor_original,appearance_dtor_original;
static int weapon_category(int n){return n==2||n==107;}
static unsigned index_slot(void* entity){uintptr_t k=(uintptr_t)entity;k^=k>>33;k*=0xff51afd7ed558ccdULL;k^=k>>33;return (unsigned)k&8191;}
/* Caller holds exclusive lock. */
static void rebuild_index(void){InterlockedIncrement64(&rebuild_calls);memset(filter_index,0,sizeof(filter_index));for(unsigned j=0;j<16;j++)if(records[j].appearance)for(int i=0;i<records[j].count;i++){Snap* s=&records[j].snaps[i];if(!s->entity||weapon_category(s->category))continue;unsigned p=index_slot(s->entity);while(filter_index[p].entity&&filter_index[p].entity!=s->entity)p=(p+1)&8191;filter_index[p].entity=s->entity;filter_index[p].owners|=(unsigned short)(1u<<j);}}
static unsigned lookup_locked(void* e){if(!e)return 0;unsigned p=index_slot(e);for(unsigned n=0;n<8192;n++,p=(p+1)&8191){if(!filter_index[p].entity)return 0;if(filter_index[p].entity==e)return filter_index[p].owners;}return 0;}
static unsigned active_mask_locked(unsigned mask){for(unsigned j=0;j<16;j++)if((mask&(1u<<j))&&!records[j].active)mask&=~(1u<<j);return mask;}
static int suppressed(void* e){AcquireSRWLockShared(&filter_lock);int v=active_mask_locked(lookup_locked(e))!=0;ReleaseSRWLockShared(&filter_lock);return v;}
static void filtered_queue(void* e,void* q,void* c,const void* l){if(suppressed(e)){InterlockedIncrement64(&suppressed_draws);return;}queue_update(e,q,c,l);}
static void filtered_visible(void* e,unsigned char show){AcquireSRWLockShared(&filter_lock);unsigned mask=active_mask_locked(lookup_locked(e));ReleaseSRWLockShared(&filter_lock);if(!mask){visible_set(e,show);return;}AcquireSRWLockExclusive(&filter_lock);mask=active_mask_locked(lookup_locked(e));for(unsigned j=0;j<16;j++)if(mask&(1u<<j))for(int k=0;k<records[j].count;k++)if(records[j].snaps[k].entity==e)records[j].snaps[k].visible=show;ReleaseSRWLockExclusive(&filter_lock);visible_set(e,mask?0:show);}
static void remove_entity_locked(void* e){for(int j=0;j<16;j++){Record* r=&records[j];for(int k=0;k<r->count;)if(r->snaps[k].entity==e){r->snaps[k]=r->snaps[--r->count];InterlockedIncrement64(&unregistration_count);}else k++;}rebuild_index();}
static void entity_dtor_hook(void* e){AcquireSRWLockShared(&filter_lock);unsigned mask=lookup_locked(e);ReleaseSRWLockShared(&filter_lock);if(mask){AcquireSRWLockExclusive(&filter_lock);if(lookup_locked(e))remove_entity_locked(e);ReleaseSRWLockExclusive(&filter_lock);}entity_dtor_original(e);}
static void appearance_dtor_hook(void* a){int found=0;AcquireSRWLockShared(&filter_lock);for(int j=0;j<16;j++)if(records[j].appearance==a){found=1;break;}ReleaseSRWLockShared(&filter_lock);if(found){AcquireSRWLockExclusive(&filter_lock);int changed=0;for(int j=0;j<16;j++)if(records[j].appearance==a){InterlockedExchangeAdd64(&unregistration_count,records[j].count);memset(&records[j],0,sizeof(Record));changed=1;}if(changed)rebuild_index();ReleaseSRWLockExclusive(&filter_lock);}appearance_dtor_original(a);}
/* Existing pair is preserved: another attach is not a new allocation. */
static int register_locked(Record* r,void* o,void* e,int cat,unsigned char intent){for(int i=0;i<r->count;i++)if(r->snaps[i].object==o&&r->snaps[i].entity==e)return i;if(r->count>=128){if(!r->fault)InterlockedIncrement64(&fault_count);r->fault=1;return -1;}r->dirty=1;int i=r->count++;InterlockedIncrement64(&registration_count);r->snaps[i]=(Snap){o,e,cat,intent,++next_serial};if(!next_serial)r->snaps[i].serial=++next_serial;return i;}
static void attach_hook(void* a,void* object){void* e=NULL;int cat=0,type=-1,hide=0,interested=0;AcquireSRWLockShared(&filter_lock);for(int j=0;j<16;j++)if(records[j].appearance==a&&records[j].active){interested=1;break;}ReleaseSRWLockShared(&filter_lock);if(!interested){attach_original(a,object);return;}__try{type=*(int*)((char*)object+8);if(type==0||type==1){e=*(void**)((char*)object+0x80);cat=*(int*)((char*)object+0x60);}}__except(EXCEPTION_EXECUTE_HANDLER){e=NULL;}if(e&&!weapon_category(cat)){AcquireSRWLockExclusive(&filter_lock);int changed=0;for(int j=0;j<16;j++)if(records[j].appearance==a&&records[j].active){int count=records[j].count;if(register_locked(&records[j],object,e,cat,0)>=0)hide=1;if(records[j].count!=count)changed=1;}if(changed)rebuild_index();ReleaseSRWLockExclusive(&filter_lock);if(hide)visible_set(e,0);}attach_original(a,object);}
static void* implementation(void* p){for(int i=0;p&&i<8;i++){unsigned char* q=p;if(q[0]==0xff&&q[1]==0x25)p=*(void**)(q+6+*(int32_t*)(q+2));else if(q[0]==0xe9)p=q+5+*(int32_t*)(q+1);else break;}return p;}
static int setup(void){if(!thread_id)thread_id=GetCurrentThreadId();if(thread_id!=GetCurrentThreadId())return -3;if(setup_state)return setup_state==1?0:setup_state;setup_state=-20;if(bind()!=1)return setup_state=-2;
 HMODULE og=GetModuleHandleA("OgreMain_x64.dll"),lib=GetModuleHandleA("KenshiLib.dll"),self;char* base=(char*)GetModuleHandleA(NULL);if(!og||!lib)return setup_state=-4;
 visible_set=(BoolSet)GetProcAddress(og,"?setVisible@MovableObject@Ogre@@QEAAX_N@Z");visible_get=(BoolGet)GetProcAddress(og,"?getVisible@MovableObject@Ogre@@QEBA_NXZ");clothes_set=(BoolSet)GetProcAddress(lib,"?_NV_setAttachmentsVisible@AppearanceHuman@@QEAAX_N@Z");parts_set=(BoolSet)GetProcAddress(lib,"?setHiddenPartsEnabled@AppearanceHuman@@QEAAX_N@Z");
 void* att=implementation((void*)GetProcAddress(lib,"?attachEntity@AppearanceBase@@QEAAXPEAVAttachedObject@@@Z"));void* ad=implementation((void*)GetProcAddress(lib,"??1AppearanceBase@@UEAA@XZ"));void* ed=implementation((void*)GetProcAddress(og,"??1Entity@Ogre@@UEAA@XZ"));void* queue=implementation((void*)GetProcAddress(og,"?_updateRenderQueue@Entity@Ogre@@UEAAXPEAVRenderQueue@2@PEAVCamera@2@PEBV42@@Z"));InstallHook hook=(InstallHook)GetProcAddress(lib,"?AddHook@KenshiLib@@YA?AW4HookStatus@1@PEAX0PEAPEAX@Z");
 if(!visible_set||!visible_get||!clothes_set||!parts_set||!hook||!queue||!ed||att!=base+0x52c9f0||ad!=base+0x5317e0||ed!=(char*)og+0xc0860||memcmp(att,"\x48\x8b\xc4\x57\x41\x54\x41\x55",8)||memcmp(ad,"\x48\x89\x4c\x24\x08\x55\x56\x57",8)||memcmp(ed,"\x48\x89\x4c\x24\x08\x55\x56\x57",8))return setup_state=-4;
 if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(const char*)&setup,&self))return setup_state=-14;
 if(hook(implementation((void*)visible_set),(void*)filtered_visible,(void**)&visible_set)!=0)return setup_state=-15;
 if(hook(queue,(void*)filtered_queue,(void**)&queue_update)!=0)return setup_state=-16;
 if(hook(ed,(void*)entity_dtor_hook,(void**)&entity_dtor_original)!=0)return setup_state=-17;
 if(hook(ad,(void*)appearance_dtor_hook,(void**)&appearance_dtor_original)!=0)return setup_state=-18;
 if(hook(att,(void*)attach_hook,(void**)&attach_original)!=0)return setup_state=-19;
 setup_state=1;return 0;}

/* collect performs raw map traversal under the existing GUI stable gate. */
static int collect(char* a,Snap* out){size_t count=*(size_t*)(a+0x30),index=*(size_t*)(a+0x28);void** buckets=*(void***)(a+0x48);char* node=count&&buckets?buckets[index]:NULL;int n=0,visited=0;while(node){if(++visited>128)return -5;char* o=*(char**)(node+0x38);if(!o)return -6;int type=*(int*)(o+8);void* e=*(void**)(o+0x80);if((type==0||type==1)&&e)out[n++]=(Snap){o,e,*(int*)(o+0x60),0,0};node=*(char**)node;}return n;}
static int owner_index(void* a,const char* owner){for(int i=0;i<16;i++)if(records[i].appearance==a&&!strcmp(records[i].owner,owner))return i;return -1;}
API int T60_visibility_begin(void* a,const char* owner){if(!a||!owner||strlen(owner)>=160)return -1;__try{int err=setup();if(err)return err;char* p=a;if(p[0xe8]||p[0x143]||!*(void**)(p+0xd8))return -12;Snap live[128];int n=collect(p,live);if(n<0)return n;for(int i=0;i<n;i++)if(!weapon_category(live[i].category))live[i].visible=visible_get(live[i].entity);AcquireSRWLockExclusive(&filter_lock);int j=owner_index(a,owner);if(j<0){for(int k=0;k<16;k++)if(!records[k].appearance){j=k;break;}if(j<0){ReleaseSRWLockExclusive(&filter_lock);return -7;}Record* r=&records[j];memset(r,0,sizeof(*r));r->appearance=a;strcpy(r->owner,owner);r->parts=p[0x1b8];r->hide=p[0x181];r->active=1;for(int i=0;i<n;i++)if(!weapon_category(live[i].category))register_locked(r,live[i].object,live[i].entity,live[i].category,live[i].visible);rebuild_index();}ReleaseSRWLockExclusive(&filter_lock);parts_set(a,0);return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return -8;}}
API int T60_visibility_tick(void* a,const char* owner,char* output,size_t capacity){if(!a||!owner||!output||capacity<256)return -1;__try{int err=setup();if(err)return err;char* p=a;if(p[0xe8]||p[0x143]||!*(void**)(p+0xd8))return -12;Snap live[128],work[128];int n=collect(p,live),w=0,refresh=0,fault=0;if(n<0)return n;AcquireSRWLockExclusive(&filter_lock);int j=owner_index(a,owner);if(j>=0){Record* r=&records[j];fault=r->fault;refresh=r->dirty||r->body!=*(void**)(p+0xd8);r->dirty=0;r->body=*(void**)(p+0xd8);}if(j>=0&&records[j].active)for(int i=0;i<n;i++)for(int k=0;k<records[j].count;k++){Snap s=records[j].snaps[k];if(s.object==live[i].object&&s.entity==live[i].entity){work[w++]=s;break;}}ReleaseSRWLockExclusive(&filter_lock);if(j<0)return -9;if(fault)return -5;int hidden=0,weapons=0;for(int i=0;i<n;i++)if(weapon_category(live[i].category))weapons++;parts_set(a,0);for(int i=0;i<w;i++){if(weapon_category(work[i].category))continue;AcquireSRWLockShared(&filter_lock);int valid=0;j=owner_index(a,owner);if(j>=0&&records[j].active)for(int k=0;k<records[j].count;k++)if(records[j].snaps[k].serial==work[i].serial&&records[j].snaps[k].entity==work[i].entity){valid=1;break;}ReleaseSRWLockShared(&filter_lock);if(valid){visible_set(work[i].entity,0);hidden++;}}snprintf(output,capacity,"hidden=%d visibleWeapons=%d hiddenParts=%u refresh=%d tracked=%d",hidden,weapons,p[0x1b8],refresh,w);return hidden;}__except(EXCEPTION_EXECUTE_HANDLER){return -8;}}
API int T60_visibility_end(void* a,const char* owner){if(!a||!owner)return -1;__try{int err=setup();if(err)return err;char* p=a;if(p[0xe8]||p[0x143])return -12;Snap live[128],work[128];int n=collect(p,live),w=0;if(n<0)return n;unsigned char parts,hide;AcquireSRWLockExclusive(&filter_lock);int j=owner_index(a,owner);if(j<0){ReleaseSRWLockExclusive(&filter_lock);return 0;}Record* r=&records[j];r->active=0;parts=r->parts;hide=r->hide;for(int i=0;i<n;i++)for(int k=0;k<r->count;k++)if(r->snaps[k].object==live[i].object&&r->snaps[k].entity==live[i].entity){work[w++]=r->snaps[k];break;}rebuild_index();ReleaseSRWLockExclusive(&filter_lock);clothes_set(a,hide?0:1);p[0x181]=hide;parts_set(a,parts);for(int i=0;i<w;i++){AcquireSRWLockShared(&filter_lock);int valid=0;j=owner_index(a,owner);if(j>=0)for(int k=0;k<records[j].count;k++)if(records[j].snaps[k].serial==work[i].serial&&records[j].snaps[k].entity==work[i].entity){valid=1;break;}ReleaseSRWLockShared(&filter_lock);if(valid)visible_set(work[i].entity,suppressed(work[i].entity)?0:work[i].visible);}AcquireSRWLockExclusive(&filter_lock);j=owner_index(a,owner);if(j>=0){InterlockedExchangeAdd64(&unregistration_count,records[j].count);memset(&records[j],0,sizeof(Record));}rebuild_index();ReleaseSRWLockExclusive(&filter_lock);return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return -8;}}
API int T60_visibility_forget(void){int e=setup();if(e)return e;AcquireSRWLockExclusive(&filter_lock);for(int j=0;j<16;j++)InterlockedExchangeAdd64(&unregistration_count,records[j].count);memset(records,0,sizeof(records));rebuild_index();ReleaseSRWLockExclusive(&filter_lock);return 0;}
API int T60_visibility_ready(void){return setup();}
API int T60_visibility_dirty(void* a,const char* owner){int e=setup();if(e)return e;AcquireSRWLockExclusive(&filter_lock);int j=owner_index(a,owner);if(j>=0){records[j].body=NULL;records[j].dirty=1;}ReleaseSRWLockExclusive(&filter_lock);return 0;}

API int T60_visibility_status(void* a,char* output,size_t capacity){
 if(!a||!output||capacity<16384)return -1;
 __try{
  int e=setup();if(e)return e;Snap live[128];int n=collect(a,live);if(n<0)return n;
  size_t u=0;int unknown=0;
  AcquireSRWLockShared(&filter_lock);
  for(int i=0;i<n;i++)if(!weapon_category(live[i].category)){
   int known=0;
   for(int j=0;j<16&&!known;j++)if(records[j].appearance==a&&records[j].active)
    for(int k=0;k<records[j].count;k++)if(records[j].snaps[k].object==live[i].object&&records[j].snaps[k].entity==live[i].entity){known=1;break;}
   if(!known)unknown++;
  }
  ReleaseSRWLockShared(&filter_lock);
#define APPEND(...) do{int wrote=snprintf(output+u,capacity-u,__VA_ARGS__);if(wrote<0||(size_t)wrote>=capacity-u)return -10;u+=(size_t)wrote;}while(0)
  APPEND("{\"hidden_parts\":%u,\"hide_attachments\":%u,\"suppressed_draws\":%llu,\"registrations\":%llu,\"unregistrations\":%llu,\"faults\":%llu,\"unregistered_live\":%d,\"entities\":[",
   ((unsigned char*)a)[0x1b8],((unsigned char*)a)[0x181],
   (unsigned long long)InterlockedCompareExchange64(&suppressed_draws,0,0),
   (unsigned long long)InterlockedCompareExchange64(&registration_count,0,0),
   (unsigned long long)InterlockedCompareExchange64(&unregistration_count,0,0),
   (unsigned long long)InterlockedCompareExchange64(&fault_count,0,0),unknown);
  for(int i=0;i<n;i++){
   APPEND("%s{\"object\":\"%p\",\"entity\":\"%p\",\"category\":%d,\"visible\":%s,\"render_suppressed\":%s}",i?",":"",live[i].object,live[i].entity,live[i].category,visible_get(live[i].entity)?"true":"false",suppressed(live[i].entity)?"true":"false");
  }
  APPEND("]}");
#undef APPEND
  return n;
 }__except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
