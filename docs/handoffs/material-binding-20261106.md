# T60种族法线混入修复候选与扛人跑步报告（2026-11-06）

用户确认修复材质问题，并新增报告：**扛着其他人物跑步时动作怪异**，不是单纯捡起瞬间或静态肩上落点。当前没有人在扛，本轮不操作玩家现场去构造动作。独立修复分支 `fix/t60-material-binding-20261106` 基于生产源PR11 `817830d98b7d6adc4ff66cd6e0304b092a92e2e5`，不覆盖其他分支，不合并main。

## 已确认的实际材质问题

用户先给了同一暂停场景的对照图，石魔穿戴者头盔与腿部出现额外圈纹。用户随后明确授权读取当前进程。两次只读采样确认活动body/private material指针稳定，已核对EXE/Ogre/两相关DLL哈希及PDB GUID/age；只使用QUERY_INFORMATION|VM_READ，没有注入/调用游戏函数/RPC/暂停/写内存/存档。

| 字段 | 人类穿戴者 | 石魔穿戴者 |
|---|---|---|
| mesh | jack_t60_wear_v08.mesh | 相同 |
| diffuseMap | t60_source_d.dds | 相同 |
| main FP | JACK_T60_Day_FP_v091 | 相同 |
| **normalMap** | **human_male_n.dds** | **bone_male_n.dds** |

两个实际材质都仍是对应owner的私有材质。正常应绑定`t60_eye_emission_n_v091.dds`；原种族皮肤法线混入装甲已确认，不是独立腿模或底色图不同。旧快路径仅比较private material指针/owner/female，直接返回0，未复核贴图内容。实际覆盖发生在哪次引擎调用、是否每帧重写尚未抓到，不将“读到错误”当修复完成。

原材质DLL SHA256 `39438e348e7a419c1400d904e6d103b29d70b00709ce642e41a68b95ff15a563`；对应作者C SHA256 `315e7673c38c8c65175ef1abf6476ab017c18f41fac15f112844a93759ce2496`。原始现场地址、角色数据和完整日志仅留测试机，不共享；公共摘要只保留上述资源名和界限。没有上传玩家截图。

## 修复行为与资源约束

在现有0.25秒材质tick中复核私有main pass与normalMap，只在错误时重绑并回读验证；无新轮询，不clone/copy材质、不重新compile/load shader、不改原角色材质、不增加/清零32槽。非目标body/线程/ABI和owner门禁不变；异常shader、缺失/重复单元、回读失败走原失败停止流程。遍历有显式上限，正常状态不写。既有外观/灯预算16/128不变。

候选DLL `T60MaterialBridge_v091_bindingfix_20261106.dll` SHA256 `c9594044aa7f8aa29be085fd51cc2cf30ea0439ca4335f6f0d7ca57d9845d7e8`，搭配本目录Lua loader SHA256 `029ab3dde8d0e320f9fccd048662b6c61036e45a37b30ece8d95ac1abc930bd8`。这是冷启动增量；旧v091已加载时新DLL拒绝bind，不能热替换共享资源组/保留池。安装需先核完整门禁与准确远端HEAD，再备份原loader、放入独立新DLL并切loader，旧DLL原字节保留；当前玩家进程不因此改变。

缓存只读接口`T60_material_binding_status(char*,size_t)` / `JACK_T60_MATERIAL_BINDING_STATUS()`提供checks/repairs/slots/limit/enabled，不新增通用RPC动作或任意地址入口。

## 本轮验证及仍待实机项

- 原作者C的离线反例已证明：模拟同指针纹理变化后旧apply返回0，纹理查询数0；不是单纯自写模型的推断。
- 修复的实际C源码Mock通过人类/石魔漂移修复、修复后no-op、1000次稳定调用无新写入/clone/compile/slot增长，保持diffuse与bodyBlendNormal；day/night、body/线程/禁用门禁、缺失/重复单元、错误shader、回读失败、status缓冲界限均通过。
- `-UNDEBUG` sentinel执行，`-DNDEBUG`负例明确拒绝编译；Windows CI已接同一测试，无Ogre或游戏加载。
- 构建产物在独立进程的缓存status导出smoke与Lua loader语法通过，未调用引擎。
- 本机全仓Ruff、源码/轮子构建安装后的完整pytest、覆盖率>=85%、CLI smoke、实际LuaJIT是发布门禁；准确远端HEAD所有push/PR checks需成功后才安装。具体结果见PR最新回执和小摘要。
- **修复候选冷启动后视觉/持续重写频率/读档回归/FPS：未验证。** 当前玩家游戏运行中不接管/重启/施加动作。只读数据证明旧版错误，不能代作候选A/B验收。

复测先正常冷启动，再读回实际normalMap/FP及缓存repair计数。期望两族均为专用法线，无持续shader编译和slot增长；若repairs持续每tick增加或画面仍闪烁，必须记录引擎覆盖频率并进一步修复，不能只看“调用返回成功”。用户旧档回归与独立测试槽结果分开；不为测试改玩家存档。

## 扛人跑步：当前事实与下一步

当前安装骨架是82骨，包含`pickup`、`carry me`、站立/步行/慢跑搬运、左右支撑片段；`jog carrying left`及派生`jog carrying left-21`的轨道集合、时间和轨道字节完全一致。因此不能宣称“完全没动画”或“派生名漏更新”已构成原因。

已有记录只证明基础移植/调用覆盖，扛着人物跑步的重甲姿态与被扛者同步没有完整自然实机验收。v095的搬运上身以jog为基础并保留支撑臂；快跑下身是另一个已调整片段。上下身时长不同不单独证明错相位，因为FCS还存在synchs/play speed参数。`back_carry_controller`是收武器控制，不是人物搬运适配。

下一次用户自然触发时只读记录：哪个角色/左右肩、速度与伤病、实际carry上身和lower clip名称/权重/时间、被扛者使用片段；对照普通角色同动作，判断支撑臂、躯干、步态相位或被扛者同步。未有动态证据前不盲改骨架、挂点或角色AI。此次材质候选不包含搬运动画修复，报告仍为未验证/待复现。

另一个已知读档故障“附件刷新超时→回退普通外观→角色锁定”曾由用户F11临时恢复，具体等待原因仍缺日志；本次法线修复不宣称解决它，也不宣称完成资源free或二次读档NULL护栏验收。

本机完整门禁结果：130通过/9可选Lua跳过、92.42%覆盖，CLI smoke及额外LuaJIT12通过。发现初始构建工作文件与Git索引仅行尾不同后，已将C/符号头/Lua归一为索引同字节LF，重新构建并重跑原生Mock；旧e749候选保留且不安装，当前c959候选与提交源码一致。


## 最新安装/用户选择

源7f7913d8e976967c2ac357bcfe5440c649734774 / [Draft PR15](https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST/pull/15)全部18项push/PR check-runs success。已备份原material_native.lua，放入新DLL c9594044…并将loader切到029ab3dd…；原v091 DLL39438e…原字节保留，已加载的玩家进程未热更。备份research/material_binding_20261106，release/Material_binding_fix_20261106只两文件冷启动增量。

用户明确选择“暂不重启，先继续玩”。因此实际法线恢复、重写频率、读档和画面验收仍未验证；不自动退出/重启或反复催促。下次用户自然冷启动且现场合适时再只读复核；原用户授权的只读调查不等于允许游戏函数调用或写玩家状态。保留当前照片和原始报告在本机，不上传地址/角色数据。

新接口缓存只读T60_material_binding_status / JACK_T60_MATERIAL_BINDING_STATUS，参见[对应源码说明](https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST/blob/7f7913d8e976967c2ac357bcfe5440c649734774/experiments/material_binding/README.md)。材质候选不包含扛人跑步改动；下一自然场景先读实际carry和lower动画再定点修，不能凭静态片段存在宣称适配通过。
