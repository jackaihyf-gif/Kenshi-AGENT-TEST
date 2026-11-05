#ifdef NDEBUG
#error Tests require active assertions
#endif
#include "visibility_lifecycle.c"
#include <assert.h>
static unsigned char last_show; static int visible_calls,attach_calls,dtor_calls;
static void fake_visible(void* p,unsigned char show){(void)p;last_show=show;visible_calls++;}
static unsigned char fake_get(void* p){(void)p;return 1;}
static void fake_attach(void* a,void* o){(void)a;(void)o;attach_calls++;}
static void fake_dtor(void* p){(void)p;dtor_calls++;}
static void* destroy_during_end; static void fake_parts(void* p,unsigned char x){(void)p;(void)x;if(destroy_during_end){void* e=destroy_during_end;destroy_during_end=NULL;entity_dtor_hook(e);}}
int main(void){char appearance[0x200]={0},object[0xa0]={0},weapon[0xa0]={0},entity[8]={0},weapon_entity[8]={0};char node[0x40]={0};void* buckets[1]={node};void* ep=entity;memcpy(object+0x80,&ep,8);ep=weapon_entity;memcpy(weapon+0x80,&ep,8);*(int*)(weapon+0x60)=2;
 visible_set=fake_visible;visible_get=fake_get;attach_original=fake_attach;entity_dtor_original=fake_dtor;appearance_dtor_original=fake_dtor;parts_set=fake_parts;clothes_set=fake_parts;thread_id=GetCurrentThreadId();setup_state=1;
 records[0].appearance=appearance;records[0].active=1;strcpy(records[0].owner,"test");
 LONG64 before=rebuild_calls;entity_dtor_hook((void*)0x9870);appearance_dtor_hook((void*)0x8760);filtered_visible((void*)0x7650,1);assert(rebuild_calls==before);attach_hook(appearance,object);assert(attach_calls==1&&suppressed(entity)&&last_show==0);uint64_t old=records[0].snaps[0].serial;before=rebuild_calls;attach_hook(appearance,object);assert(records[0].count==1&&records[0].snaps[0].serial==old&&before==rebuild_calls);Sleep(2100);assert(suppressed(entity));filtered_visible(entity,1);assert(last_show==0&&records[0].snaps[0].visible==1);attach_hook(appearance,weapon);assert(!suppressed(weapon_entity));
 records[0].active=0;assert(!suppressed(entity));entity_dtor_hook(entity);assert(!suppressed(entity)&&records[0].count==0);records[0].active=1;attach_hook(appearance,object);assert(suppressed(entity)&&records[0].snaps[0].serial!=old);
 records[1].appearance=(void*)0x3130;records[1].active=1;strcpy(records[1].owner,"other");attach_hook(records[1].appearance,object);assert(suppressed(entity));filtered_visible(entity,1);*(void**)(node+0x38)=object;*(size_t*)(appearance+0x30)=1;*(size_t*)(appearance+0x28)=0;*(void***)(appearance+0x48)=buckets;assert(T60_visibility_end(appearance,"test")==0);assert(suppressed(entity)&&last_show==0&&!records[0].appearance);appearance_dtor_hook((void*)0x3130);assert(!suppressed(entity));
 records[0].appearance=appearance;records[0].active=1;strcpy(records[0].owner,"test");attach_hook(appearance,object);appearance_dtor_hook(appearance);assert(!suppressed(entity)&&!records[0].appearance);
 records[0].appearance=appearance;records[0].active=1;strcpy(records[0].owner,"test");attach_hook(appearance,object);destroy_during_end=entity;assert(T60_visibility_end(appearance,"test")==0);assert(!suppressed(entity)&&records[0].count==0);records[0].appearance=appearance;records[0].active=1;attach_hook(appearance,object);assert(T60_visibility_forget()==0&&!suppressed(entity));printf("PASS attach intent weapon >2s destruction address-reuse end appearance-dtor epoch\n");return 0;}
