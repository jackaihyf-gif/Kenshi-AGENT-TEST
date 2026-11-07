# 2026-11-07 故障覆盖：单骨架安装回归已撤回，用户确认显示恢复

上午单独安装9cf7ab19候选漏掉原生动画缓存门禁的精确SHA绑定。用户重启10:27日志先报`T60 cache bootstrap refused -31`，随后锁存重入`-30`，`t60_wear.lua`在注册穿甲控制器之前return；因此全套动力甲不显示且F11无效。这与此前附件刷新超时/blocked不是同一个故障。

作者cache_preload_gate.h明确把骨架SHA256绑定37246540fc1c985f6b95041595688463acc82bca23d0b05e248e5e9ead711609，安装的T60CacheWarm_gated.dll为ecccbfebb61a689a8cd870d68e0fe913513ea04a9c2926c59b37e46a37702e9a。只换骨架虽然离线轨迹检查通过，仍不满足真实启动依赖；这是本机部署遗漏。**9cf候选已撤回、禁止按下方已安装记录重装。**

用户正常保存退出后，10:32保留失败日志/坏候选备份，双重确认无游戏进程，仅原子恢复37246540原骨架；未改缓存DLL或绕过门禁。一次独立主菜单冷启实证：state2/allowed1/animations200/warmed200/errors0，WearLab控制器Ready；未加载世界、未操作人物/RPC或写存档。菜单夹具40秒等待偏短，实际约51秒启动，早期WM_CLOSE未退出加载进程；同一会话随后确认初始化并核EXE身份正常关闭，没有重开第二轮。原始失败与夹具超时记录均留本机，不能隐藏为首次全部通过。

**用户随后正常启动读档，明确反馈“已恢复显示”。** 这是用户视觉认可；主菜单日志只证明启动门禁/注册恢复。扛人候选并未保留，原动作过大仍待配套修复。材质修复实际跨族对照/长期覆盖频率未因此验证；生产free/原NULL/旧附件超时不因此解决。

防回归：PR16新增只读`experiments/carry_phase/preflight_install.py --candidate-skeleton <candidate> --cache-gate <actual-installed-DLL>`，只有审核过的精确DLL/骨架对通过；当前372+eccc通过，9cf+eccc必须拒绝，未知DLL拒绝，不调用引擎、不写文件。生成器报告明确标记现门禁下不可安装。配套native gate必须独立审核、完整质量门禁与冷启动证据后才登记新pair；不能简单放行哈希或屏蔽Lua错误。防回归源f49101f63dece60cff244c348c3b0455c281d3e0 / Draft PR16，准确HEAD全部16项checks success；全仓Ruff、sdist/wheel安装完整pytest143通过/9可选Lua跳过、92.42%覆盖、CLI smoke及实际LuaJIT12通过。首次全量有1项因本机临时路径超长失败，失败记录保留，使用短临时目录完整重跑后全过，没有降低门槛或跳测试。

当前本机research/cache_gate_regression_20261107保存回滚回执/失败日志，当前聊天cache-gate-regression-20261107保存菜单记录与result；不上传原日志/地址/资产。旧staging/安装回执完整保留为历史。下一轮先读本段和Agent.md，不再把9cf视为已安装或可复测修复；用户游戏只离线，不接管。

--- 下方安装/暂存记录均为历史，冲突以本次回滚为准 ---

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
