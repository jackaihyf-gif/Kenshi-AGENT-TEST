# 单人只读计数仪器候选

基于 PR3 `d2809fd8df7ca4c1d0093bd78c1efd9a01d56b8b`，用于测试机采证，不改变生产穿脱/释放逻辑，不合并main。

新增 `lifecycle target=single-telemetry`，仅接受暂停、禁止自动存档的配置单人；GUI/原生世界快照稳定、非busy/loading、身份世代一致、身体非重建，且本桥固定路径的独立槽加载请求对应世代、SaveManager name/location/signal匹配。空菜单、多角色、缺失/未知字段和错世代拒绝。

读数语义：appearance_allocations是进程累计成功工厂返回次数；visual_pool_entries是当前Lua池项数；material_slots是已加载生产材质DLL的保留槽计数。这些不是全引擎实际存活对象总量，也不证明回收。未知项不填0。

材料DLL只通过完整路径GetModuleHandleA获取已有实例，GetModuleFileNameA核对路径、GetProcAddress调用已有T60_material_slots导出，不使用LoadLibrary。宿主启动前须核对已接受DLL哈希和精确游戏版本。

请求名和signal闲置、世代前进只是门禁证据，不单独证明读回成功；getCurrentGame可能保留旧值，仅报告。实机需独立比对源槽文件哈希、角色与装备，不能将本接口输出当保存成功证明。整个既有RPC还会执行原桥characters/observe读取，不能称全部RPC只访问缓存。本次只在连续稳定暂停后调用，原桥加载期的行为未重构。

离线：使用本机LuaJIT，13项Python测试通过（新observer内包含多项拒绝断言、既有真实Lua桥Mock、安装器重复安装/备份/聚合标识）；所改Python Ruff通过。命令：

```
python -m pytest -q tests/test_single_telemetry.py tests/test_telemetry_install.py tests/test_direct_bridge.py -p no:faulthandler --no-cov
python -m ruff check tests/test_single_telemetry.py tests/test_telemetry_install.py scripts/install_lua_bridge.py
```

必须设置KENSHI_TEST_LUA51到已存在的LuaJIT DLL；未设置则Lua项跳过，不能写为已执行。no:faulthandler避免把LuaJIT可捕获异常展开为Windows fatal堆栈；之前默认handler曾打印该诊断，但测试进程退出0，不是游戏崩溃。

独立Terra中等审查后修正加载门禁、请求归因、已加载模块核对和安装器聚合哈希遗漏。实机尚待执行；异常立即停止，不放宽门禁。资源16/32/128不变，不启用私有释放、不清计数，不执行新保存，不改用户存档。
