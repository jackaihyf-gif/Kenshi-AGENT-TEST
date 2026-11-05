/* Generated verbatim slices; no engine access, setup, collection or exports. */
#include <stdint.h>
#include <string.h>
typedef void (*BoolSet)(void*,unsigned char);
typedef unsigned char (*BoolGet)(void*);
typedef struct {void* object;void* entity;int category;unsigned char visible;} Snap;
typedef struct {char owner[160];void* appearance;void* body;unsigned char parts,hide;int count;Snap snaps[128];} Record;
static Record records[16];static DWORD thread_id;
static BoolSet visible_set,clothes_set,parts_set;static BoolGet visible_get;
static int ready_api;

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
