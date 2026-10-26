# Kenshi Test CLI

第一阶段：在**没有 Kenshi** 的 Windows 电脑上开发和验证 Mod 自动化测试基础设施。
使用 Python 3.11+；运行时没有第三方依赖。无需游戏、Steam、Blender、API Key 或管理员权限。

当前实现：CLI、严格 TOML 配置、MockAdapter、armor 模拟流程、异常与超时处理、JSON / Markdown
报告、OGRE 静态检查基础框架、pytest 和 GitHub Actions。
`KenshiAdapter` 是明确拒绝执行的接口占位；真实启动、输入、状态识别、截图均未实现。

## Windows 快速开始

在 PowerShell 中进入源码目录执行：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
# 仅修改当前终端 PATH，无需激活脚本或修改 ExecutionPolicy。
$env:Path = (Join-Path (Get-Location) '.venv\Scripts') + ';' + $env:Path

kenshi-test doctor
kenshi-test run --adapter mock --suite armor
kenshi-test report --latest

python -m pytest
python scripts/smoke.py
```

三条验收命令在无游戏环境中应返回 `0`。`doctor` 显示游戏缺失是正常情况，默认仅检查离线就绪状态。
报告保存在 `reports/<UTC时间-唯一ID>/report.json` 和 `report.md`。
截图是本程序生成的 SVG 示意画面，带有明显的 **MOCK / SIMULATED FRAME / NOT KENSHI** 标识。
它不是屏幕抓取，也不是游戏渲染。截图链接相对于报告，可整个目录复制到另一台电脑查看。

## 模拟测试和退出码

```powershell
kenshi-test run --adapter mock --suite armor --mock-scenario failure
kenshi-test run --adapter mock --suite armor --mock-scenario timeout --timeout 0.2
kenshi-test run --adapter mock --suite armor --mock-scenario missing
kenshi-test run --adapter mock --suite armor --mock-scenario crash
kenshi-test run --adapter mock --suite armor --mock-scenario screenshot-error
kenshi-test report --latest --format json
```

| 退出码 | 含义 |
| --- | --- |
| 0 | 命令成功；Mock 成功只证明模拟流程通过 |
| 1 | 测试断言失败或资产基础检查失败 |
| 2 | 参数、配置或测试套件无效 |
| 3 | 适配器、文件读写、清理或意外错误 |
| 4 | 测试超时 |
| 5 | 游戏缺失或未配置；Mock missing 场景同样返回此码 |
| 6 | 真实功能未实现，或资产类型均无可用检查器 |
| 130 | 用户中断 |

`report --latest` 的退出码表示“读取是否成功”，不复用被读取测试的退出码；自动化应检查 `run`
的退出码或 JSON 的 `exit_code`。`--latest` 选择按运行开始时间排序的最新完整报告，忽略未完成目录；
如果最新报告损坏则明确报错，不偷偷返回旧报告。

## 配置

```powershell
Copy-Item kenshi-test.example.toml kenshi-test.toml
kenshi-test --config kenshi-test.toml doctor
kenshi-test run --config kenshi-test.toml --adapter mock
```

配置来源顺序：显式 `--config` → `KENSHI_TEST_CONFIG` → 当前目录 `kenshi-test.toml` → 内置默认。
字段优先级：CLI 覆盖 → 环境变量覆盖 → TOML → 默认值。未知键、非法类型和非有限超时会报错。

支持 `KENSHI_TEST_REPORTS_DIR` 和 `KENSHI_TEST_GAME_EXECUTABLE`。配置内路径支持环境变量和 `~`。
配置及环境变量的相对路径以配置文件所在目录为基准；CLI 路径以当前工作目录为基准。
用户自己的 `kenshi-test.toml` 已忽略，避免把机器路径同步到其他电脑。

## 静态资产检查

```powershell
kenshi-test check-assets .\local-assets\armor.mesh .\local-assets\armor.skeleton
kenshi-test check-assets --manifest .\local-assets\manifest.json
kenshi-test report --latest
```

将 `examples/asset-manifest.example.json` 复制到自己的资产目录并修改。示例中引用的文件不随仓库提供。
清单格式是本项目定义的 JSON，不是 Kenshi FCS / `.mod` 格式。所有引用必须使用 `/` 分隔的相对路径，
相对于清单目录且不得越界；程序只读取资产，不修改它们。

目前检查文件存在、非空、OGRE `0x1000` 流头、大小端、serializer 版本字符串、载荷存在，
以及显式声明的依赖存在且非空。读取二进制头是有界的，不加载整个模型。
对于 `.material`、纹理、`.mod` 等，仅支持清单中的存在性检查，没有内容解析器。
未知文件类型返回 `skipped`；全为未知类型不会报告成功。

**基础检查通过不代表模型有效或兼容 Kenshi。** 骨骼、顶点、蒙皮权重、动画、材质语义、FCS 引用、
OGRE 版本兼容性和游戏内效果仍为未验证。测试数据由 pytest 合成，不含游戏模型或存档。

## 架构

```text
CLI / TOML config
  ├─ TestRunner ─ armor suite ─ GameAdapter
  │                              ├─ MockAdapter (in-memory state + labeled SVG)
  │                              └─ KenshiAdapter (explicit errors; phase 2)
  ├─ AssetChecker (offline, read-only)
  └─ ReportGenerator (JSON + Markdown + relative artifacts)
```

```text
src/kenshi_test/     Python package, console entry point
  adapters/         deadline contract, mock, real adapter boundary
  assets.py         extensible offline checks
  suites.py         adapter-independent test steps
  runner.py         timeout, assertions, exception and cleanup handling
  reports.py        atomic report writes, latest report lookup
tests/              unit tests + installed CLI subprocess integration tests
scripts/smoke.py     three acceptance commands + expected failure exit codes
docs/               Windows deployment and phase-two integration contract
.github/workflows/  Windows/Linux, Python 3.11/3.12/3.13 offline CI
```

超时使用单调时钟、全流程共享预算。失败后的诊断截图预算为 1 秒，清理预算为 2 秒，独立于主预算。
这是适配器必须遵守的协作式超时协议；不宣称可强制杀死任意卡住的第三方 Python 方法。
真实后端须为子进程/IPC 配置剩余超时并实现可靠清理，详见 [接入约定](docs/real-adapter.md)。

## 跨电脑和持续集成

完整步骤见 [Windows 安装与 GitHub 部署](docs/windows.md)。只同步源码、说明、配置模板和测试。
不提交游戏本体、原版模型、Mod 实体、私人存档、机器配置或测试截图。
GitHub Actions 自动构建 wheel，再从 wheel 运行测试与验收命令；不安装游戏，不需要游戏资源或密钥。
本地通过与 GitHub 远端 Actions 成功是不同状态。只有推送后实际完成的 Actions 才能作为远端 CI 通过证据。

## 参考与证据边界

- [Universal Modder](https://github.com/rehan-remade/universal-modder) 作为后续 Windows 自动化集成参考。
  已查看其 [`um win` 源码](https://github.com/rehan-remade/universal-modder/blob/main/um/win.py)；
  第一阶段不安装、不调用、不复制该工具，不宣称已完成与 Kenshi 的联调。
- OGRE 基础流头规则参考官方 [OgreSerializer.cpp](https://github.com/OGRECave/ogre/blob/master/OgreMain/src/OgreSerializer.cpp)
  和 [Skeleton 文件格式声明](https://github.com/OGRECave/ogre/blob/master/OgreMain/include/OgreSkeletonFileFormat.h)。
  这些通用格式资料不能代替对 Kenshi 实际使用版本和资产的验证。
- 所有第一阶段报告均为 `game_verified: false`；`mock_simulation`、`static_only`、
  `unverified_game_attempt` 分别表示模拟、离线静态检查和未完成的真实游戏尝试。
