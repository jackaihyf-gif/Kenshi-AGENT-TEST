# 三工作台分离实机交接（2026-11-05）

用户同意分离拥挤配方。已安装 Craft SHA256 `1f03ee6ccb69a6dae018785bdb53f400178d177b88534ad6eac3dedf95d39182`。修复分支 `fix/station-separation-20261105` 基于 `38310acf6f5380a8357351bf66020f086db7ce61`；构建源见 `experiments/station_split/build_candidate_local.py`。仪器分支 `test-machine/station-separation-20261105` 基于 `b7ea1d4a488694ce10963046b85fbb289e59c2aa`，当前 `ca6ebdaeea1fc86f5d49c11b5d18d477d0c4cc8c`。结果分支和Draft PR1只接收交接，不合并main。

## 数据结果与兼容边界

| 工作台 | 配方 | 技能 | 倍率 |
|---|---|---|---|
| 能量武器100 / 功能110 | 五枪械组件400–440、两枪Energy100/110，共7 | 弩制造38 | 1 |
| 动力装甲200 / 功能210 | 伺服450、结构460、T60 650，共3 | 护甲锻造8 | 1 |
| 新弹药500 / 功能510 | Energy200/210，共2 | 弩制造38 | 2 |

24→26记录；新台复用96181-Newwworld.mod的现有part，10电、4铁板+2电子元件，原枪台15/甲台30不变。310能量武器工程增加新台解锁，320/330原解锁保留。撤回旧110通用2倍补偿后的7组件/两枪工时，弹药工时仍整数1，新510单独2倍。材料配方与3个储具覆盖保持。Energy仍 `e85dbe46581ff0d7f424d745d862a0394ec969914e1701675a09f05b279e3bb2`；未应用仅讨论的激光伤害、容量、重量平衡。可见性DLL仍a5c5c9fe…；原16/32/128不变，无新轮询或资产。

旧台已存在队列/输入迁移未验证。重启前建议完成或取消旧枪台的弹药/装甲部件队列，取走输入材料；这些配方更新后在对应台重新排队，不承诺旧队列自动迁移。本轮不修改玩家存档。Research::load的准确原生反汇编显示会从已完成科技的当前GameData重新读取enable buildings，支持“完成310的旧档冷读可获得新台”这一推断；用户旧档实际菜单仍未验证，不能为此要求导入。天然科研前置仍照常。

## 环境、命令与前置

Windows x64、16GiB内存，游戏子EXE SHA256 `504b362cde850d56afb1cea6f5b7b0ee014d9dd7b47e188599d91c804502cd3e`。`game.root`指真实安装；120条mods.cfg SHA256 `53dedcd285ca49301a9f86d9e2dca927c7172719eaa3ed77709b0c2d9adb9af0`，另4原版依赖。Steam正常权限运行。独立固定单人槽，不是玩家存档；暂停/禁自动保存、GUI线程/身份/epoch稳定后测试。

本机私有 `station_split_evidence` 为 writable workspace 下 station-split-20261105，保留原始报告但不上Git。执行顺序：安装候选回执→安装对应Lua桥→ `python -X utf8 run_native_split2.py` →独立冷会话 `run_native_menus.py` →独立冷会话 `run_native_menus_researched.py`。这些运行脚本依赖本机原生启动固定工具，未发布为通用自动化API。无需启动器手动确认或computer-use。重复执行同输出目录会拒绝以保留证据，不能删除证据后重跑。

新增固定仪器：`craft create-ammo`；snapshot读取实际functionality的三类配方；queue仅接受该台实际声明SID。`craft <energy|armour|ammo>-recipe-menu` 只操作本桥创建台，检查GUI稳定、库存归属和精确CraftingInventoryLayout vtable `EXE+0x16942a8`，经原生QueueButton及newCraftingButton打开原生菜单。`lifecycle single-station-research`复用完整single-telemetry门禁，仅本进程一次完成固定310/320/330；在全量预检后先锁存，再调用原生Research.completeResearch，无任意SID、保存或自然研究声明。ABI针对上述EXE，其他版本未验证。不得用于玩家现场。

## 分阶段实际结果

1. **静态通过**：原24记录字节往返一致；候选26记录回读一致；当前120+4加载序合并无新增未解析引用；储具3记录未改，新增中文UTF8正确。静态原报告保留candidate_only/gameplay未验证，不能把它误当实机报告。混合衣服台ITEM示例来自2333.mod，并非独立原版证明。
2. **受控原生制作通过**：被测仪器 `1cb3c1b271b8ba13d76259dfe718ba502a8e8a52`。原生实际三列表7/3/2；同一工人两制造技能50。每3秒operate步长，融合/电磁弹进度均0.0010999999067，线圈0.0001833332572、激光0.0000916666286，伺服/结构各0.0005499999534，T60 0.00002820511054。两类弹药各产出1、两甲部件各1、T60 1；线圈/枪只采样进度后取消，未完成制品。18次受控work调用用于完成采样，不是自然AI、实际墙钟产速或科研施工搬料闭环；弹药2倍结论结合此前独立A/B及本轮倍率/进度保持。9人物字段保留，零保存写入。
3. **无科研菜单控制组**：被测 `fdc8f07e2321221b9774f69e5ff8eddbc513c890`，三台原生窗口打开但配方空，UI提示需蓝图/研究，和独立槽未研究一致。不是配方已丢失。此轮仅窗口路径通过，配方验收不足。
4. **科研准备后原生菜单通过及代理视觉判断**：被测 `ca6ebdaeea1fc86f5d49c11b5d18d477d0c4cc8c`，另一冷会话固定原生完成310/320/330后，三截图逐一检查，枪7、甲3、弹2的中文名称正确且无串组。截图来自引擎capture，已在本机查看；不是用户人工认可、自然科研或用户旧档解锁结果。[枪](evidence/station-split-20261105/menu-energy.jpg)、[甲](evidence/station-split-20261105/menu-armour.jpg)、[弹药](evidence/station-split-20261105/menu-ammo.jpg)。
5. **离线Mock/边界回归**：当前ca6，`KENSHI_TEST_LUA51`指本机已存在LuaJIT DLL，`python -m pytest -q -p no:cacheprovider -p no:faulthandler tests/test_bridge_boundaries.py tests/test_direct_bridge.py tests/test_telemetry_install.py tests/test_single_telemetry.py`：26通过、0跳过。最初未设置环境变量为17通过/9跳过，后已实际执行这9项。此回归不能代替新native ABI或自然AI覆盖。

各会话连续内存完整保留，小型摘要列起点/稳定冷态/末点/峰值和系统余量，见[evidence JSON](evidence/station-split-20261105.json)。本轮三个冷会话稳定态工作集约4273/4282/4429MiB，私有提交约7637/7475/7649MiB；加载和开窗仍有增长，非同一长期序列，不能据此证明泄漏或低开销。外观累计/保留对象/材质槽未在本轮采集，记未验证、不填0。未设置内存停测阈值；无游戏/RPC异常。三个有效会话均退出、桥停用、设置逐字节恢复、18运行文件及固定槽不变。

## 已保留的问题及最小复现

- 候选准备发现中文编码错误，拒绝候选28aa…未部署；修正到最终1f03…后通过原Reader中文检查。
- 本机脚本命名inspect.py遮蔽标准库，prelaunch导入失败且没启动游戏；重命名disabled后继续，证据保留。
- 首个实机native-split在配方比较处报 `('recipe partition', 'energy', {'3', '1', '2', '4', '5'})`：Lua数组JSON表现为数字键对象，宿主错误迭代键。停止、退出、回滚后修宿主解析用values，再装同一1f03测试通过。不是原生配方或游戏错误。
- 最小菜单复现：普通独立槽→建三台→打开配方可见“需研究”空列表；另会话完成固定310/320/330→同流程应显示7/3/2。自然科研/用户旧档不可由该夹具推断通过。

## 未验证、资源及下一轮

自然科研/建造/供电/取料卸货、旧台已有队列迁移、完整枪械制品、工作点/碰撞、旧档解锁、真跨区、多人体型伤病、长时性能/干净安装都未验证。旧混箱误拿根因仍未确认；生产外观free协议仍未完成，渲染注销不是free。这轮不重跑旧已通过场景、不扩大上限。测试进程已退出、RPC锁空，未留下游戏资源占用；仅原有工作分支和历史75未跟踪脚本，本轮候选/备份/原始证据在本机。

分析机具体任务：①审查210护甲+ITEM混合分派及旧队列迁移；②为真正有界跨区与自然连续队列混箱观察补最小固定仪器，保留门禁；③继续reader/epoch/保存借用/回滚释放协议，提供明确完整修复SHA。修复后本机先核SHA/哈希，再只在对应独立会话测差异，不合并main。

本机备份 `mod.project/research/station_split_20261105`，发行 `mod.project/release/Station_split_20261105` 只有Craft数据增量，依赖原完整模组及既有资产。回退只在无游戏安全节点从该备份恢复fe8；不自动回写存档或改历史清单。共享内容仅作者源码、小摘要及三张独立测试截图，无游戏二进制/存档/凭据/原始报告。
