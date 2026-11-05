/* Serialize original appearance data for registered T60 wearers only.
 * The exact native function reads this+0x148 and copies its GameData. Pass a
 * stack-local shadow receiver: the live renderer and its pointers stay intact. */
#include "../visibility_lifecycle/t60_attachment_compat_v083.c"
#include <limits.h>
typedef void (*Serialize)(void*,void*);
typedef int (*SaveHook)(void*,void*,void**);
typedef struct {void* appearance;void* character;void* original;void* visual; unsigned long long generation; unsigned long long readers; int active;} SaveEntry;
typedef struct {SaveEntry entry; int slot;} SaveBorrow;
static SaveEntry saves[128];static SRWLOCK saveLock=SRWLOCK_INIT;
static unsigned long long nextGeneration, totalReaders;
static int readerQuarantine;
static unsigned long long clearEpoch;
typedef struct {void* data;unsigned long long owner,token;} RetirementLease;
static RetirementLease leases[128];static unsigned long long nextLeaseToken;
static Serialize saveOriginal;static int saveInstalled, hookAttempted;static SRWLOCK hookLock=SRWLOCK_INIT;static LONG64 saveCalls,saveShadows,savePasses;
/* A retired slot remains reserved until its final reader exits. No engine calls under lock. */
static SaveBorrow borrow(void* appearance){
 SaveBorrow b={0}; b.slot=-1; AcquireSRWLockExclusive(&saveLock);
 for(int i=0;i<128;i++) if(saves[i].active&&saves[i].appearance==appearance){
  b.entry=saves[i];
  if(saves[i].readers != ULLONG_MAX && totalReaders != ULLONG_MAX){saves[i].readers++;totalReaders++;b.slot=i;}
  else {readerQuarantine=1;b.slot=-2;} /* Preserve shadow serialization; no retirement may trust counts. */
  break;
 }
 ReleaseSRWLockExclusive(&saveLock);return b;
}
static void releaseBorrow(SaveBorrow* b){
 if(b->slot<0)return;AcquireSRWLockExclusive(&saveLock);SaveEntry* e=&saves[b->slot];
 if(e->generation==b->entry.generation && e->readers){e->readers--;totalReaders--;if(!e->active&&!e->readers)memset(e,0,sizeof(*e));}
 ReleaseSRWLockExclusive(&saveLock);b->slot=-1;
}
static void serializeOriginalAppearance(void* appearance,void* state){
 InterlockedIncrement64(&saveCalls);SaveBorrow b=borrow(appearance);
 __try {
  SaveEntry entry=b.entry;
  if(b.slot!=-1&&entry.original&&entry.original!=entry.visual&&*(void**)((char*)appearance+0xf0)==entry.character&&
     *(void**)((char*)appearance+0x148)==entry.visual){
   __declspec(align(16)) unsigned char shadow[0x170];memcpy(shadow,appearance,sizeof(shadow));
   *(void**)(shadow+0x148)=entry.original;saveOriginal(shadow,state);InterlockedIncrement64(&saveShadows);
  }else{saveOriginal(appearance,state);InterlockedIncrement64(&savePasses);}
 } __finally {releaseBorrow(&b);}
}
/* Called only once, even if a failing hook implementation writes the trampoline. */
static int installHookOnce(SaveHook hook,void* target){
 int result;AcquireSRWLockExclusive(&hookLock);
 if(saveInstalled)result=0;
 else if(hookAttempted)result=-4;
 else {hookAttempted=1;result=hook(target,(void*)&serializeOriginalAppearance,(void**)&saveOriginal);if(result==0&&saveOriginal){saveInstalled=1;result=0;}else result=-4;}
 ReleaseSRWLockExclusive(&hookLock);return result;
}
API int T60_save_ready(void){
 if(saveInstalled)return 0;if(bind()!=1)return -1;
 HMODULE lib=GetModuleHandleA("KenshiLib.dll");
 SaveHook hook=(SaveHook)(uintptr_t)GetProcAddress(lib,"?AddHook@KenshiLib@@YA?AW4HookStatus@1@PEAX0PEAPEAX@Z");
 void* target=(char*)GetModuleHandleA(NULL)+0x534d50;
 const unsigned char expected[]={0x4c,0x8b,0xdc,0x57,0x48,0x83,0xec,0x60,0x48,0xc7,0x44,0x24,0x20,0xfe,0xff,0xff};
 if(!hook||memcmp(target,expected,sizeof(expected)))return -2;
 HMODULE self;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(const char*)&T60_save_ready,&self))return -3;
 return installHookOnce(hook,target);
}
API int T60_save_register(void* appearance,void* character,void* original,void* visual){
 if(!saveInstalled||!appearance||!character||!original||!visual||original==visual)return -1;
 if(*(void**)((char*)appearance+0xf0)!=character||*(void**)((char*)appearance+0x148)!=visual)return -2;
 int index=-1,old=-1;AcquireSRWLockExclusive(&saveLock);
 if(readerQuarantine){index=-3;goto done;}
 for(int i=0;i<128;i++)if(leases[i].data==original||leases[i].data==visual){index=-4;goto done;}
 for(int i=0;i<128;i++)if(saves[i].active&&saves[i].appearance==appearance){old=i;break;}
 if(old>=0 && saves[old].character==character && saves[old].original==original && saves[old].visual==visual){index=old;goto done;}
 if(old>=0&&!saves[old].readers)index=old;
 else for(int i=0;i<128;i++)if(!saves[i].active&&!saves[i].readers){index=i;break;}
 if(index>=0 && nextGeneration!=ULLONG_MAX){
  if(old>=0){saves[old].active=0;if(!saves[old].readers)memset(&saves[old],0,sizeof(SaveEntry));}
  saves[index]=(SaveEntry){appearance,character,original,visual,++nextGeneration,0,1};
 }else index=-1;
 done: ReleaseSRWLockExclusive(&saveLock);return index;
}
API void T60_save_forget(void* appearance){
 AcquireSRWLockExclusive(&saveLock);for(int i=0;i<128;i++)if(saves[i].active&&saves[i].appearance==appearance){saves[i].active=0;if(!saves[i].readers)memset(&saves[i],0,sizeof(SaveEntry));}ReleaseSRWLockExclusive(&saveLock);
}
API void T60_save_clear(void){AcquireSRWLockExclusive(&saveLock);if(clearEpoch==ULLONG_MAX)readerQuarantine=1;else clearEpoch++;for(int i=0;i<128;i++){saves[i].active=0;if(!saves[i].readers)memset(&saves[i],0,sizeof(SaveEntry));}ReleaseSRWLockExclusive(&saveLock);}
/* Nonblocking save-reader closure only. Caller must establish that the App was
 * destroyed, data is actually detached, and NativeLife has unique ownership.
 * Owner IDs are a trusted NativeLife protocol, not authentication. */
API int T60_save_retire_try_acquire(void* data,unsigned long long owner,unsigned long long* token){
 if(!data||!owner||!token)return -1;*token=0;AcquireSRWLockExclusive(&saveLock);
 if(readerQuarantine){ReleaseSRWLockExclusive(&saveLock);return -3;}
 int slot=-1,empty=-1;
 for(int i=0;i<128;i++){if(leases[i].data==data){slot=i;break;}if(!leases[i].data&&empty<0)empty=i;}
 if(slot<0){if(empty<0){ReleaseSRWLockExclusive(&saveLock);return -2;}slot=empty;leases[slot].data=data;leases[slot].owner=owner;}
 if(leases[slot].owner!=owner){ReleaseSRWLockExclusive(&saveLock);return -5;}
 for(int i=0;i<128;i++)if(saves[i].active&&(saves[i].original==data||saves[i].visual==data)){
  saves[i].active=0;if(!saves[i].readers)memset(&saves[i],0,sizeof(SaveEntry));
 }
 if(leases[slot].token){ReleaseSRWLockExclusive(&saveLock);return 0;}
 for(int i=0;i<128;i++)if(saves[i].readers&&(saves[i].original==data||saves[i].visual==data)){
  ReleaseSRWLockExclusive(&saveLock);return 0;
 }
 if(nextLeaseToken==ULLONG_MAX){readerQuarantine=1;ReleaseSRWLockExclusive(&saveLock);return -3;}
 leases[slot].token=++nextLeaseToken;*token=leases[slot].token;ReleaseSRWLockExclusive(&saveLock);return 1;
}
API int T60_save_retire_release(unsigned long long token){
 if(!token)return -1;AcquireSRWLockExclusive(&saveLock);
 if(readerQuarantine){ReleaseSRWLockExclusive(&saveLock);return -3;}
 for(int i=0;i<128;i++)if(leases[i].token==token){memset(&leases[i],0,sizeof(leases[i]));ReleaseSRWLockExclusive(&saveLock);return 0;}
 ReleaseSRWLockExclusive(&saveLock);return -2;
}
/* A snapshot only, not a proof that engine users have quiesced. */
API int T60_save_clear_epoch(unsigned long long* epoch){if(!epoch)return -1;AcquireSRWLockShared(&saveLock);*epoch=clearEpoch;int result=readerQuarantine?-3:0;ReleaseSRWLockShared(&saveLock);return result;}
/* Snapshot only. generation=0 queries aggregate; nonzero queries retained generation.
 * A missing generation has zero tracked readers, but is not an engine lifetime proof. */
API int T60_save_readers(unsigned long long generation,unsigned long long* readers,int* active){
 if(!readers||!active)return -1;AcquireSRWLockShared(&saveLock);*readers=0;*active=0;
 if(readerQuarantine){*readers=ULLONG_MAX;*active=-1;ReleaseSRWLockShared(&saveLock);return -3;}
 if(!generation){*readers=totalReaders;for(int i=0;i<128;i++)*active+=saves[i].active;}
 else for(int i=0;i<128;i++)if(saves[i].generation==generation){*readers=saves[i].readers;*active=saves[i].active;break;}
 ReleaseSRWLockShared(&saveLock);return 0;
}
API int T60_save_generation(void* appearance,unsigned long long* generation){
 if(!appearance||!generation)return -1;*generation=0;AcquireSRWLockShared(&saveLock);
 if(readerQuarantine){ReleaseSRWLockShared(&saveLock);return -3;}
 for(int i=0;i<128;i++)if(saves[i].active&&saves[i].appearance==appearance){*generation=saves[i].generation;break;}
 ReleaseSRWLockShared(&saveLock);return *generation?0:-2;
}
API int T60_save_status(char* out,size_t capacity){
 if(!out||capacity<512)return -1;int active=0,retired=0,quarantine;unsigned long long readers;
 AcquireSRWLockShared(&saveLock);for(int i=0;i<128;i++){active+=saves[i].active;retired+=!saves[i].active&&saves[i].readers!=0;}quarantine=readerQuarantine;readers=quarantine?ULLONG_MAX:totalReaders;ReleaseSRWLockShared(&saveLock);
 return snprintf(out,capacity,"{\"installed\":%d,\"active\":%d,\"retired\":%d,\"readers\":%llu,\"quarantined\":%d,\"calls\":%lld,\"original_appearance_serializations\":%lld,\"ordinary_passthrough\":%lld,\"live_renderer_writes\":0}",saveInstalled,active,retired,readers,quarantine,(long long)saveCalls,(long long)saveShadows,(long long)savePasses);
}
