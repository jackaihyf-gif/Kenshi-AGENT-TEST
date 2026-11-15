# 运动头灯调查：混入战斗，未作整项通过

固定被测源码 **`d2809fd8df7ca4c1d0093bd78c1efd9a01d56b8b`**；PR #3 HEAD本轮复核未变，没有新的修复PR。当前生产文件和16/32/128上限保持，未调用私有释放、保存或切区。用户取消2 GiB线后，本轮内存仅记录。

原计划中真实角色跨区卸载仍缺接口，因此本轮推进可用的单人夜间有界运动头灯，并针对实际断言失败做两个独立对照。**主试验退出1，旧失败不改写为通过。** 没有游戏/RPC错误；失败来自驱动末尾对原始技能恒等的断言，进一步查出夹具混入战斗和弹药消耗。

## 实际执行和结果

使用既有单人ORDINARY_D、穿甲、power status、camera、capture、move/resume/pause/halt/release接口。源槽已经是夜间，本轮没有快速调时。每次移动命令半径小于64、租约20秒，没有强制传送或关闭AI。

- 前进位移约 **8.5509游戏单位**，返程停下距起点 **0.6211单位**。
- 15次灯采样均active=true、active count=1、native faults=0；Lua created转换计数始终1、removed始终0，身体82骨。
- 每次有效力量/原始力量比约1.5，没有观测到这个倍率累乘。原始力量 **50.75684738→50.75749969**；原始敏捷 **50.23997498→50.24458313**。
- 姓名、逻辑/视觉种族、性别、发型、剃发、身体文件等可比字段不变。
- 第11号power采样（从0计数，返程期间）明确 `combat=true`，当前武器为 `100-JACK_EnergyWeapons.mod`；随后第12号采样中 `200-JACK_EnergyWeapons.mod` 弹药 **1→0**。这不是纯移动场景，不能将敏捷变化直接归因于T60或视作已确认的自然经验来源。

原始失败：`run_lamp.py / run: AssertionError: ('character drift', 'raw_strength')`。完整往返及截图已在此断言之前完成，之后立即退出本轮游戏，没有在异常现场继续测试。

## 两个独立对照

均从相同原始单人槽冷启，不装备T60、不调用power诊断，不保存。

| 对照 | 实际位移 | 原始力量变化 | 原始敏捷变化 | 已确认范围 |
| --- | ---: | ---: | ---: | --- |
| 无甲静止4秒 | 0 | 0 | 0 | 静止的这4秒未出现同样变化 |
| 无甲步行6秒 | 7.1816 | +0.00128174 | 0 | 力量变化也能在未穿甲移动中复现 |

因此“只有穿T60才发生力量变化”不受数据支持；运行中的力量不能直接套用暂停穿脱的恒等断言。具体经验字段没有正式回读，不能把经验来源写成已证实。敏捷目前只在混入战斗的穿甲试验里变化，缺少干净对照，不修改生产敏捷/力量逻辑来迎合测试。

静止控制的原result.json曾含一条错误的模板解释文字（称观察到变化），与两个delta=0矛盾；数值及RPC才是证据，本共享汇总已去掉该解释，原文件保留，不据模板作因果结论。

## 诊断与截图边界

power.stats采样前后：`skillMultRanged=4`、`skillBonusPerception=30`、`skillMultDexterity=1`保持；有效力量钩子报告factor1.5、faults0。截图弩/感知面板数值变化与当前武器、战斗、照明、UI缓存的上下文尚未隔离，不能据截图直接认定倍率叠加。

更重要的是，**power status不是严格只读**：现有 `_G.JACK_T60_POWER_PROBE` 会sync并normalizeInventory，可能校准护甲实例并重算装备加值。后续只读诊断接口不应直接复用它来声称“采样完全不干扰状态”。关联Lua及C参考源码已补到[审查快照](source-baseline-20261103/README.md)，C与安装DLL的逐字构建对应尚未重建；探针的base_writes等报告也不是全引擎写入监视证明。

选定引擎原始截图，未裁剪或生成编辑：

- [运动前](screenshots/moving-lamp-before-20261103.jpg)
- [前进中](screenshots/moving-lamp-forward-20261103.jpg)

可见眼部发光和角色运动。场景附近有营火、左侧有RE_Kenshi面板；亮斑无法唯一归属头灯。现有探针不暴露灯节点世界坐标，**精确跟随、无漂移及全灯池保留数未验证**，不能将active count=1称为128池占用总量。

## 驱动修正与验证

新增纯离线 [scene_guard](../../experiments/motion_fixture/README.md)：每次采样拒绝战斗、攻击、伤病、弹药数量或电量变化；未知/缺失字段拒绝，不默认0，不改变游戏AI。

- 15项针对真实混杂条件的回归测试通过，所改Python Ruff通过。
- 对实际旧RPC离线重放：首先在power采样11拒绝战斗，采样12及之后拒绝弹药变化。
- 本机保留原run_lamp.py；另备v2驱动，仍检查敏捷与身份字段，原始力量改作差值记录。**v2未重新实机执行**；新guard也尚未接入正式CLI/桥，不能把离线修正算实机重验。

复现命令：`python -m pytest -q tests/test_motion_scene_guard.py`；`python -m ruff check tests/test_motion_scene_guard.py experiments/motion_fixture/scene_guard.py`。没有修改生产源码或降低原生门禁。

## 证据与收尾

[聚合摘要](evidence/moving-lamp-20261103.json)含原始SHA、属性差异、逐次战斗/弹药、对照和清理结果。三组连续内存：[运动灯](evidence/lamp-lamp-memory-20261103.csv)、[无甲静止](evidence/lamp-standing-memory-20261103.csv)、[无甲移动](evidence/lamp-walk-memory-20261103.csv)。本轮共240点；运动灯工作集峰值4720.25 MiB、私有提交8247.70 MiB，仅一次短测，不能据此做泄漏或整机FPS结论。

本机原始目录：`PR3_WORKTREE/reports/moving-lamp-20261103`、`standing-control-20261103`、`unarmored-walk-control-20261103`。每次游戏退出、桥停用、RPC锁空闲、临时设置恢复，18项生产哈希及固定COLD2文件不变。没有新存档或原始数据上传，旧75份专项脚本保留。

分析机下一步：正式整合非战斗夹具守卫，并提供无营火/安全环境或经审查的独立夹具；补有界只读灯节点位置、单人资源计数和经验语义可观测性；拆开power校准与只读快照。核对新SHA后再做最小干净复测。生产保存/借用/回收协议和真正切区接口仍独立待办，不绕过。
