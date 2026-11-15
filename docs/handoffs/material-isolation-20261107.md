# 私有法线隔离修复与用户确认 — 2026-11-07

结果：用户在正常重启读回原来的多角色场景后明确反馈**“已稳定，不再跳动”**。当前保留隔离修复；这项用户视觉认可与单人绑定测试分开记录，不代表生产资源回收/完整模组验收完成。

## 原因、版本与安装

v1源PR15 f78bf47，DLL c959、loader6fca在原GUI tick反复将normalMap改回专用法线。用户运行时跳、暂停稳定；授权只读40点约4秒实际捕获同一批私有材质在bone_male_n.dds与t60_eye_emission_n_v091.dds交替，repairs1048→1053，slots5保持。此前另一暂停12点repairs364不变、纹理稳定，不混写成采样内新增364次。资料含地址仅本机留存，不上传。

新源 `7b2c22a5a9a5dabfc10f761d563a34f3d603f737` / fix/t60-private-normal-isolation-20261107 / [Draft PR17](https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST/pull/17)，全部18项准确HEAD push/PR检查success。仅将克隆材质法线单元改为JACK_T60_PrivateNormal_v091，保持原索引1、13单元的数量/顺序、纹理和HLSL register(s1)，不改shader或原角色材质。真实引擎存在按normalMap名字查找的更新路径及下游NULL单元保护；私有单元不再匹配该皮肤语义。稳定tick只检查，不周期回写；私有名/索引/纹理意外变化fail-closed，不反复争写。无新增轮询、texture unit、材质槽、clone循环、shader编译循环或预算返还/扩容。

当前DLL `T60MaterialBridge_v091_isolatednormal_20261107.dll` SHA256 `d9f2b374765f5a312b596d33f4d2600dffd1f03c49b264a816c8d3a74d379f74`；loader SHA256 `711479c7bb6bc2dec1dff409ab12f6ea6aca3b5f3721a5fa29a3bb5b66df42cf`。Git同字节LF构建，冷启动拒绝原桥/v1已加载；loader watcher保留已加载原桥/v1，cold才选新，禁止热换池/资源组。新源全仓Ruff、sdist/wheel安装完整pytest130通过/10可选Lua跳过、92.42% CLI覆盖、smoke与实际LuaJIT13通过；实际C Mock覆盖1000模拟种族更新、稳定无写/clone/compile/growth、两旧桥拒绝、day/night、读回/索引/漂移门禁，断言sentinel和NDEBUG拒编译接Windows CI。Mock不等于真实引擎覆盖所有更新路径。

只读仪器 `b3e3964bfdabd2d3796a377f8b6ab8d08a8ff36d` / test-machine/material-observer-20261107 / [Draft PR18](https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST/pull/18)，全部14项checks success。既有single-telemetry只扩展固定三种已知材质DLL全路径GetModuleHandle，恰好一个/实际路径一致/已存在slots导出/0..32整数；不LoadLibrary。原单人、暂停、固定读档证明、GUI/epoch/身份/加载和上限全部保留，未加动作。117通过/11可选Lua跳过、92.42% CLI覆盖、smoke及实际LuaJIT14通过。

备份research/material_isolation_20261107，release/Material_isolated_normal_20261107是两文件增量，非全包。骨架仍37246540、cache gate仍eccc；9cf扛人候选已撤回，禁止重装。旧c959/6fca回执保留历史，不按旧哈希误报当前安装损坏。

## 受限实机阶段与停止原因

前置：用户正常保存退出；确认无游戏/其他执行者/RPC锁；完整120 mods.cfg基准53dedcd2、正常Steam保留，临时仅关闭autosave。使用固定独立T60_LIFE_096_ORDINARY_D读取，没有玩家存档访问/新存档或保存命令；16/32/128保持。执行本机固定单人驱动及只读绑定观察，原始路径以local_evidence.material_isolation代称，关键命令为既有lifecycle load固定槽、wear、single-telemetry、resume/pause、single-visibility-rebuild一次。startup等待有界120秒，动作/身份门禁未减弱。

| 阶段 | 采样点 | 底层checks | material slots | 专用法线 | unexpected_drifts |
|---|---:|---:|---:|---|---:|
| 初始穿甲暂停 | 12 | 24→31 | 1 | 全部正确 | 0 |
| 运行采样 | 40 | 55→70 | 1 | 全部正确 | 0 |
| 一次原生模型reload后 | 12 | 94→100 | 1 | 全部正确 | 0 |
| reload后运行采样 | 40 | 121→136 | 1 | 全部正确 | 0 |

实际是**104个采样点**；底层checks总跨度增加112，不能把它当112个采样点。全部活动body/private material/模块hash/PDB对应通过。候选binding_repairs是优化掉的常量，未从内存取值，JSON明确null/未采样，不能填0冒充采样；无周期写路径由审核源码/实际C Mock支持。原生unexpected_drifts真实读0，槽数真实读1。

61次RPC无错误、无材质DISABLED/缓存错误/穿甲timeout。96内存点：稳定普通态working4245.1MiB/private9477.2，末4815.7/10790.0，最低物理余量3398.2MiB；只记录未加阈值，内存增加不单独判断泄漏或长期收敛，FPS未测。

后段测试人物combat=true，dead/unconscious/injured=false，按预定清洁场景guard停测并回退。**整场passed=false的STOP/cleanup保留**，卸甲恢复未执行，不能声称全部计划通过。材质绑定子项已在运行和模型reload后完成且稳定，战斗不是材质故障；收尾复核接受该有界子项后，在再次确认无游戏时重新备份并启用7114 loader。该决策另记installation.json，不篡改STOP。所有自建进程已关闭、测试桥停用/原disabled入口恢复、配置逐字节恢复、独立源槽哈希不变。

先前两次会话因私有诊断兼容问题停止并回退：①EXE文件名大小写；②优化后常量计数无PDB变量。不是引擎/native错误；未隐藏重试。修正后的第三次才取得上表资料。未将缺失计数/未执行卸甲改成通过。之后用户在自己的多角色场景视觉确认不再跳动；未操作/暂停/关闭用户游戏或把用户确认写成代理自动化覆盖。

## 后续范围与接口注意

当前解决运行时法线来回切换；用户视觉认可不替代长时FPS、真正区域卸载返回、多体型/伤病/倒地等全矩阵。一次reload不是切区。未完成卸甲恢复本轮不倒填旧结果；没有新异常不反复跑旧穿脱/保存/私有free试验。

新cached接口仍为T60_material_binding_status / JACK_T60_MATERIAL_BINDING_STATUS，新增unexpected_drifts字段；原slots ABI不变。PR18只读single-telemetry可用于独立槽计数；**旧migration:status仍有ffi.load原v091的历史路径，不可在新版运行时调用**，否则会映射不需要的旧桥并造成多模块歧义。需要该观察时先改成只读GetModuleHandle+严格已知版本选择并经检查，不为读计数加载旧桥。

分析机请审：①私有名字与引擎更新/NULL guard边界，保留fail-closed；②未来迁移status去除加载旧DLL副作用；③在平静受限场景补未执行卸甲与长期观察。不要合并main，不把这项修复当生产外观free或原NULL崩溃根治。小型[脱敏证据](evidence/material-isolation-20261107.json)，原始报告/DLL/游戏代码/存档/地址不上传。
