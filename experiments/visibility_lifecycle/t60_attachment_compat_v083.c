/* Refresh only AppearanceBase.slots through this executable's own cache.
 * No setAppearanceData, object deletion, hooks, pose edits or save writes.
 * RVAs derived from RE_Kenshi child SHA256, not the different root executable.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wincrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define API __declspec(dllexport)
typedef struct {union {char small[16];const char* data;} storage;uint64_t length,capacity;} Str32;
typedef void* (*Singleton)(void);
typedef void (*Load)(void*,void*);
typedef void* (*Find)(void*,void*,unsigned char);
typedef unsigned char (*Position)(void*,const Str32*,float*,float*);
static Singleton singleton;static Load load;static Find find;static Position position;
static int ready;
static int bind(void){
 if(ready)return ready;
 char path[MAX_PATH];if(!GetModuleFileNameA(NULL,path,sizeof(path)))return -1;
 FILE* f=fopen(path,"rb");if(!f)return -2;
 HCRYPTPROV p=0;HCRYPTHASH h=0;unsigned char digest[32],*buffer=malloc(65536);DWORD n=32;
 int ok=buffer&&CryptAcquireContextA(&p,NULL,NULL,PROV_RSA_AES,CRYPT_VERIFYCONTEXT)&&
  CryptCreateHash(p,CALG_SHA_256,0,0,&h);
 size_t count;while(ok&&(count=fread(buffer,1,65536,f))>0)ok=CryptHashData(h,buffer,(DWORD)count,0);
 if(ferror(f))ok=0;fclose(f);free(buffer);
 if(ok)ok=CryptGetHashParam(h,HP_HASHVAL,digest,&n,0)&&n==32;
 if(h)CryptDestroyHash(h);if(p)CryptReleaseContext(p,0);
 const unsigned char expected[]={0x50,0x4b,0x36,0x2c,0xde,0x85,0x0d,0x56,0xaf,0xb1,0xce,0xa6,0xf5,0xb7,0xb0,0xee,0x01,0x4d,0x9d,0xd7,0xb4,0x7e,0x18,0x85,0x99,0xd9,0x1c,0x80,0x45,0x02,0xcd,0x3e};
 if(!ok||memcmp(digest,expected,32))return -3;
 char* base=(char*)GetModuleHandleA(NULL);
 if(memcmp(base+0x536950,"\x48\x8b\xc4\x55\x57\x41\x54",7)||
    memcmp(base+0x536840,"\x48\x89\x5c\x24\x18\x48\x89\x54\x24\x10",10)||
    memcmp(base+0x546020,"\x48\x83\xec\x38",4))return -4;
 singleton=(Singleton)(base+0x546020);load=(Load)(base+0x536950);find=(Find)(base+0x536840);
 position=(Position)(uintptr_t)GetProcAddress(GetModuleHandleA("KenshiLib.dll"),
 "?getAttachmentPosition@AppearanceBase@@QEAA_NAEBV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEAVVector3@Ogre@@AEAVQuaternion@5@@Z");
 if(!position)return -5;ready=1;return 1;
}
API int T60_attachment_read(void* appearance,char* out,size_t capacity){
 if(!appearance||!out||capacity<4096)return -1;out[0]=0;
 __try{
  int b=bind();if(b<0)return b;
  char* a=appearance;size_t used=(size_t)snprintf(out,capacity,"slots=%p race=%p data=%p female=%u\n",
   *(void**)(a+8),*(void**)(a+0x150),*(void**)(a+0x148),(unsigned char)a[0x140]);
  const char* names[]={"back","back2","hip","hands"};
  for(int i=0;i<4;i++){
   Str32 s={0};s.length=strlen(names[i]);s.capacity=15;memcpy(s.storage.small,names[i],s.length);
   float p[3]={0},q[4]={0};int found=position(a,&s,p,q);
   used+=(size_t)snprintf(out+used,capacity-used,"%s found=%d pos=(%.6f,%.6f,%.6f) quat=(%.6f,%.6f,%.6f,%.6f)\n",
    names[i],found,p[0],p[1],p[2],q[0],q[1],q[2],q[3]);
  }return 0;
 }__except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
API int T60_attachment_ready(void){return bind();}
API int T60_attachment_select(void* appearance){
 if(!appearance)return -1;
 __try{
  int b=bind();if(b<0)return b;
  char* a=appearance;
  void* race=*(void**)(a+0x150);if(!race)return -7;
  unsigned char female=(unsigned char)a[0x140];if(female>1)return -9;
  void* cache=singleton();if(!cache)return -10;
  void* slots=find(cache,race,female);
  if(!slots){load(cache,race);slots=find(cache,race,female);}
  if(!slots)return -11;
  void* old=*(void**)(a+8);
  *(void**)(a+8)=slots; /* Same assignment as native setAppearanceData, no data deletion. */
  return old==slots?0:1;
 }__except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
API int T60_attachment_restore(void* appearance,void* original){
 if(!appearance||!original)return -1;
 __try{int b=bind();if(b<0)return b;*(void**)((char*)appearance+8)=original;return 0;}
 __except(EXCEPTION_EXECUTE_HANDLER){return -8;}
}
API int T60_attachment_sync(void* appearance,char* out,size_t capacity){
 if(!appearance||!out||capacity<4096)return -1;
 int n=T60_attachment_select(appearance);if(n<0)return n;
 int read=T60_attachment_read(appearance,out,capacity);return read<0?read:n;
}
