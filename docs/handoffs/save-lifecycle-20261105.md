# 资源稳定性与二次读档崩溃：本机推进（2026-11-05）

用户最新分工：本机推进第4项（资源回收/长期稳定与二次读档）；换区视觉、混箱、工作台自然闭环等其他验收留给用户晚上，自动化不要抢跑这些功能验收。

## 当前交付与准确SHA

独立修复分支 `fix/save-reader-lifecycle-20261105`，实际被测 **9d95a9cb33ed138175fc42042fd969e2174e6d4b**（基于PR9 444f5d5）；仪器分支 `test-machine/save-reader-lifecycle-20261105`，实际被测 **7f5d1b9f8f7e18e37b7a6fafcabf40acfdfa7d92**（基于PR10 5f0aad8）。测试时上述commit已存在。随后仅补离线测试/文档，禁止将后续HEAD倒填实测。结果仍走 test-machine/real-bridge-handoff-20261103 / Draft PR1，不合并main。

已冷安装三文件：保存DLL `e336a29cc90efd8344d4015e7457bb0badea10b6751f9070e3146a1128df5d09` 替代 `50548585996690987f8e7442e63e36396a45fe7abbc106cd04c16029d84c3a60`；新增reset DLL `ddfdbdde4bb76f51f5ea53bbf6a0d788e6bd65783fa66f86d9d01dc84c55a2bf` 与init loader `e4855fecd65c29317095fe79f87e5ea5342d4967f91ed7c1b6600390da8007c7`。作者源码在experiments/save_lifecycle，无DLL上传。Craft仍1f03ee6c…、Energy仍e85dbe46…、可见性DLL仍a5c5c9fe…；未改武器平衡/配方/储具/声音/资产及16/32/128。

## 崩溃的新定位与有限保护

从原私有转储，用准确EXE的.pdata/version1 unwind重建14层有界整数栈；每一层返回PC逐个与实际call指令结束位置核对，遇到离开该游戏image即停止，不猜动态/外部模块。它比之前的栈内地址扫描增加了可核对调用关系，但不是完整系统调试器栈。结构规则参照[Microsoft AMD64异常展开文档](https://learn.microsoft.com/en-us/cpp/build/exception-handling-x64?view=msvc-170)。

导出映射确认主路径：loadGame→世界清理→FactionManager::clearAndDestroy→Platoon析构→ActivePlatoon析构→GameWorld::destroy→句柄树容器操作。0x7990d5虚调用返回NULL，0x7990db仍将返回值加0x3d0，再经0x28d400传入0x28b830；0x28b83a读取+8正好访问0x3d8。到故障处RAX未被两层容器函数改写，转储RAX=0/RCX=0x3d0和指令一致。详细RVA/调用位置见[脱敏栈证据](evidence/reset-null-crash-20261105.json)。虚方法具体含义、上游为何NULL、缺111依赖是否唯一诱因、是否与旁置外观有关仍未确认。未为复现读玩家旧世界。

reset_guard候选只在**当前线程正处于FactionManager清理且该返回值为NULL**时，跳过对不存在容器的这一次erase并从0x7990ea继续原清理；不跳角色销毁/整个reset，不等待或额外free，不改对象字段。非NULL/其他线程/非reset回原trampoline。启动核准确EXE哈希、目标指令、TEB线程ID与API一致、pin模块，部分hook失败锁存。clear hook异常finally归还线程/深度。无逐帧扫描或新轮询。

**本轮4次clear hook实际返回，但midpoint checks=0、null_skips=0。** 单人源槽未进入原失败的关联对象清理分支，不能说NULL或非NULL的实际引擎midpoint已验证，更不能称原崩溃已根治。该分支由真实汇编Mock覆盖；更接近原失败上下文的受限最小夹具尚未接入，列为未验证，不篡改玩家对象或强制伪造状态绕过。

## 保存借用协议的实质改动

旧生产保存表复制裸指针后不保留读者；现在每代registration带计数，borrow在锁内领取、锁外调用原生serializer，正常/SEH异常都在finally归还。clear/forget只使登记退役，有在途读者的slot不被复用；128槽、epoch、唯一lease及异常隔离保持有界，失败不重试hook、不清生产计数。还修正旧候选quarantine后generation查询仍给有效代号的问题：现在返回-3且输出0。只读status额外返回clear_epoch/registrations。

这是后续回收所需的保存读取部分，**不证明引擎/渲染reader已结束，没有任何free路径，也未解决完整回收**。退役lease不会在生产Lua里被调用，不能拿reader=0当作释放许可。首次旧非隔离Mock在明确启用断言时因前一溢出场景残留lease而失败；已采用历史审计过的独立fixture，只在测试线程全部join后重建测试状态，生产无对应清零操作。

## 一次有界实机过程

环境：Windows x64/16GiB，RE子EXE SHA504b362c…，正常权限Steam，完整120项mods.cfg SHA53dedcd2…。先核无游戏/其他执行者/RPC锁后安装。使用既有固定单人普通槽和唯一新槽 `T60_LIFE_096_READER_20261105_155147`，不读写玩家存档。game.save_root指本机lifecycle_v096/saves；原始记录在本机 `resource-lifecycle-20261105/native-series`，不上Git。

命令顺序：本机 `build_save_lifecycle_20261105.py` → 白名单提交绑定SHA → `install_save_lifecycle_20261105.py` → 仪器分支 `python scripts/install_lua_bridge.py --game <game.root> --install` → `python -X utf8 run_save_lifecycle_20261105.py`。运行器只调用已有单人load/save/wear/single-telemetry/status，新增仪器仅在status返回缓存reset_guard_runtime字符串，没有新动作或任意读写入口。保存名要求T60_LIFE_096前缀、唯一新槽、暂停禁自动保存；加载仍原生deferred请求及GUI/epoch/独立性门禁，无computer-use。

| 阶段 | 累计外观分配 | 已知Lua视觉池 | 材质槽 | 工作集MiB | 私有提交MiB |
|---|---:|---:|---:|---:|---:|
| 普通冷载 | 0 | 0 | 0 | 4478.2 | 7737.1 |
| 穿甲 | 1 | 1 | 1 | 4486.1 | 7784.8 |
| 新槽保存后 | 1 | 1 | 1 | 4549.5 | 7848.1 |
| 穿甲读回 | 2 | 1 | 2 | 4628.8 | 7940.2 |
| 读回普通源槽 | 2 | 0 | 2 | 4760.5 | 8029.3 |
| 再穿甲 | 3 | 1 | 3 | 4765.5 | 8039.8 |
| 再读回普通源槽 | 3 | 0 | 3 | 4852.6 | 8104.6 |
| 稳定等待20秒 | 3 | 0 | 3 | 4854.9 | 8106.7 |

实际新保存1次、在首次冷载之后读回3次；三个读回节点均完成，9人物字段比较通过。现有SaveReader只读比较独立源/新槽的原外观：**75字段和1组引用完全一致**，无head污染。没有完整递归库存GUI/所有原生容器一致性声明。8阶段保存reader都为0、retired=0、quarantine=0；registrations 0→1→2→3，clear_epoch 1→4，实际shadow保存1次、ordinary passthrough261次。共238连续内存点，无游戏/RPC异常；不设2GiB/主观阈值。

累计外观和材质槽随重新穿甲/读回增长，Lua池在普通态归0；**Lua池归0不等于原生对象已销毁**，本轮没有原生全存活计数。内存增长也包含正常世界加载/缓存，不能把约370MiB工作集增量直接归为泄漏。20秒稳定段计数不再增长，仍不足以证明长期收敛。上述表明确说明资源回收尚未完成、16累计预算仍在，不以扩容/清零掩盖。

## 验证边界、收尾与下一步

离线：保存reader线程/异常/租约/溢出和generation隔离查询通过；reset真实汇编Mock覆盖NULL/非NULL/其他线程/非reset、clear异常归还、首/第二hook失败及success-null锁存。显式-UNDEBUG、编译拒NDEBUG、sentinel执行；未把旧无断言PASS计入。26项LuaJIT Mock/桥边界/安装器/单人telemetry回归通过；作者构建脚本Ruff通过，未声称历史全分支CI绿。

实机仅上述一会话，结束后只关闭本轮身份核验进程，桥停用、设置逐字节恢复、固定源槽不变；新安装20文件哈希不变。旧cleanup字段名baseline_18_unchanged来自继承helper，实际检查集合已覆盖原18（保存DLL替换）+2新增，不能据旧名字声称旧保存DLL未改。独立新槽保留作证据；当前无游戏进程、RPC锁空。所有本地未提交/历史75脚本保留。

本机备份 `mod.project/research/save_lifecycle_20261105`；发行 `mod.project/release/Save_lifecycle_20261105` 是3文件增量候选，非干净完整包。回退在无游戏安全节点恢复备份保存DLL，停用新增loader；不回写或导入玩家存档。新增null护栏仍是有限证据候选，原失败路径实机未命中。

下一轮本机/分析机聚焦：①补只属于独立夹具的关联对象/队伍销毁最小上下文，证明原生midpoint正常及NULL场景，先审明确SHA；②继续原版setter/私有完整快照所有权方案，证明Lua撤销、生产save借用、普通/渲染用户和外部析构之间的提交/退出合同，再允许有界真正释放；③扩展同场景资源趋势前先确定计数含义，长期压力测试仍未执行。不为追求通过绕过旧ABI/GUI/身份/epoch/16/32/128门禁、不重试异常free。

其余跨区视觉、混箱与三台自然生产由用户晚间验收，暂不自动启动这些测试。共享只有作者源码、小摘要，无原始dump/游戏/DLL/资产/存档/凭据或私人数据。
