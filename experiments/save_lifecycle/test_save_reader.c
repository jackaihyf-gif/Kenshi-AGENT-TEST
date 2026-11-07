#ifdef NDEBUG
#error Assertions must be enabled
#endif
#include "save_reader.c"
#include <assert.h>
static unsigned char obj[0x170]; static int character,original,visual,original2,visual2;
static HANDLE entered,proceed;static volatile LONG mode,observed; static int depth, nestedCount;
static void engine(void* a,void* s){(void)s; if(a!=obj && *(void**)((char*)a+0x148)==&original)InterlockedIncrement(&observed); if(mode==1){assert(SetEvent(entered));assert(WaitForSingleObject(proceed,5000)==WAIT_OBJECT_0);} if(mode==2)RaiseException(0xe0000001,0,0,NULL); if(mode==3){unsigned long long n;int active;T60_save_readers(0,&n,&active);if(depth==0){depth++;serializeOriginalAppearance(obj,NULL);depth--;}else nestedCount=(int)n;}}
static int hookCalls;
static int failingHook(void* target,void* detour,void** originalOut){(void)target;(void)detour;hookCalls++;*originalOut=(void*)engine;return 7;}
static int nullHook(void* target,void* detour,void** originalOut){(void)target;(void)detour;hookCalls++;*originalOut=NULL;return 0;}
static volatile LONG wins;static unsigned long long concurrentToken;
static DWORD WINAPI contender(void* x){unsigned long long token=0;int result=T60_save_retire_try_acquire(&original,(unsigned long long)(uintptr_t)x,&token);if(result==1){InterlockedIncrement(&wins);concurrentToken=token;}else assert(result==-5||result==0);return 0;}
static DWORD WINAPI worker(void* x){(void)x;serializeOriginalAppearance(obj,NULL);return 0;}
/* Test-only reset after all test threads are joined; never part of production. */
static void fresh_fixture(void){
 memset(saves,0,sizeof saves); memset(leases,0,sizeof leases);
 nextGeneration=totalReaders=clearEpoch=nextLeaseToken=0; readerQuarantine=0;
 saveCalls=saveShadows=savePasses=0; saveInstalled=1; hookAttempted=0; saveOriginal=engine;
 memset(obj,0,sizeof obj); *(void**)(obj+0xf0)=&character; *(void**)(obj+0x148)=&visual;
 mode=observed=depth=nestedCount=hookCalls=wins=0; concurrentToken=0;
}
static void quarantine_checks(void){
 unsigned long long token=123,n=0,epoch=0; int active=0;
 assert(T60_save_register(obj,&character,&original,&visual)==-3);
 assert(T60_save_retire_try_acquire(&original,42,&token)==-3 && token==0);
 assert(T60_save_retire_release(1)==-3);
 assert(T60_save_readers(0,&n,&active)==-3 && n==ULLONG_MAX && active==-1);
 assert(T60_save_clear_epoch(&epoch)==-3);
}
int main(int argc,char** argv){
 volatile int sentinel=0;assert(++sentinel==1);
 if(argc>1 && !strcmp(argv[1],"generation_quarantine")){
  fresh_fixture(); assert(T60_save_register(obj,&character,&original,&visual)>=0);
  nextLeaseToken=ULLONG_MAX; unsigned long long token=0,generation=0;
  assert(T60_save_retire_try_acquire(&original2,44,&token)==-3);
  /* Requested query fail-closed check: exposes actual API contract if it fails. */
  assert(T60_save_generation(obj,&generation)==-3 && generation==0); return 0;
 }

 assert(installHookOnce(failingHook,obj)==-4);assert(saveOriginal==engine);assert(installHookOnce(failingHook,obj)==-4);assert(hookCalls==1&&!saveInstalled);
 hookAttempted=0;hookCalls=0;saveOriginal=NULL;assert(installHookOnce(nullHook,obj)==-4);assert(!saveOriginal&&!saveInstalled);assert(installHookOnce(nullHook,obj)==-4);assert(hookCalls==1);
 saveInstalled=1;saveOriginal=engine;*(void**)(obj+0xf0)=&character;*(void**)(obj+0x148)=&visual;
 entered=CreateEvent(NULL,TRUE,FALSE,NULL);proceed=CreateEvent(NULL,TRUE,FALSE,NULL);assert(entered && proceed);
 unsigned long long epoch;assert(!T60_save_clear_epoch(&epoch)&&epoch==0);T60_save_clear();assert(!T60_save_clear_epoch(&epoch)&&epoch==1);T60_save_clear();assert(!T60_save_clear_epoch(&epoch)&&epoch==2);
 int first=T60_save_register(obj,&character,&original,&visual);assert(first>=0);unsigned long long g1,g2,n;int active;assert(!T60_save_generation(obj,&g1));
 mode=1;HANDLE t=CreateThread(NULL,0,worker,NULL,0,NULL);assert(t);assert(WaitForSingleObject(entered,5000)==WAIT_OBJECT_0);
 T60_save_clear();assert(!T60_save_clear_epoch(&epoch)&&epoch==3);assert(!T60_save_readers(g1,&n,&active)&&n==1&&!active);
 *(void**)(obj+0x148)=&visual2;int second=T60_save_register(obj,&character,&original2,&visual2);assert(second>=0&&second!=first);assert(!T60_save_generation(obj,&g2)&&g2!=g1);
 assert(SetEvent(proceed));assert(WaitForSingleObject(t,5000)==WAIT_OBJECT_0);CloseHandle(t);assert(!T60_save_readers(g1,&n,&active)&&n==0&&!active);assert(!T60_save_readers(g2,&n,&active)&&n==0&&active);assert(observed==1);
 T60_save_forget(obj);assert(!T60_save_clear_epoch(&epoch)&&epoch==3);*(void**)(obj+0x148)=&visual;assert(T60_save_register(obj,&character,&original,&visual)==first);assert(!T60_save_generation(obj,&g2)&&g2!=g1);
 mode=2;__try{serializeOriginalAppearance(obj,NULL);assert(0);}__except(EXCEPTION_EXECUTE_HANDLER){} assert(!T60_save_readers(0,&n,&active)&&n==0&&active==1);
 mode=3;serializeOriginalAppearance(obj,NULL);assert(nestedCount==2);assert(!T60_save_readers(0,&n,&active)&&n==0);
 mode=0;HANDLE threads[16];for(int i=0;i<16;i++){threads[i]=CreateThread(NULL,0,worker,NULL,0,NULL);assert(threads[i]);}assert(WaitForMultipleObjects(16,threads,TRUE,5000)==WAIT_OBJECT_0);for(int i=0;i<16;i++)CloseHandle(threads[i]);assert(!T60_save_readers(0,&n,&active)&&n==0);/* Existing reader closes atomically; pending calls cannot mint a token. */
 assert(ResetEvent(entered));assert(ResetEvent(proceed));mode=1;t=CreateThread(NULL,0,worker,NULL,0,NULL);assert(t);assert(WaitForSingleObject(entered,5000)==WAIT_OBJECT_0);
 unsigned long long lease=0,lease2=0;assert(T60_save_retire_try_acquire(&original,42,&lease)==0&&lease==0);
 assert(T60_save_retire_try_acquire(&original,43,&lease2)==-5&&!lease2);assert(T60_save_register(obj,&character,&original,&visual)==-4);T60_save_clear();assert(T60_save_register(obj,&character,&original,&visual)==-4);
 assert(T60_save_retire_try_acquire(&original,42,&lease)==0);assert(SetEvent(proceed));assert(WaitForSingleObject(t,5000)==WAIT_OBJECT_0);CloseHandle(t);mode=0;
 assert(T60_save_retire_try_acquire(&original,42,&lease)==1&&lease);assert(T60_save_retire_try_acquire(&original,42,&lease2)==0&&!lease2);
 assert(T60_save_retire_release(lease)==0);assert(T60_save_register(obj,&character,&original,&visual)>=0);
 assert(T60_save_retire_try_acquire(&original,42,&lease2)==1&&lease2!=lease);assert(T60_save_retire_release(lease)==-2);assert(T60_save_register(obj,&character,&original,&visual)==-4);
 /* Closing before borrow prevents a shadow borrow. */
 LONG obs=observed;serializeOriginalAppearance(obj,NULL);assert(observed==obs);assert(T60_save_retire_release(lease2)==0);
 HANDLE racers[16];for(int i=0;i<16;i++){racers[i]=CreateThread(NULL,0,contender,(void*)(uintptr_t)(i+1),0,NULL);assert(racers[i]);}assert(WaitForMultipleObjects(16,racers,TRUE,5000)==WAIT_OBJECT_0);for(int i=0;i<16;i++)CloseHandle(racers[i]);assert(wins==1&&concurrentToken);assert(T60_save_retire_release(concurrentToken)==0);
 assert(T60_save_register(obj,&character,&original,&visual)>=0);
 nextLeaseToken=ULLONG_MAX;assert(T60_save_retire_try_acquire(&visual,44,&lease)==-3);assert(T60_save_retire_release(concurrentToken)==-3);assert(T60_save_register(obj,&character,&original,&visual)==-3);
 quarantine_checks();
 /* Each overflow scenario starts a full, thread-quiescent mock fixture. */
 fresh_fixture(); clearEpoch=ULLONG_MAX; T60_save_clear();
 assert(T60_save_clear_epoch(&epoch)==-3 && epoch==ULLONG_MAX); quarantine_checks();
 fresh_fixture(); assert(T60_save_register(obj,&character,&original,&visual)>=0);
 assert(!T60_save_generation(obj,&g2)); totalReaders=ULLONG_MAX; LONG before=observed;
 serializeOriginalAppearance(obj,NULL); assert(observed==before+1); T60_save_forget(obj);
 assert(T60_save_readers(0,&n,&active)==-3 && n==ULLONG_MAX && active==-1);
 assert(T60_save_readers(g2,&n,&active)==-3); quarantine_checks();
 char status[512];assert(T60_save_status(status,sizeof status)>0 && strstr(status,"\"quarantined\":1"));
 assert(CloseHandle(entered)); assert(CloseHandle(proceed));
 puts("save reader mock tests passed");return 0;
}
