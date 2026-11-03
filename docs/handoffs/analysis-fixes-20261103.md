# 分析机修复交接 — 2026-11-03

基于测试机分支 `test-machine/real-bridge-handoff-20261103` 的 `d8d8721`。
修复分支 `fix/bridge-state-deadline-ci`；PR 指向测试分支，不合并 main。

## 修改范围

- KenshiAdapter 从 `detail.wardrobe["14"]` 的组件 ID 和严格布尔 `equipped`
  判断腰甲；上衣槽不再参与判断。缺失或畸形的细节表示未确认装备。
  `ready` 同时要求非空角色字典，缺少 phase 返回 unknown。
- 动作请求在 session 查询后、写请求前计算 expires，并使用同一个 Deadline
  的剩余预算。预算耗尽时不发布动作，释放客户端锁。
  拒绝参数覆盖协议字段；动作响应必须匹配刚查询的 session。
- 两个严格 XFAIL 已改为普通回归测试，新增缺字段、会话不匹配、预算耗尽、
  observe 证据边界和假的 Win32 API 启动器测试。
- 修复 Python 白名单 Ruff 问题，不改变规则或85%覆盖门槛。
  Lua 武器夹具移入 tests/fixtures，运行库改由 KENSHI_TEST_LUA51 提供。

## 验证与限制

本机离线结果：115 passed、9 skipped、0 XFAIL；覆盖率92.42%；
Ruff 与 CLI smoke通过，保留85%门槛。远端矩阵结果见修复PR检查。

分析机没有游戏。启动器测试拦截所有 DLL 和进程创建调用，仅验证控制流程。
observe 成功只表示桥报告已加载角色；不证明身体、附件、动画或外观完成，
`game_verified` 继续为 false。真实启动器和通用 GameAdapter 的能力仍有区别。

无 LuaJIT 环境时9项原生库相关测试明确跳过；本次未验证 LuaJIT 原生异常隔离，
也未审查或修改私有快照/析构候选、模组池保护或资源回收协议。
原始测试机交接文档保留不变，以免把历史实机证据改写成此次修复的验证。

## 测试机最小复测

1. 从修复 PR 核对完整 HEAD SHA，在独立 worktree/导出目录测试，保留原工作区。
2. 安装该版本，运行 pytest、Ruff、85%覆盖门禁、scripts/smoke.py；
   未配置 LuaJIT 时保留跳过说明，配置后另记原生测试结果。
3. 沿用已审查的独立夹具，检查腰部 slot14 的 ID/equipped 与适配器回读一致；
   普通上衣变化不能影响判断。observe 保持 game_verified=false。
4. 慢 status 与预算耗尽用离线回归验证，不主动卡住真实游戏线程；
   真实动作只按现有门禁执行，检查同一 session 响应，并记录被测 SHA。
5. 更新测试机交接证据，仍不运行私有 native delete 或扩容池上限。
