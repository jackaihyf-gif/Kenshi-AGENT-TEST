#ifdef NDEBUG
#error Material binding tests require active assertions
#endif
#include <assert.h>
#include <windows.h>
#include <string.h>
static int prior_bridge,ogre_queries;
static HMODULE WINAPI synthetic_module(LPCSTR name){
 if(!strcmp(name,"T60MaterialBridge_v091.dll"))return prior_bridge==1?(HMODULE)1:NULL;
 if(!strcmp(name,"T60MaterialBridge_v091_bindingfix_20261106.dll"))return prior_bridge==2?(HMODULE)2:NULL;
 ogre_queries++;return NULL;
}
#define GetModuleHandleA synthetic_module
#include "material_bridge.c"

typedef struct {Str32 name,texture;} Unit;
typedef struct {Str32 program;Unit units[3];int count;} Pass;
static int body,sub,material,technique;
static Shared16 selected;
static Pass pass;
static int entity_reads,texture_writes,clones,compiles;
static int ignore_write,name_writes,ignore_name;
static size_t entity_count(void* p){assert(p==&body);entity_reads++;return 1;}
static void* entity_sub(void* p,size_t n){assert(p==&body&&n==0);return &sub;}
static const Shared16* sub_material(void* p){assert(p==&sub);return &selected;}
static unsigned short tech_count(void* p){assert(p==&material);return 1;}
static void* tech_get(void* p,unsigned short n){assert(p==&material&&n==0);return &technique;}
static unsigned short pass_count(void* p){assert(p==&technique);return 1;}
static void* pass_get(void* p,unsigned short n){assert(p==&technique&&n==0);return &pass;}
static const Str32* pass_fp(void* p){assert(p==&pass);return &pass.program;}
static unsigned short unit_count(void* p){assert(p==&pass);return (unsigned short)pass.count;}
static void* unit_get(void* p,size_t n){assert(p==&pass&&n<(size_t)pass.count);return &pass.units[n];}
static const Str32* unit_name(void* p){return &((Unit*)p)->name;}
static const Str32* unit_texture(void* p){return &((Unit*)p)->texture;}
static void unit_set_texture(void* p,const Str32* name,int type){
 assert(type==2);texture_writes++;if(!ignore_write)((Unit*)p)->texture=*name;
}
static void unit_set_name(void* p,const Str32* name){name_writes++;if(!ignore_name)((Unit*)p)->name=*name;}
static Shared16* clone_forbidden(void* a,Shared16* b,const Str32* c,unsigned char d,const Str32* e){
 (void)a;(void)b;(void)c;(void)d;(void)e;clones++;assert(0);return NULL;
}
static void compile_forbidden(void* a,unsigned char b){(void)a;(void)b;compiles++;assert(0);}
static void reset_fixture(void){
 memset(&state,0,sizeof(state));memset(&og,0,sizeof(og));memset(&pass,0,sizeof(pass));
 state.thread=GetCurrentThreadId();state.bound=state.registered=state.enabled=1;state.slots=1;
 strcpy(state.slot[0].owner,"mock-owner");state.slot[0].modified.rep=&material;
 selected.rep=&material;binding_checks=binding_repairs=binding_unexpected_drifts=0;night_mode=0;
 entity_reads=texture_writes=clones=compiles=ignore_write=name_writes=ignore_name=0;
 pass.program=str(DAY_PROGRAM);pass.count=3;
 pass.units[0]=(Unit){str("diffuseMap"),str("t60_source_d.dds")};
 pass.units[1]=(Unit){str("normalMap"),str(NORMAL)};
 pass.units[2]=(Unit){str("bodyBlendNormal"),str("unchanged_blend.dds")};
 og.entity_count=entity_count;og.entity_sub=entity_sub;og.sub_material=sub_material;
 og.tech_count=tech_count;og.tech_get=tech_get;og.pass_count=pass_count;og.pass_get=pass_get;
 og.pass_fp=pass_fp;og.unit_count=unit_count;og.unit_get=unit_get;
 og.unit_name=unit_name;og.unit_texture=unit_texture;og.unit_set_texture=unit_set_texture;og.unit_set_name=unit_set_name;
 og.material_clone=clone_forbidden;og.material_load=compile_forbidden;
}
static int apply(void){return T60_material_apply(&body,"mock-owner",0,2,"jack_t60_wear_v08.mesh");}
static void prepare(void){assert(isolate_normal_unit(&pass.units[1],1)==1);}
static void engine_skin_update(const char* normal){
 for(int i=0;i<pass.count;i++)if(equal(&pass.units[i].name,"normalMap"))pass.units[i].texture=str(normal);
}
int main(void){
 int sentinel=0;assert(++sentinel==1);
 for(int previous=1;previous<=2;previous++){
  prior_bridge=previous;ogre_queries=0;assert(T60_material_bind()<0);
  assert(strstr(state.error,"Cold restart required")&&ogre_queries==0);
 }
 prior_bridge=0;
 reset_fixture();prepare();assert(equal(&pass.units[1].name,PRIVATE_NORMAL));
 assert(texture_writes==1&&name_writes==1&&pass.count==3);
 assert(apply()==0&&binding_checks==1);
 for(int i=0;i<1000;i++){
  engine_skin_update(i%2?"human_male_n.dds":"bone_male_n.dds");
  assert(apply()==0&&equal(&pass.units[1].texture,NORMAL));
 }
 assert(texture_writes==1&&name_writes==1&&binding_repairs==0&&binding_unexpected_drifts==0);
 assert(state.slots==1&&clones==0&&compiles==0);
 assert(equal(&pass.units[0].texture,"t60_source_d.dds"));
 assert(equal(&pass.units[2].texture,"unchanged_blend.dds"));
 char status[512];assert(T60_material_binding_status(status,sizeof(status))>0);
 assert(strstr(status,"\"repairs\":0")&&strstr(status,"\"unexpected_drifts\":0"));
 assert(T60_material_binding_status(status,8)<0);
 int before=entity_reads;
 assert(T60_material_apply(&body,"mock-owner",0,3,"human_male.mesh")<0);
 assert(entity_reads==before);state.thread=GetCurrentThreadId()+1;assert(apply()<0);
 assert(entity_reads==before);state.thread=GetCurrentThreadId();state.enabled=0;
 assert(apply()==0&&entity_reads==before);
 reset_fixture();prepare();night_mode=1;pass.program=str(PROGRAM);assert(apply()==0);
 reset_fixture();prepare();pass.program=str("Character_FP");assert(apply()<0&&state.enabled==0);
 reset_fixture();prepare();pass.units[1].name=str("missingNormal");assert(apply()<0);
 reset_fixture();prepare();pass.units[2].name=str(PRIVATE_NORMAL);assert(apply()<0);
 reset_fixture();prepare();pass.units[2].name=str("normalMap");assert(apply()<0);
 reset_fixture();prepare();pass.units[1].texture=str("bone_male_n.dds");
 assert(apply()<0&&state.enabled==0&&binding_unexpected_drifts==1&&texture_writes==1);
 reset_fixture();ignore_write=1;pass.units[1].texture=str("bone_male_n.dds");
 assert(isolate_normal_unit(&pass.units[1],1)<0);
 reset_fixture();ignore_name=1;assert(isolate_normal_unit(&pass.units[1],1)<0);
 reset_fixture();assert(isolate_normal_unit(&pass.units[1],0)<0&&texture_writes==0);
 assert(sentinel==1);
 puts("MATERIAL_BINDING_MOCK_PASS: sentinel, two prior bridge guards, isolated s1 name, 1000 simulated race updates, no periodic writes/clone/compile/growth, day/night and gates, unexpected drift fails closed");
 return 0;
}
