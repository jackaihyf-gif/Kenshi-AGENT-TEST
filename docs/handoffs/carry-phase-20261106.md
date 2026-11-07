# 2026-11-07 最新覆盖：已安全安装，实际动作仍待验收

10:13香港时间确认无Kenshi进程、无其他执行者、无RPC锁且桥停用后，重新核远端PR16仍为 `9781167f8b491db30b7612dc62643ec36bfe93c8`、全部16项push/PR检查success。原资产37246540与暂存9cf7ab19及历史原骨架备份逐一匹配；新建额外备份后，在替换前再次确认无Kenshi进程，仅原子替换模组私有骨架一个文件，安装后SHA256 `9cf7ab197fe155b38fdb4d0e20d49527784d4cfc0fa9b79c97ba11f1a38b0589` 回读一致。下方“仅暂存/未安装/玩家游戏仍运行”是前日历史，当前已安装。

本机备份与回执为research/carry_phase_install_20261107；原release/Carry_phase_fix_20261106/staging.json保留初始暂存历史，不覆写旧回执。本轮无源码/全局FCS/DLL/Lua/预算改动、无游戏启动/角色操控/RPC/存档写入。PR1/15/16、生命周期PR11/12远端明确SHA未变化，全部Draft，不合并main。

实机修复后的左扛jog视觉、手臂支撑/被扛者同步、普通jog/右扛/静止/捡起回归仍为**未验证**。当前受限仪器PR12 `1334fc453f3886e6299b66d909cdb10f9c08f82d` 的integration/kenshilua与src/kenshi_test源码未接入人物pickup/carry动作与运行组合（carry检索只命中getTotalCarryWeight）；因此自动动态验收**接口阻塞**，没有借任意游戏调用、改玩家状态或临时绕过门禁来复现。下次用户自然冷启动后可先人工观察左扛慢跑；有明确新受限夹具SHA再用独立测试槽验收。既有离线运动学与Mock通过不替代这一步。

材质c959/loader6fca仍为前日已部署候选，正常冷启动效果/反复覆盖频率/FPS继续未验证；生产free/附件超时blocked/原NULL崩溃根因不因此解决。

--- 以下为2026-11-06分析与暂存历史 ---

# 动力甲左扛慢跑躯干相位修复 — 2026-11-06

当前目标：修复用户“濑户扛人跑步时上半身幅度非常大”。源 `9781167f8b491db30b7612dc62643ec36bfe93c8` / `fix/t60-carry-phase-20261106` / [Draft PR16](https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST/pull/16)，基于生产源PR11 `817830d98b7d6adc4ff66cd6e0304b092a92e2e5`，不合并main。原始人物地址/状态和完整日志只留测试机，不上传。

## 证据、原因与修复边界

用户自然扛人过程中，只读8份动态采样：`jog carrying left-21`权重约0.95，`jog lower-11`约1，两者时长同为1.119057秒，固定错开半周期。之后的mask采样已回到静止，不能声称获得了慢跑完整blend mask。FCS左扛`sync offset=.5`（实际字段名`synch offset`），普通jog和右扛为0；当前动力甲左扛Spine/Spine1/Spine2/Neck/Head轨道与普通jog upper逐字节相同。适配躯干时保留了不适配新轨道的原左扛半周期偏移。

已安装原82骨的离线120点前向运动学复现同类过量摆动：躯干Spine2角度峰峰值54.15°，移除不匹配后21.23°；头部40.35°→11.49°。实际候选在原引擎半周期下复算也为21.23°/11.49°，与普通慢跑躯干一致。此为骨架离线计算，不是完整实时混合或用户视觉验收；约5% walk贡献、动态mask及被扛人物同步尚未全部还原。

候选仅将T60私有骨架`jog carrying left`与`jog carrying left-21`的5条躯干/头颈轨迹移半周期，补偿原引擎相位。两别名共10条轨道变化；原支撑臂/手/肩甲/武器挂点、双腿、右扛、捡起和被扛者动画、其余所有轨道、绑定层级/时长逐字节保留。**不修改全局FCS左扛记录**，不影响普通角色，不新增运行时脚本/轮询/DLL/分配，不改变速度或16/32/128上限。

## 执行与实际结果

前置：本机作者资产、验证过的82骨v1.80布局，精确输入SHA；无引擎调用。执行`python experiments/carry_phase/build_candidate.py --input <author-skeleton> --expected-sha256 37246540fc1c985f6b95041595688463acc82bca23d0b05e248e5e9ead711609 --output <new-candidate.skeleton>`。预期只改上述10条轨道，实际生成候选SHA `9cf7ab197fe155b38fdb4d0e20d49527784d4cfc0fa9b79c97ba11f1a38b0589`，完整保留审计与前向运动学断言通过。

全仓Ruff、源码/轮子构建并安装后完整pytest **138通过/9可选Lua跳过，CLI覆盖92.42%**，CLI smoke和额外实际LuaJIT12通过。8项新增合成测试覆盖半周期补偿、两别名、未改字节与错误轨迹拒绝；不加载游戏资产到CI。远端准确HEAD全部16项push/PR检查success。CLI覆盖率不是动画视觉覆盖率。

## 最小复现与下一步验收

旧版：穿T60→自然左肩扛人→以触发jog的速度移动，观察胸甲/头盔左右甩幅；对比同角色普通慢跑、静止左扛和右扛。实证来自玩家自然操作，本机没有发动作/暂停/存读档/RPC。当前玩家游戏及原骨架仍在运行，候选**尚未安装**；用户明确暂不重启，不热更骨架、不接管角色。

下次无玩家游戏时，先核PR准确SHA/CI与候选哈希，备份原骨架后只换这一文件，再正常冷启动。优先相同左扛jog场景，确认躯干甩幅、手臂支撑和被扛者位置；再看普通慢跑/右扛/静止/捡起是否保持。若实机仍异常，记录实际clip/权重/相位及动态mask，继续定点分析，不能凭离线幅度减少称整项通过。

希望分析机审查：①半周期补偿范围与FCS/两别名一致性；②支撑臂mask、残余walk混合及被扛者同步；③生成器拒绝门禁。无需重跑历史读档/free试验。生产free、附件超时锁定、二次读档NULL原根因仍未解决。

本机证据键：本聊天`seto-armor-20261106/carry-live-and-bridge-state.json`、`carry-live-mask.json`、`carry-phase-audit.json`、`carry-phase-candidate-audit.json`、`carry-phase-preservation.json`、`qa-carry/`；小型脱敏[摘要](evidence/carry-phase-20261106.json)。资产/原始报告不入Git。玩家进程由用户保留，测试桥仍停用；无自建游戏，无测试RPC锁。
