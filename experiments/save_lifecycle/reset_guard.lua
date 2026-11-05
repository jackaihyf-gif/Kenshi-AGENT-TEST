-- Exact-build, reset-only null-result guard. No object writes or polling.
local ffi=require('ffi')
ffi.cdef[[int T60_reset_guard_ready(void);int T60_reset_guard_status(char*,size_t);]]
local native=ffi.load('D:/steam/steamapps/common/Kenshi/mods/JACK_T60_WearLab/plugin/T60ResetGuard_20261105.dll')
assert(native.T60_reset_guard_ready()==0,'Reset null-result guard refused this build')
_G.JACK_T60_RESET_GUARD_STATUS=function()
 local out=ffi.new('char[512]')
 assert(native.T60_reset_guard_status(out,512)>=0)
 return ffi.string(out)
end
print('[JACK T60 Reset Guard] Exact-build reset null-result guard ready')
