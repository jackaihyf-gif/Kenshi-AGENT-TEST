# PR #3 与生产基线扩大测试：实机因物理内存余量停测

本轮没有完成扩大验收。**五人冷载已稳定，但在第一轮穿脱之前，宿主机可用物理内存低于预先设置的2 GiB保护阈值，立即停止全部后续实机阶段并收尾。** 这是一项测试资源门禁事件，不是已确认的模组泄漏或PR #3析构失败。没有降低阈值、扩容/清零资源预算或继续尝试其他游戏场景。

- 被审查、离线测试及部署桥源码的完整SHA：**`d2809fd8df7ca4c1d0093bd78c1efd9a01d56b8b`**，核对为 [Draft PR #3](https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST/pull/3) 的HEAD。
- [分析机原生所有权交接（固定提交）](https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST/blob/d2809fd8df7ca4c1d0093bd78c1efd9a01d56b8b/docs/handoffs/native-ownership-20261103.md)。该PR包含已测PR #2作为依赖。
- 生产模组不是此Git仓库的提交：以[证据摘要中的18项运行哈希](evidence/expanded-pr3-20261103.json)标识；`wear_controller.lua` 为 `4f9566ad083512bbd8be6b4c0f282dcb324858f519d023826197174e0e67e826`。
- 使用独立detached worktree `PR3_WORKTREE`；原测试工作区、75份历史脚本、旧DLL、旧探针、旧报告与存档均保留。结果只提交到测试分支，不合并修复或main。

## 测试计划和实际到达位置

计划顺序是：离线门禁 → 五人冷载 → 三轮五人穿脱及每轮内存采样 → 在现有16次外观预算内最多两次既有MIGRATION1重载及后续穿脱 → 独立冷启单人、新槽保存/同槽读回 → 受限镜头远移/返回 → 独立冷启私有完整复制及8次双对象释放/预算拒绝。任意意外、隔离、角色不一致或内存余量不足均立即停止后续阶段。

| 阶段 | 实际执行及资源/数据 | 状态与证据 |
| --- | --- | --- |
| Python离线门禁 | 115 passed、9 skipped（未配置LuaJIT）、0 XFAIL，coverage92.42%，Ruff与Mock CLI smoke退出0 | 通过；不是游戏证据 |
| 原生Mock | Zig0.13.0；显式`-UNDEBUG`及有副作用sentinel；10次Mock进程均通过 | 通过；未调用真实引擎 |
| 新实机候选构建 | 两份未改动的PR #3 C源码和共享头构建AMD64 DLL；导出表符合预期；哈希见下 | 构建/静态通过，**未加载** |
| 五人冷载 | 原生启动器自动确认，真实新RPC；加载既有COLD2、暂停、禁自动存档、绑定五人；epoch1；5人均82骨、ARMORED/rebound、无blocked | 已观察；外观累计5/16、pool_entries5、材质5/32；冷载与循环前两次计数均5，未发生穿脱 |
| 第1轮穿脱之前 | Win32进程/宿主机内存采样触发2 GiB物理余量门禁 | **停测点**；完成穿脱循环0，完成重载循环0 |
| 多轮穿脱/旧夹具重载 | 没有执行任何wear/unwear/reload动作 | 未执行；无斜率或循环增长结论 |
| 单人唯一新槽保存/同槽回读 | 现有受限接口可支持，但资源停测后没有启动此会话，也未创建新存档 | 未执行；不能写成五人组合已支持 |
| 镜头远移/返回 | 现有单人固定句柄探针可支持，但没有执行 | 未执行；本身也不证明角色切区/卸载 |
| 私有完整复制/真实释放 | 新候选和路径绑定准备完成，但没有部署绑定副本、初始化探针或调用trial | **真实删除未执行**，不能以Mock或DLL构建替代 |
| 收尾 | 核对本轮PID、创建时间、实际EXE和会话后退出；桥停用、RPC锁空闲；18项生产哈希及COLD2文件逐文件哈希不变 | 已完成；未写存档、未修改资源上限 |

本轮真实动作仅为 `load:STAGE2_COLD2`、`stage2-pause`、`migration:bind` 及两次 `migration:status`，其他为只读status。没有私有native调用、save、reload、region或wear命令。所有实际RPC成功，角色/控制器没有记录到本轮新错误；人工视觉仍**未验证**。

## 内存数值与证据边界

采样用 `GetProcessMemoryInfo(PROCESS_MEMORY_COUNTERS_EX)` 读取本轮真实RE游戏进程，`GlobalMemoryStatusEx`读取宿主机；每次按EXE路径与创建时间核对PID。物理RAM约15.88 GiB。下面单位为GiB（1024³字节），精确字节在JSON摘要。

| 时点 | 游戏工作集 | 游戏PrivateUsage/私有提交 | 系统可用物理内存 | 系统可用提交空间 |
| --- | ---: | ---: | ---: | ---: |
| 五人冷载稳定、第一轮穿脱前 | 4.2884 | 9.3965 | **1.1566** | 16.1284 |
| 已退出本轮游戏、完成收尾 | 无活动游戏 | 无活动游戏 | **5.715** | 26.077 |

触发条件是物理余量，不是提交空间耗尽。测试前设定 `available_phys >= 2 GiB` 且 `available_page >= 2 GiB` 才继续；前者失败。关键异常为：

```text
expanded_driver.py / cycles -> stage -> memory
AssertionError: Memory headroom below bounded-test threshold
```

只有一个有效游戏内存采样点，退出后的宿主机数值不能当作连续穿脱/读档内存曲线。游戏进程含原版世界及全部启用模组，不能将9.40 GiB提交归因于T60，也不能由此证明泄漏。不能把工作集等同私有提交，或把累计工厂调用数等同活跃堆对象数。

恢复测试需先改善实际宿主机余量，再核对相同SHA和现场；本次冷载点距离2 GiB阈值约差0.84 GiB，达到该值也不保证后续重载峰值足够。保留现有保护值，不通过反复重启或关闭用户无关程序制造通过。现场状态未变时不重复启动相同负载。

## 最小复现与原始证据

以下在独立测试环境进行，路径以配置键或本机别名表示，不依赖另一账号聊天：

1. 检出固定SHA到独立worktree，核对18项生产哈希及实际RE EXE SHA `504b362cde850d56afb1cea6f5b7b0ee014d9dd7b47e188599d91c804502cd3e`；确认没有活动游戏/RPC锁。
2. 运行该提交的 `scripts/install_lua_bridge.py --game <game.root> --install`，沿用原生 `launcher.start_game(..., skip_mod_warnings=True, bridge_dir=<game.bridge_dir>)`，记录新进程所有权。
3. 空菜单调用 `lifecycle / load:STAGE2_COLD2`；等待五人非加载、82骨，再调用 `stage2-pause`、`migration:bind`。通过 `migration:status` 读取角色、epoch、wear_controller和材质。
4. **在发出第一条穿脱命令之前**采样游戏与宿主机内存。若宿主机物理余量小于2147483648字节，驱动立即停止；无需故意制造内存压力。该结果依赖宿主机其他负载，不保证另一时刻必然复现。
5. 保存原始证据，只关闭本轮拥有的游戏，停用桥，核验基线及存档。保持原生产上限16/32/128。

本机驱动与原始证据根：`PR3_WORKTREE/reports/expanded-pr3-20261103`。驱动为 `expanded_driver.py`；现场目录 `session-five` 包含 `preflight.json`、`startup-raw.json`、`rpc-raw.json`、`cold-migration-raw.json`、`round-group-0-before-raw.json`、`memory.json`、`STOP-cycles-*.json`、`post-cleanup-host-memory.json`、`before-cleanup-raw.json` 和 `cleanup.json`。摘要给出关键文件SHA；原始角色/会话数据、桥配置/入口/备份、DLL/EXE和存档不上传。

## 私有候选审查与部署准备（不是实机通过）

审查确认PR #3新增名称缓冲区/双副本独立性拒绝、失败停止锁存、双对象预算预检、NULL回退及readers拒绝。完整保存借用协议仍不存在；零readers不授权生产对象释放。析构异常可发生在部分释放之后，不能把隔离当回收。

以PR #3原始C/头、无`PRIVATE_RELEASE_TEST`宏，使用：

```text
zig cc -std=c11 -fms-extensions -O1 -UNDEBUG -shared <candidate.c> -ladvapi32 -o <new-private-output.dll>
```

- 完整复制DLL SHA：`82e3e3f963974a9e16a43ba688264760be319ec8b8c9bfc2d7b617c3c7c12b43`。
- 私有释放DLL SHA：`d2840d9d29cd4f6cbedd17a0008b5388bbb3677c23f9c6ed983fd1763727181b`。
- 已静态解析两者为AMD64 DLL，complete的11个、release的3个导出符合预期；**没有在进程中加载验证ABI**。

旧probe固定加载旧DLL，不能称作PR #3新产物。准备了全新路径的受限probe及game_ops副本，只绑定指定新路径；完整复制probe不再调用已占用旧文件路径的可选导出；release补采cap9的stopped与有符号返回码。原生源码、固定夹具断言、版本/GUI/epoch/类型/独立性和停止门禁均未改。副本diff与哈希保存在 `native-game`；本轮因停测**没有部署副本**。因此也没有新的外部序列化文件比较结论。

准备生成器最初误把complete探针路径出现次数写成2，实际PR #3中只有1次，导致本地断言拒绝；按源码核对后修正为精确1次。此为部署前工具错误，未调用引擎；保留在 `setup-notes.json`。另发现现有SaveReader对部分旧单人夹具名称产生解码替换字符，后续不能只按名称解码结果证明完整角色保存一致。

## 明确阻塞的组合路径和下一轮任务

| 路径 | 当前限制 | 分析机所需交付 |
| --- | --- | --- |
| 五人新存档保存后读回同槽 | game_ops:430–439只支持MIGRATION1–6，全部已存在；reload只读MIGRATION1 | 独立PR提供唯一受限新槽、不可覆盖、与本轮请求绑定的读回和重新绑定；不删旧槽、不引入任意路径保存 |
| 单人新槽保存/回读 | game_ops:543–568已有固定root和`T60_LIFE_096_*`命名门禁；这条可用路径本轮因资源停止而未执行 | 先准备可比较的单人字段/引用及存档解析证据；保留完整库存未验证边界 |
| 真实角色切区/卸载返回 | game_ops:33–48只把镜头移到+12000并返回；角色原地，五人也不满足单人门禁 | 独立PR设计有界角色移动/取消/返回与实际卸载观测，不扩大现有64单位动作限制或绕过固定句柄 |
| 私有释放+生产穿脱/保存/读档 | 完整reader/epoch/保存租约和恢复协议未接入 | 先给出所有权、借用、回滚及异常停止协议和Mock，再申请明确SHA实机验证；不能直接解除生产释放开关 |
| 128灯池真实占用监测 | 现有灯探针可读活跃灯数，不能给出整个保留池占用；五人migration状态不含该计数 | 提供有界只读计数接口，明确active/retained/cumulative语义；不能把上限或活跃数伪装成池总数 |

下一次复测仍先核对修复SHA和宿主机余量，在各自独立进程中测试生产基线和私有候选。私有部分先验证完整复制、源字段及身份不变，再至多8个双对象trial和不分配的预算拒绝；任何意外立即停测，不换epoch、清计数或重试free。当前这些后续步骤全部**未验证**。没有合并任何PR或main。
