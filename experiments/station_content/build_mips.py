from pathlib import Path
import io,json,hashlib,struct
import numpy as np
from PIL import Image
p=Path(r'D:\JACK\KenshiArmorMod\research\station_candidate_20261103'); opt=p/'optimized';out=opt/'with_mips';assert not out.exists();out.mkdir()

def sha(x):return hashlib.sha256(x).hexdigest()
def normalize(image):
 a=np.asarray(image,dtype=np.uint8); rgb=a[:,:,:3].astype(np.float32)/127.5-1.0
 lengths=np.linalg.norm(rgb,axis=2,keepdims=True); rgb=np.where(lengths>1e-8,rgb/np.maximum(lengths,1e-8),np.array([0,0,1],dtype=np.float32)); b=np.empty_like(a);b[:,:,:3]=np.clip(np.rint((rgb+1)*127.5),0,255).astype(np.uint8);b[:,:,3]=a[:,:,3];return Image.fromarray(b,'RGBA')
def length(w,h,fmt):return max(1,(w+3)//4)*max(1,(h+3)//4)*(8 if fmt=='DXT1' else 16)
def single(image,fmt):
 b=io.BytesIO();image.save(b,format='DDS',pixel_format=fmt);raw=b.getvalue();assert raw[:4]==b'DDS ' and raw[84:88]==fmt.encode();w,h=image.size; assert len(raw)==128+length(w,h,fmt); return raw
results={}
for name,fmt in [('station_d','DXT5'),('station_n','DXT5'),('station_m','DXT1')]:
 base=(opt/(name+'.dds')).read_bytes();assert len(base)==128+length(2048,2048,fmt) and base[84:88]==fmt.encode()
 im=Image.open(p/(name+'.dds')).convert('RGBA'); assert im.size==(2048,2048)
 levels=[{'level':0,'width':2048,'height':2048,'bytes':len(base)-128,'sha256':sha(base[128:])}];pieces=[base[128:]];level=0
 while im.size!=(1,1):
  w,h=im.size; im=im.resize((max(1,w//2),max(1,h//2)),Image.Resampling.BOX)
  if name=='station_n':im=normalize(im)
  level+=1; raw=single(im,fmt);payload=raw[128:];pieces.append(payload);levels.append({'level':level,'width':im.width,'height':im.height,'bytes':len(payload),'sha256':sha(payload)})
 header=bytearray(base[:128]); flags=struct.unpack_from('<I',header,8)[0]|0x20000;struct.pack_into('<I',header,8,flags);struct.pack_into('<I',header,20,len(pieces[0]));struct.pack_into('<I',header,28,len(pieces));caps=struct.unpack_from('<I',header,108)[0]|0x8|0x400000;struct.pack_into('<I',header,108,caps)
 result=bytes(header)+b''.join(pieces);target=out/(name+'.dds');target.write_bytes(result);check=target.read_bytes();assert len(check)==128+sum(x['bytes'] for x in levels) and len(levels)==12 and struct.unpack_from('<I',check,28)[0]==12 and check[128:128+len(pieces[0])]==base[128:]
 assert struct.unpack_from('<I',check,8)[0]&0x20000 and (struct.unpack_from('<I',check,108)[0]&0x400008)==0x400008
 pos=128
 for entry in levels:
  n=length(entry['width'],entry['height'],fmt); assert entry['bytes']==n and sha(check[pos:pos+n])==entry['sha256'];pos+=n
  # Rewrap each block as a standalone DDS to verify the decoder at that size.
  h=bytearray(base[:128]);struct.pack_into('<I',h,12,entry['height']);struct.pack_into('<I',h,16,entry['width']);struct.pack_into('<I',h,20,n);struct.pack_into('<I',h,28,0)
  decoded=Image.open(io.BytesIO(bytes(h)+check[pos-n:pos]));decoded.load();assert decoded.size==(entry['width'],entry['height'])
 original=Image.open(io.BytesIO(base)).convert('RGBA');current=Image.open(target).convert('RGBA');assert sha(original.tobytes())==sha(current.tobytes())
 results[name]={'format':fmt,'bytes':len(check),'sha256':sha(check),'base_decoded_sha256':sha(current.tobytes()),'mip0_identical':True,'levels':levels}
(out/'mip_audit.json').write_text(json.dumps({'status':'offline structural and Pillow decode validation; not engine validated','level_count':12,'filter':'BOX in existing stored channel values; no color space conversion','normal':'RGB decoded to [-1,1], averaged then renormalized for each lower level; alpha separately BOX filtered','diffuse_alpha':'BOX filtered with other stored channels; remains alpha','textures':results},indent=2),encoding='utf-8');print(json.dumps({k:{'bytes':v['bytes'],'levels':len(v['levels']),'mip0_identical':v['mip0_identical']}for k,v in results.items()},indent=2))
