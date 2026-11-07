#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wincrypt.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#define API __declspec(dllexport)
typedef unsigned char (*SaveFile)(void*,const void*);
typedef struct {union {char small[16];const char*data;} storage;unsigned long long length,capacity;} NativeString;
typedef void* (*Alloc)(size_t);typedef void* (*Ctor)(void*);typedef unsigned char (*Update)(void*,const void*,unsigned char);typedef int (*Epoch)(unsigned long long*,long*,unsigned long*);
typedef struct {unsigned long long id,epoch;void *app,*character,*source,*copy,*scratch;unsigned validity;void* container;unsigned char standalone,readonly;unsigned copy_validity;void* copy_container;unsigned char copy_standalone,copy_readonly;int state,copy_ok;unsigned long long readers;} Snapshot;
static SaveFile saveFile;static void*saveTarget;static unsigned savedMask;
static unsigned objects, objectAttempts;
static unsigned long long privateCreated,privateDeleted,privateRetained,privateCompleted,privateQuarantine;static LONG trialBusy;static int releaseStopped;
static Snapshot slots[2];static unsigned long long next_id;static unsigned attempts;static LONG gui;static int prepared,ready;static void *ctorTarget;static Ctor ctor;static Update update;static Alloc allocfn;static Epoch epochfn;
static int isgui(void){return gui&&(LONG)GetCurrentThreadId()==gui;}
static int hash_ok(void){char path[MAX_PATH];if(!GetModuleFileNameA(NULL,path,MAX_PATH))return 0;FILE*f=fopen(path,"rb");if(!f)return 0;HCRYPTPROV p=0;HCRYPTHASH h=0;BYTE buf[65536],hash[32];DWORD len=32;int ok=CryptAcquireContextA(&p,0,0,PROV_RSA_AES,CRYPT_VERIFYCONTEXT)&&CryptCreateHash(p,CALG_SHA_256,0,0,&h);size_t n;while(ok&&(n=fread(buf,1,sizeof buf,f))>0)ok=CryptHashData(h,buf,(DWORD)n,0);if(ferror(f))ok=0;fclose(f);if(ok)ok=CryptGetHashParam(h,HP_HASHVAL,hash,&len,0)&&len==32;if(h)CryptDestroyHash(h);if(p)CryptReleaseContext(p,0);const BYTE e[]={0x50,0x4b,0x36,0x2c,0xde,0x85,0x0d,0x56,0xaf,0xb1,0xce,0xa6,0xf5,0xb7,0xb0,0xee,0x01,0x4d,0x9d,0xd7,0xb4,0x7e,0x18,0x85,0x99,0xd9,0x1c,0x80,0x45,0x02,0xcd,0x3e};return ok&&!memcmp(hash,e,32);}
/* KenshiLib exports are import-indirect jump stubs. Read target, do not execute it. */
static void* target(HMODULE lib,const char*name){__try{unsigned char*s=(void*)GetProcAddress(lib,name);int32_t disp;if(!s||s[0]!=0xff||s[1]!=0x25)return NULL;memcpy(&disp,s+2,4);return *(void**)(s+6+disp);}__except(EXCEPTION_EXECUTE_HANDLER){return NULL;}}
static int T60_snapshot_prepare(unsigned long long*ctorRva){if(!ctorRva)return -1;*ctorRva=0;LONG t=(LONG)GetCurrentThreadId(),g=InterlockedCompareExchange(&gui,t,0);if(g&&g!=t)return -2;if(!hash_ok())return -3;HMODULE exe=GetModuleHandleA(NULL),lib=GetModuleHandleA("KenshiLib.dll"),ogre=GetModuleHandleA("OgreMain_x64.dll"),probe=GetModuleHandleA("player_epoch_probe.dll");if(!lib||!ogre||!probe)return -4;void*u=target(lib,"?updateFrom@GameData@@QEAA_NPEBV1@_N@Z"),*ser=target(lib,"?serialise@AppearanceBase@@QEAAXPEAVGameData@@@Z");ctorTarget=target(lib,"?_CONSTRUCTOR@GameDataCopyStandalone@@QEAAPEAV1@XZ");saveTarget=target(lib,"?saveToFile@GameData@@QEAA_NAEBV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@@Z");allocfn=(Alloc)GetProcAddress(ogre,"??2?$AllocatedObject@V?$CategorisedAllocPolicy@$0A@@Ogre@@@Ogre@@SAPEAX_K@Z");epochfn=(Epoch)GetProcAddress(probe,"T60_player_epoch_probe_snapshot");static const unsigned char uc[]={0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x8d,0x6c,0x24};
 static const unsigned char cc[]={0x40,0x53,0x48,0x83,0xec,0x20,0x48,0x8b,0xd9,0xe8,0x26,0xd8,0xf5,0xff,0x4c,0x8d};
 static const unsigned char sc[]={0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x48,0x8d,0xac,0x24,0xf0,0xfe,0xff,0xff};
 if(u!=(char*)exe+0x2e6450||ser!=(char*)exe+0x534d50||ctorTarget!=(char*)exe+0xb65c0||saveTarget!=(char*)exe+0x6c05e0||!allocfn||!epochfn)return -5;
 if(memcmp(u,uc,sizeof uc)||memcmp(ctorTarget,cc,sizeof cc)||memcmp(saveTarget,sc,sizeof sc))return -5;MEMORY_BASIC_INFORMATION mbi;if(!VirtualQuery(ctorTarget,&mbi,sizeof mbi)||mbi.AllocationBase!=exe||(uintptr_t)ctorTarget<(uintptr_t)exe)return -6;*ctorRva=(uintptr_t)ctorTarget-(uintptr_t)exe;update=(Update)u;ctor=(Ctor)ctorTarget;prepared=1;return 0;}
/* The caller must independently verify ctor target/bytes before this step. */
static int T60_snapshot_ready(unsigned long long confirmedCtorRva,const unsigned char*prefix,size_t n){if(!isgui()||!prepared||!prefix||n!=16||confirmedCtorRva!=(uintptr_t)ctorTarget-(uintptr_t)GetModuleHandleA(NULL))return -1;__try{if(memcmp(ctorTarget,prefix,16))return -1;}__except(EXCEPTION_EXECUTE_HANDLER){return -1;}HMODULE h;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(const char*)&T60_snapshot_ready,&h))return -2;ready=1;return 0;}
static int snap_epoch(unsigned long long*e){long busy;unsigned long thread;if(epochfn(e,&busy,&thread)||busy||(thread&&thread!=(unsigned long)gui))return 0;return 1;}
/* Attestation is a trusted GUI caller assertion, not independently proven here. */
static int T60_snapshot_capture(void*app,void*character,void*attestedSource,unsigned long long attestedEpoch,int ordinaryStable,unsigned long long*out){
 if(out)*out=0;if(!out||!ready||!isgui()||!app||!character||!attestedSource||ordinaryStable!=1)return -1;unsigned long long ep;if(!snap_epoch(&ep)||ep!=attestedEpoch)return -2;void*source=0;__try{if(*(void**)((char*)app+0xf0)!=character)return -3;source=*(void**)((char*)app+0x148);if(source!=attestedSource||*(void**)source!=(char*)GetModuleHandleA(NULL)+0x1682098||*(unsigned*)((char*)source+8)!=0x1e240||*(size_t*)((char*)source+0x98)!=0||*(unsigned*)((char*)source+0x50)!=66)return -3;}__except(EXCEPTION_EXECUTE_HANDLER){return -3;}
 if(attempts>=16||next_id==ULLONG_MAX)return -4;for(int i=0;i<2;i++)if(slots[i].state&&slots[i].source==source&&slots[i].epoch==ep)return -10;int k=-1;for(int i=0;i<2;i++)if(!slots[i].state){k=i;break;}if(k<0)return -4;attempts++;Snapshot*s=&slots[k];s->id=++next_id;s->epoch=ep;s->app=app;s->character=character;s->source=source;s->state=1;*out=s->id;
 __try{s->validity=*(unsigned*)((char*)source+8);s->container=*(void**)((char*)source+0x10);s->standalone=*((unsigned char*)source+0x18);s->readonly=*((unsigned char*)source+0x20);if(objects>=4||objectAttempts>=16){s->state=3;return -4;}objects++;objectAttempts++;s->copy=allocfn(0x300);if(s->copy){privateCreated++;privateRetained++;}if(!s->copy){objects--;s->state=3;return -5;}if(ctor(s->copy)!=s->copy){s->state=3;return -6;}if(!snap_epoch(&ep)||ep!=attestedEpoch||*(void**)((char*)app+0x148)!=source){s->state=3;return -7;}if(s->copy==source||*(void**)s->copy!=(char*)GetModuleHandleA(NULL)+0x1682098){s->state=3;return -6;}s->copy_ok=update(s->copy,source,0);if(!s->copy_ok){s->state=3;return -8;}if(!snap_epoch(&ep)||ep!=attestedEpoch||*(void**)((char*)app+0x148)!=source){s->state=3;return -7;}s->copy_validity=*(unsigned*)((char*)s->copy+8);s->copy_container=*(void**)((char*)s->copy+0x10);s->copy_standalone=*((unsigned char*)s->copy+0x18);s->copy_readonly=*((unsigned char*)s->copy+0x20);s->state=2;return 0;}__except(EXCEPTION_EXECUTE_HANDLER){s->state=3;return -9;}
}
static int T60_snapshot_status(unsigned long long id,Snapshot*out,size_t size){if(!isgui()||!out||size<sizeof(*out))return -1;for(int i=0;i<2;i++)if(slots[i].state&&slots[i].id==id){*out=slots[i];out->copy=NULL;out->scratch=NULL;return 0;}return -2;}
static unsigned T60_snapshot_status_size(void){return sizeof(Snapshot);}
static unsigned T60_snapshot_attempts(void){return attempts;}

/* Caller supplies independently audited EXE RVA and first 16 bytes after cold resolution. */
static int T60_snapshot_confirm_save(unsigned long long rva,const unsigned char*prefix,size_t n){if(!isgui()||!ready||!saveTarget||!prefix||n!=16)return -1;HMODULE exe=GetModuleHandleA(NULL);MEMORY_BASIC_INFORMATION m;__try{if(!VirtualQuery(saveTarget,&m,sizeof m)||m.AllocationBase!=exe||(uintptr_t)saveTarget!=(uintptr_t)exe+rva||memcmp(saveTarget,prefix,16))return -2;}__except(EXCEPTION_EXECUTE_HANDLER){return -2;}saveFile=(SaveFile)saveTarget;return 0;}
static int reserve_file(const char*name){HANDLE h=CreateFileA(name,GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);if(h==INVALID_HANDLE_VALUE)return 0;CloseHandle(h);return 1;}
static int file_nonempty(const char*name){WIN32_FILE_ATTRIBUTE_DATA a;if(!GetFileAttributesExA(name,GetFileExInfoStandard,&a))return 0;return a.nFileSizeHigh||a.nFileSizeLow;}
static int write_snapshot_file(void*data,const char*name){NativeString path={0};path.storage.data=name;path.length=strlen(name);path.capacity=path.length;return saveFile(data,&path)!=0;}
/* Fixed, unique workspace paths only. Original must still be current and ordinary.
 * Failure leaves the pair reserved and cannot be retried; no pre-existing file is overwritten. */
static int T60_snapshot_write_files(unsigned long long id,int ordinaryStable){
 if(!isgui()||!ready||!saveFile||ordinaryStable!=1)return -1;int k=-1;for(int i=0;i<2;i++)if(slots[i].id==id&&slots[i].state==4){k=i;break;}if(k<0)return -2;if(savedMask&(1u<<k))return -3;
 Snapshot*s=&slots[k];unsigned long long ep;if(!snap_epoch(&ep)||ep!=s->epoch)return -4;
 const char*source=k==0?"D:/JACK/KenshiArmorMod/research/private_snapshot_complete_20261103/source_1.gamedata":"D:/JACK/KenshiArmorMod/research/private_snapshot_complete_20261103/source_2.gamedata";
 const char*copy=k==0?"D:/JACK/KenshiArmorMod/research/private_snapshot_complete_20261103/copy_1.gamedata":"D:/JACK/KenshiArmorMod/research/private_snapshot_complete_20261103/copy_2.gamedata";
 __try{if(*(void**)((char*)s->app+0xf0)!=s->character||*(void**)((char*)s->app+0x148)!=s->source)return -4;savedMask|=1u<<k;if(!reserve_file(source))return -5;if(!reserve_file(copy))return -5;if(!write_snapshot_file(s->source,source)||!file_nonempty(source))return -6;if(!snap_epoch(&ep)||ep!=s->epoch||*(void**)((char*)s->app+0x148)!=s->source)return -4;if(!write_snapshot_file(s->copy,copy)||!file_nonempty(copy))return -6;
 const char*scratch=k==0?"D:/JACK/KenshiArmorMod/research/private_snapshot_complete_20261103/scratch_1.gamedata":"D:/JACK/KenshiArmorMod/research/private_snapshot_complete_20261103/scratch_2.gamedata";if(!reserve_file(scratch)||!write_snapshot_file(s->scratch,scratch)||!file_nonempty(scratch))return -6;return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return -7;}
}
/* Version-specific map helper ABI; only private objects may be modified. */
typedef void*(*IndexBool)(void*,const NativeString*);typedef size_t(*EraseBool)(void*,void**,void*);typedef void*(*RefList)(void*,const NativeString*);typedef void(*ClearData)(void*);
static IndexBool boolIndex;static EraseBool boolErase;static RefList refList;static ClearData clearData;static int completeReady;
typedef struct {char key[129];unsigned short len;unsigned char value;} Item;
typedef struct {Item items[128];unsigned count;} Items;
static int index_item(const Items*a,const char*key,unsigned len){for(unsigned i=0;i<a->count;i++)if(a->items[i].len==len&&!memcmp(a->items[i].key,key,len))return (int)i;return -1;}
/* For ref map value=1 means empty; for active map it is the bool. */
static int read_items(void*data,size_t off,int ref,Items*out){
 memset(out,0,sizeof(*out));__try{char*m=(char*)data+off;size_t cap=*(size_t*)(m+0x18),count=*(size_t*)(m+0x20);void**b=*(void***)(m+0x38);
  if(count>128||cap>8192||!cap||(cap&(cap-1)))return 0;if(!count&&!b)return 1;if(!b)return 0;void*node=count?b[cap]:NULL;
  while(node){if(out->count>=count)return 0;char*n=node;NativeString*str=(NativeString*)(n+0x10);size_t len=str->length,c=str->capacity;if(len>128||len>c||(c<16&&len>15))return 0;const char*k=c<16?str->storage.small:str->storage.data;if(!k||index_item(out,k,(unsigned)len)>=0)return 0;Item*x=&out->items[out->count++];memcpy(x->key,k,len);x->key[len]=0;x->len=(unsigned short)len;
   if(ref){uintptr_t start=*(uintptr_t*)(n+0x38),end=*(uintptr_t*)(n+0x40);if(end<start||(end-start)%0x40||(end-start)/0x40>4096)return 0;x->value=(start==end);}else{x->value=*(unsigned char*)(n+0x38);if(x->value>1)return 0;}node=*(void**)n;}
  return out->count==count;
 }__except(EXCEPTION_EXECUTE_HANDLER){return 0;}
}
static NativeString key_view(const Item*x){NativeString k={0};if(x->len<16){memcpy(k.storage.small,x->key,x->len);k.capacity=15;}else{k.storage.data=x->key;k.capacity=x->len;}k.length=x->len;return k;}
static int same_items(const Items*a,const Items*b){if(a->count!=b->count)return 0;for(unsigned i=0;i<a->count;i++){int j=index_item(b,a->items[i].key,a->items[i].len);if(j<0||a->items[i].value!=b->items[j].value)return 0;}return 1;}
static int copy_active(void*data,const Items*items){for(unsigned i=0;i<items->count;i++){NativeString key=key_view(&items->items[i]);char*pair=boolIndex((char*)data+0xb8,&key);if(!pair)return 0;pair[0x28]=items->items[i].value;}return 1;}
static int clear_active(void*data){char*m=(char*)data+0xb8;size_t count=*(size_t*)(m+0x20),cap=*(size_t*)(m+0x18);void**b=*(void***)(m+0x38);if(count>128||!cap||cap>8192||(cap&(cap-1)))return 0;if(!count)return !b||b[cap]==NULL;if(!b||boolErase(m,&b[cap],NULL)!=count)return 0;cap=*(size_t*)(m+0x18);b=*(void***)(m+0x38);if(!cap||cap>8192||(cap&(cap-1))||*(size_t*)(m+0x20)!=0)return 0;if(!b)return 1;if(b[cap])return 0;for(size_t i=0;i<cap;i++)b[i]=NULL;return 1;}
static int restore_empty_refs(void*data,const Items*src){Items dst;if(!read_items(data,0x2b8,1,&dst))return 0;for(unsigned i=0;i<src->count;i++)if(src->items[i].value&&index_item(&dst,src->items[i].key,src->items[i].len)<0){NativeString key=key_view(&src->items[i]);void**vec=refList(data,&key);if(!vec||vec[0]!=vec[1])return 0;}return 1;}
typedef struct {Items keys;char*nodes[128];} Nodes;
static int read_nodes(void*data,size_t off,Nodes*out){memset(out,0,sizeof(*out));char*m=(char*)data+off;size_t cap=*(size_t*)(m+0x18),count=*(size_t*)(m+0x20);void**b=*(void***)(m+0x38);if(!cap||cap>8192||(cap&(cap-1))||count>128)return 0;if(!count&&!b)return 1;if(!b)return 0;char*n=count?b[cap]:NULL;while(n){if(out->keys.count>=count)return 0;NativeString*z=(NativeString*)(n+0x10);size_t len=z->length;if(len>128||len>z->capacity)return 0;const char*k=z->capacity<16?z->storage.small:z->storage.data;if(!k||index_item(&out->keys,k,(unsigned)len)>=0)return 0;unsigned i=out->keys.count++;memcpy(out->keys.items[i].key,k,len);out->keys.items[i].key[len]=0;out->keys.items[i].len=(unsigned short)len;out->nodes[i]=n;n=*(char**)n;}return out->keys.count==count;}
static int same_string(NativeString*a,NativeString*b){if(a->length>4096||a->length!=b->length||a->length>a->capacity||b->length>b->capacity)return 0;const char*x=a->capacity<16?a->storage.small:a->storage.data,*y=b->capacity<16?b->storage.small:b->storage.data;return x&&y&&!memcmp(x,y,(size_t)a->length);}
static int same_full_maps(void*a,void*b){Nodes x,y;for(unsigned k=0;k<8;k++){void**xb=*(void***)((char*)a+0xf8+k*0x40+0x38),**yb=*(void***)((char*)b+0xf8+k*0x40+0x38);if(xb&&xb==yb)return 0;if(!read_nodes(a,0xf8+k*0x40,&x)||!read_nodes(b,0xf8+k*0x40,&y)||x.keys.count!=y.keys.count)return 0;for(unsigned i=0;i<x.keys.count;i++){int j=index_item(&y.keys,x.keys.items[i].key,x.keys.items[i].len);if(j<0)return 0;if(x.nodes[i]==y.nodes[j])return 0;NativeString*xkey=(NativeString*)(x.nodes[i]+0x10),*ykey=(NativeString*)(y.nodes[j]+0x10);if(xkey->capacity>=16&&ykey->capacity>=16&&xkey->storage.data==ykey->storage.data)return 0;char*av=x.nodes[i]+0x38,*bv=y.nodes[j]+0x38;
 if(k==1||k==4){if(!same_string((NativeString*)av,(NativeString*)bv))return 0;NativeString*as=(NativeString*)av,*bs=(NativeString*)bv;if(as->capacity>=16&&bs->capacity>=16&&as->storage.data==bs->storage.data)return 0;}
 else if(k==7){uintptr_t ab=*(uintptr_t*)av,ae=*(uintptr_t*)(av+8),bb=*(uintptr_t*)bv,be=*(uintptr_t*)(bv+8);if(ae<ab||be<bb||(ae-ab)%0x40||ae-ab!=be-bb||(ae-ab)/0x40>4096||(ae!=ab&&ab==bb))return 0;for(size_t q=0;q<(ae-ab)/0x40;q++){char*ar=(char*)ab+q*0x40,*br=(char*)bb+q*0x40;if(memcmp(ar,br,12)||!same_string((NativeString*)(ar+0x10),(NativeString*)(br+0x10)))return 0;NativeString*as=(NativeString*)(ar+0x10),*bs=(NativeString*)(br+0x10);if(as->capacity>=16&&bs->capacity>=16&&as->storage.data==bs->storage.data)return 0;}}
 else {size_t n=k==0?1:(k==5?12:(k==6?16:4));if(memcmp(av,bv,n))return 0;}
 }}return 1;}
static int active_independent(void*a,void*b){Nodes x,y;void**ab=*(void***)((char*)a+0xf0),**bb=*(void***)((char*)b+0xf0);if(ab&&ab==bb)return 0;if(!read_nodes(a,0xb8,&x)||!read_nodes(b,0xb8,&y)||x.keys.count!=y.keys.count)return 0;for(unsigned i=0;i<x.keys.count;i++){int j=index_item(&y.keys,x.keys.items[i].key,x.keys.items[i].len);if(j<0||x.nodes[i]==y.nodes[j])return 0;NativeString*p=(NativeString*)(x.nodes[i]+0x10),*q=(NativeString*)(y.nodes[j]+0x10);if(p->capacity>=16&&q->capacity>=16&&p->storage.data==q->storage.data)return 0;}return 1;}
#include "private_ownership.h"
static int same_content_shape(void*a,void*b){
 if(!private_id_independent(a,b))return 0;
 if(*(unsigned*)((char*)a+0x50)!=*(unsigned*)((char*)b+0x50)||*(size_t*)((char*)a+0x98)||*(size_t*)((char*)b+0x98))return 0;
 NativeString*x=(NativeString*)((char*)a+0x28),*y=(NativeString*)((char*)b+0x28);if(x->length>4096||y->length!=x->length||x->length>x->capacity||y->length>y->capacity)return 0;
 const char*xs=x->capacity<16?x->storage.small:x->storage.data,*ys=y->capacity<16?y->storage.small:y->storage.data;if(!xs||!ys||memcmp(xs,ys,(size_t)x->length))return 0;
 for(size_t i=0;i<8;i++)if(*(size_t*)((char*)a+0x118+i*0x40)!=*(size_t*)((char*)b+0x118+i*0x40))return 0;return 1;
}
static int complete_copy(void*dst,void*src){if(!private_id_independent(src,dst))return 0;Items active,refs,a,b;if(*(size_t*)((char*)src+0x98)!=0||*(size_t*)((char*)dst+0x98)!=0||!read_items(src,0xb8,0,&active)||!read_items(src,0x2b8,1,&refs))return 0;if(!clear_active(dst))return 0;clearData(dst);if(!update(dst,src,0)||!copy_active(dst,&active)||!restore_empty_refs(dst,&refs))return 0;if(!read_items(dst,0xb8,0,&a)||!read_items(dst,0x2b8,1,&b)||!same_items(&active,&a)||!same_items(&refs,&b)||!same_content_shape(src,dst)||!same_full_maps(src,dst)||!active_independent(src,dst))return 0;return 1;}
static int T60_complete_prepare(void){if(!isgui()||!ready)return -1;HMODULE exe=GetModuleHandleA(NULL),lib=GetModuleHandleA("KenshiLib.dll");void*r=target(lib,"?_getReferenceList_nonConst@GameData@@QEAAPEAV?$vector@VGameDataReference@@V?$STLAllocator@VGameDataReference@@V?$CategorisedAllocPolicy@$0A@@Ogre@@@Ogre@@@std@@AEBV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@3@@Z"),*c=target(lib,"?clearEverything@GameData@@QEAAXXZ");unsigned char bp[]={0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x48,0x81,0xec,0x90,0,0,0,0x48},ep[]={0x48,0x89,0x5c,0x24,8,0x48,0x89,0x6c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57},rp[]={0x48,0x83,0xec,0x28,0x48,0x81,0xc1,0xb8,2,0,0,0xe8,0xca,0xfd,0xf2,0xff},cp[]={0x48,0x89,0x5c,0x24,8,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x20,0x33};if(r!=(char*)exe+0xd5010||c!=(char*)exe+0x57a990||memcmp(r,rp,16)||memcmp(c,cp,16)||memcmp((char*)exe+0x6c780,bp,16)||memcmp((char*)exe+0xa6900,ep,16))return -2;boolIndex=(IndexBool)((char*)exe+0x6c780);boolErase=(EraseBool)((char*)exe+0xa6900);refList=(RefList)r;clearData=(ClearData)c;completeReady=1;return 0;}
/* On success active and reference-key/empty-shape validated; other maps require separate semantic compare. */
static int T60_complete_roundtrip(unsigned long long id){if(!isgui()||!completeReady)return -1;Snapshot*s=NULL;for(int i=0;i<2;i++)if(slots[i].id==id&&slots[i].state==2)s=&slots[i];if(!s)return -2;unsigned long long ep;if(!snap_epoch(&ep)||ep!=s->epoch)return -3;__try{if(*(void**)((char*)s->app+0x148)!=s->source||*(size_t*)((char*)s->source+0x98)!=0)return -3;if(!complete_copy(s->copy,s->source)){s->state=3;return -4;}Items initialActive,initialRefs;if(!read_items(s->copy,0xb8,0,&initialActive)||!read_items(s->copy,0x2b8,1,&initialRefs)){s->state=3;return -4;}
 Item baseline={"__T60_snapshot_baseline_false_20261103__",0,0},baselineRef={"__T60_snapshot_baseline_empty_20261103__",0,0};baseline.len=(unsigned short)strlen(baseline.key);baselineRef.len=(unsigned short)strlen(baselineRef.key);if(index_item(&initialActive,baseline.key,baseline.len)>=0||index_item(&initialRefs,baselineRef.key,baselineRef.len)>=0){s->state=3;return -6;}NativeString baseKey=key_view(&baseline);char*basePair=boolIndex((char*)s->copy+0xb8,&baseKey);if(!basePair){s->state=3;return -4;}basePair[0x28]=0;baseKey=key_view(&baselineRef);void**baseVec=refList(s->copy,&baseKey);if(!baseVec||baseVec[0]!=baseVec[1]){s->state=3;return -4;}
 if(objects>=4||objectAttempts>=16){s->state=3;return -5;}objects++;objectAttempts++;s->scratch=allocfn(0x300);if(s->scratch){privateCreated++;privateRetained++;}if(!s->scratch){objects--;s->state=3;return -5;}if(ctor(s->scratch)!=s->scratch||*(void**)s->scratch!=(char*)GetModuleHandleA(NULL)+0x1682098){s->state=3;return -5;}if(!complete_copy(s->scratch,s->copy)){s->state=3;return -4;}
 baseKey=key_view(&baseline);basePair=boolIndex((char*)s->scratch+0xb8,&baseKey);if(!basePair){s->state=3;return -4;}basePair[0x28]=1;
 Items before,refs,after,tmp;if(!read_items(s->copy,0xb8,0,&before)||!read_items(s->copy,0x2b8,1,&refs)){s->state=3;return -4;}Item test={"__T60_snapshot_active_test_20261103__",35,1},empty={"__T60_snapshot_empty_ref_20261103__",34,0};test.len=(unsigned short)strlen(test.key);empty.len=(unsigned short)strlen(empty.key);if(index_item(&before,test.key,test.len)>=0||index_item(&refs,empty.key,empty.len)>=0){s->state=3;return -6;}NativeString key=key_view(&test);char*pair=boolIndex((char*)s->scratch+0xb8,&key);if(!pair){s->state=3;return -4;}pair[0x28]=1;key=key_view(&empty);void**v=refList(s->scratch,&key);if(!v||v[0]!=v[1]||!read_items(s->scratch,0xb8,0,&after)||index_item(&after,test.key,test.len)<0||!read_items(s->scratch,0x2b8,1,&tmp)||index_item(&tmp,empty.key,empty.len)<0){s->state=3;return -4;}if(!complete_copy(s->scratch,s->copy)||!snap_epoch(&ep)||ep!=s->epoch||*(void**)((char*)s->app+0x148)!=s->source){s->state=3;return -4;}if(!read_items(s->scratch,0xb8,0,&after)||!read_items(s->scratch,0x2b8,1,&tmp)){s->state=3;return -4;}int bi=index_item(&after,baseline.key,baseline.len),ri=index_item(&tmp,baselineRef.key,baselineRef.len);if(bi<0||after.items[bi].value!=0||ri<0||!tmp.items[ri].value||index_item(&after,test.key,test.len)>=0||index_item(&tmp,empty.key,empty.len)>=0){s->state=3;return -4;}s->state=4;return 0;}__except(EXCEPTION_EXECUTE_HANDLER){s->state=3;return -7;}}

/* No free is implemented in this research candidate. */
static int T60_complete_stats(unsigned long long*out,unsigned cap){if(!isgui()||!out||cap<6)return -1;unsigned ok=0,quarantined=0;for(int i=0;i<2;i++){ok+=slots[i].state==4;quarantined+=slots[i].state==3;}out[0]=objectAttempts;out[1]=objects;out[2]=ok;out[3]=quarantined;out[4]=0;out[5]=attempts;return 0;}
typedef void*(*DeletePrivate)(void*,unsigned);
static DeletePrivate privateDeleter;
static int source_current(Snapshot*s){unsigned long long ep;if(!snap_epoch(&ep)||ep!=s->epoch)return 0;__try{return *(void**)((char*)s->app+0xf0)==s->character&&*(void**)((char*)s->app+0x148)==s->source;}__except(EXCEPTION_EXECUTE_HANDLER){return 0;}}
#ifdef PRIVATE_RELEASE_TEST
static int checked_private(void*p,Snapshot*s){return p&&p!=s->source&&p!=s->app&&p!=s->character;}
#else
static int checked_private(void*p,Snapshot*s){if(!p||p==s->source||p==s->app||p==s->character)return 0;__try{unsigned char*exe=(unsigned char*)GetModuleHandleA(NULL);void**vt=*(void***)p;return vt==(void**)(exe+0x1682098)&&vt[0]==exe+0x5097f;}__except(EXCEPTION_EXECUTE_HANDLER){return 0;}}
#endif
#ifdef PRIVATE_RELEASE_TEST
static int deleter_ok(void){return privateDeleter!=NULL;}
#else
static int deleter_ok(void){static const unsigned char thunk[]={0xe9,0x8c,0x5c,0x06,0};static const unsigned char del[]={0x48,0x89,0x5c,0x24,0x08,0x57,0x48,0x83,0xec,0x20,0x48,0x8d,0x05,0x77,0xba,0x5c,0x01,0x8b,0xda,0x48,0x8b,0xf9,0x48,0x89,0x01,0xe8,0x4c,0x8e,0xf5,0xff,0xf6,0xc3};__try{unsigned char*exe=(unsigned char*)GetModuleHandleA(NULL);return privateDeleter==(DeletePrivate)(exe+0x5097f)&&!memcmp(exe+0x5097f,thunk,sizeof thunk)&&!memcmp(exe+0xb6610,del,sizeof del)&&*(void**)(exe+0x1682098)==exe+0x5097f;}__except(EXCEPTION_EXECUTE_HANDLER){return 0;}}
#endif
API int T60_private_release_ready(void){unsigned long long rva;static const unsigned char ctorPrefix[]={0x40,0x53,0x48,0x83,0xec,0x20,0x48,0x8b,0xd9,0xe8,0x26,0xd8,0xf5,0xff,0x4c,0x8d};static const unsigned char thunk[]={0xe9,0x8c,0x5c,0x06,0};static const unsigned char del[]={0x48,0x89,0x5c,0x24,0x08,0x57,0x48,0x83,0xec,0x20,0x48,0x8d,0x05,0x77,0xba,0x5c,0x01,0x8b,0xda,0x48,0x8b,0xf9,0x48,0x89,0x01,0xe8,0x4c,0x8e,0xf5,0xff,0xf6,0xc3};int rc=T60_snapshot_prepare(&rva);if(rc)return rc;if(T60_snapshot_ready(rva,ctorPrefix,16)||T60_complete_prepare())return -11;unsigned char*exe=(unsigned char*)GetModuleHandleA(NULL);if(memcmp(exe+0x5097f,thunk,sizeof thunk)||memcmp(exe+0xb6610,del,sizeof del)||*(void**)(exe+0x1682098)!=exe+0x5097f)return -12;privateDeleter=(DeletePrivate)(exe+0x5097f);return 0;}
static void private_report(unsigned long long*out,Snapshot*s,int result){out[0]=s?s->id:0;out[1]=privateCreated;out[2]=privateDeleted;out[3]=privateRetained;out[4]=privateQuarantine;out[5]=privateCompleted;out[6]=objectAttempts;out[7]=s?source_current(s):0;out[8]=(unsigned long long)(long long)result;}
API int T60_private_release_stats(unsigned long long*out,unsigned cap){if(!isgui()||!out||cap<8)return -1;out[0]=privateCreated;out[1]=privateDeleted;out[2]=privateRetained;out[3]=privateQuarantine;out[4]=privateCompleted;out[5]=objectAttempts;out[6]=next_id;out[7]=objects;if(cap>=9)out[8]=releaseStopped;return 0;}
API int T60_private_release_trial(void*app,void*character,void*source,unsigned long long epoch,int ordinaryStable,unsigned long long*out,unsigned cap){
 if(!out||cap<9)return -1;memset(out,0,9*sizeof(*out));if(!isgui()||!completeReady||!privateDeleter||InterlockedCompareExchange(&trialBusy,1,0))return -1;unsigned long long id=0;Snapshot*s=NULL;int rc=-2;
 __try{
  /* A failed private operation stops this DLL session, even for a new source.
   * Capacity is checked for the pair before reserving an ID or touching data. */
  if(releaseStopped){rc=-25;goto done;}
  if(objectAttempts>14||objects>2){rc=-4;goto done;}
  rc=T60_snapshot_capture(app,character,source,epoch,ordinaryStable,&id);if(id)for(int i=0;i<2;i++)if(slots[i].id==id){s=&slots[i];break;}if(rc||!s)goto done;
  rc=T60_complete_roundtrip(id);if(rc)goto quarantine;
  if(s->readers||!source_current(s)||s->copy==s->scratch||!checked_private(s->copy,s)||!checked_private(s->scratch,s)){rc=-20;goto quarantine;}
  /* Remove test sentinels and revalidate both private copies against the live source. */
  if(!complete_copy(s->copy,s->source)||!complete_copy(s->scratch,s->source)||!source_current(s)){rc=-21;goto quarantine;}
  /* Two individually source-independent copies can still alias each other. */
  if(!same_content_shape(s->copy,s->scratch)||!same_full_maps(s->copy,s->scratch)||!active_independent(s->copy,s->scratch)){rc=-26;goto quarantine;}
  s->state=5;
  for(int i=0;i<2;i++){
   void**field=i?&s->scratch:&s->copy;void*p=*field;
   if(s->readers||!source_current(s)||!checked_private(p,s)||!deleter_ok()||(i==0&&p==s->scratch)||(i==1&&p==s->copy)){rc=-22;goto quarantine;}
   privateDeleter(p,1);*field=NULL;privateDeleted++;privateRetained--;objects--;
  }
  if(!source_current(s)){rc=-23;goto quarantine;}
  privateCompleted++;rc=0;private_report(out,s,rc);memset(s,0,sizeof(*s));s=NULL;goto done;
 quarantine: if(s&&s->state!=3)s->state=3;
 done: if(rc&&s){releaseStopped=1;s->state=3;privateQuarantine++;}if(s||rc)private_report(out,s,rc);
 }__except(EXCEPTION_EXECUTE_HANDLER){rc=-24;releaseStopped=1;if(s){s->state=3;privateQuarantine++;}private_report(out,s,rc);}
 InterlockedExchange(&trialBusy,0);return rc;
}
