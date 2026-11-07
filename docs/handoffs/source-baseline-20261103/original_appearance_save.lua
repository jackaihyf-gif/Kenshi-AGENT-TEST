-- Only the save receiver is shadowed; no frame-time visual or item changes.
local ffi=require('ffi')
ffi.cdef[[int T60_save_ready(void);int T60_save_register(void*,void*,void*,void*);void T60_save_forget(void*);void T60_save_clear(void);int T60_save_status(char*,size_t);]]
local native=ffi.load('D:/steam/steamapps/common/Kenshi/mods/JACK_T60_WearLab/plugin/T60OriginalSave_v096.dll')
assert(native.T60_save_ready()==0,'Original-appearance serializer refused this engine build')
local function raw(x)return x and ffi.cast('void**',x)[0]or nil end
local M={}
function M.register(c,a,original,visual)
 assert(native.T60_save_register(raw(a),raw(c),raw(original),raw(visual))>=0,'Original-appearance save registration failed')
end
function M.forget(a)native.T60_save_forget(raw(a))end
function M.clear()native.T60_save_clear()end
_G.JACK_T60_SAVE_STATUS=function()local b=ffi.new('char[512]');assert(native.T60_save_status(b,512)>=0);return ffi.string(b)end
print('[JACK T60 Save v0.9.6] Original appearance serializer ready; live visual unchanged')
return M
