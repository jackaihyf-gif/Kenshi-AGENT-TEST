# KenshiAdapter 第二阶段接入约定

最新双机交接见 [test-machine-latest.md](handoffs/test-machine-latest.md)。下面的第一阶段设计记录不能作为当前实现能力证明。

## 当前代码的实际边界

| 入口 | 实际实现 | 未实现或未验证 |
| --- | --- | --- |
| `KenshiAdapter.launch` | 检查 EXE 并通过 RPC 附加现有会话 | 不启动、不拥有游戏进程 |
| `get_state` | 读取 phase 和简化装备判断 | 腰部组件被误按 upper 判断；不返回完整库存/外观判定 |
| `press_key` / `screenshot` | 明确返回 FeatureUnavailable | 通用 I/E 流程与适配器截图未实现 |
| `stop` | 附加模式不关闭用户进程 | 不等于拥有完整进程回收器 |
| 独立 `start` | Windows 原生启动器握手及新 RPC 回包检查 | 工具返回初始化成功不等于 Mod 验收成功 |
| 独立 `live` / `LuaBridge` | 固定语义操作和专项受限测试 | 不自动补全 GameAdapter 方法；部分高级目标仅 Python RPC 暴露 |

`observe` 的 ready 当前只表示观测到角色，不证明身体加载、附件、动画或视觉完成。`game_verified` 仍为 false。默认 CI 不依赖游戏，LuaJIT Mock 也不属于实机测试。

本机集成版已实现可选 KenshiLua 文件 RPC 后端，支持实际状态读取和固定语义控制命令；
`start` 可通过原生命令确认启动器，并在显式 `--skip-mod-warnings` 时确认已识别的 Mod 警告。
2026-10-26 已实测确认中文 Mod 警告后进入主菜单，获取真实新会话 RPC 回包。
详见 [本机接入记录](local-t60-integration.md)。

未配置 `game.bridge_dir` 时仍返回 `not_implemented`；缺失游戏路径返回 `game_missing`。
已通过 `live new-test/finish-editor` 创建并进入固定测试开局，
通过 `live capture` 和记录脚本获取真实引擎截图。旧 armor 套件的 I/E 映射仍未集成。
本机 v0.8.2 已实测但未通过动作验收，详见本机记录；工具可用与 Mod 合格是两个结论。
以下职责表和未实现清单保留为第一阶段设计记录，当前支持范围以本机接入记录为准。

## 接口及职责

| 方法 | 契约 | 下一阶段工作 |
| --- | --- | --- |
| `launch(deadline)` | 只创建并记录自身拥有的游戏会话 | 验证安装和版本、启动参数、记录 PID 和窗口 |
| `press_key(key, deadline)` | 对正确且已获焦点的目标窗口发送输入 | 语义操作到可配置按键映射、焦点确认、按键释放 |
| `get_state(deadline)` | 返回实际观测到的状态 | 探索可验证的状态来源；不能根据“按键已发出”推断装备成功 |
| `screenshot(path, deadline)` | 输出真实捕获与 `simulated=false` 元数据 | 验证 GPU 窗口捕获、黑帧检查、目标窗口核对 |
| `stop(deadline)` | 幂等地释放自身资源 | 只清理自建 PID，保留原有进程和用户存档 |

`Deadline.remaining()` 使用单调时钟。所有外部进程必须通过参数数组启动，设置 `timeout=remaining`，
不得拼接 shell 命令。对无法保证及时返回的 SDK，应使用可终止的工作进程隔离，而不是遗留后台线程。
主运行、失败截图、清理分别有预算；保留原始失败，即使诊断截图或清理也失败。

## Universal Modder 评估入口

参考项目的 [`um win`](https://github.com/rehan-remade/universal-modder/blob/main/um/win.py)
提供 Windows 自动化相关命令，可作为后续后端候选。上游能力不等于本项目已经集成或 Kenshi 已验证。
本项目第一阶段没有执行这些命令，也不要求安装该工具。

接入时先记录上游 commit / 版本与许可证，再核对安装方式、命令参数、超时行为、截图输出和窗口识别。
不要未经核实就把上游 CLI 当成稳定 Python SDK，或假定存在 Kenshi 专用状态接口。

## 明确待实现项

1. 由用户配置游戏、Mod、测试存档、外部工具路径；不扫描或硬编码 Steam/Blender 路径。
2. 只在获准的游戏机器上验证安装、启动、窗口/PID 归属、退出及崩溃处理。
3. 使用可丢弃的独立测试存档，事先备份；确定安全停止行为和超时后的进程回收。
4. 实现有焦点验证的输入与真实状态观测，定义稳定的 armor 测试起始条件。
5. 捕获真实窗口并排查黑帧/错窗；保留时间、工具版本、游戏版本、Mod 版本和失败证据。
6. 扩展资产解析前确认 Kenshi 使用的 OGRE serializer 版本；增加 chunk、骨骼、权重和引用校验。
7. 将真实测试标记为显式 opt-in，保持默认 GitHub Actions 完全不依赖游戏。
8. 增加专用真实集成测试，再评审报告中的 `game_verified` 语义；不能只改标志绕过验收。

当前 armor suite 的 `I` / `E` 是模拟操作约定，没有验证为 Kenshi 实际按键映射。
真实接入时可重构为语义动作接口或可配置映射，同时保持测试断言和后端实现解耦。
