# Windows 安装、测试与 GitHub 部署

## 无游戏开发机

需要 Python 3.11–3.13 和 Git。安装 Python 时选择可在终端中使用；不需要管理员运行本项目。
使用 PowerShell，在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:Path = (Join-Path (Get-Location) '.venv\Scripts') + ';' + $env:Path
kenshi-test doctor
kenshi-test run --adapter mock --suite armor
kenshi-test report --latest
python -m pytest --cov=kenshi_test --cov-report=term-missing --cov-fail-under=85
python -m ruff check .
python scripts/smoke.py
python -m build
```

无需执行 `Activate.ps1`，无需 `Set-ExecutionPolicy`，无需关闭任何 Windows 防护。
也可始终使用 `.\.venv\Scripts\kenshi-test.exe` 和 `.\.venv\Scripts\python.exe`。
安装依赖首次需要网络；安装完成后的 Mock、报告和静态检查不联网。

## 上传到 GitHub

在 GitHub 建立自己的空仓库，使用自己的仓库 URL。下列步骤适用于尚未初始化 Git 的目录：

```powershell
git init -b main
git add pyproject.toml MANIFEST.in README.md .gitignore .gitattributes src tests scripts docs examples kenshi-test.example.toml .github
git diff --cached --stat
git commit -m "Add offline Kenshi test CLI phase one"
git remote add origin https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST.git
git push -u origin main
```

以上使用当前项目仓库；若部署到自己的 fork，请替换 URL。提交前查看暂存内容；不要强制添加被忽略的资源。
`.gitignore` 只是防误提交措施，并不能代替检查。仓库没有包含游戏或第三方项目源码。

推送或提交 PR 后，Actions 的 **Offline tests** 工作流执行六组 Windows/Linux 和 Python 版本测试。
每组构建发行包、安装 wheel、运行 pytest 和 CLI smoke；JUnit 与覆盖率文件作为 CI 附件保存。
不运行真实游戏，也不要求 Steam、Blender、Universal Modder 或游戏路径。

## 另一台 Windows 电脑

```powershell
git clone https://github.com/jackaihyf-gif/Kenshi-AGENT-TEST.git
Set-Location Kenshi-AGENT-TEST
python -m venv .venv
# 仅使用 CLI，无需安装开发工具。
.\.venv\Scripts\python.exe -m pip install .
$env:Path = (Join-Path (Get-Location) '.venv\Scripts') + ';' + $env:Path
kenshi-test doctor
kenshi-test run --adapter mock --suite armor
kenshi-test report --latest
```

开发电脑的 `.venv` 不可直接复制；目标机从源码重新创建环境。更新时 `git pull` 后重新运行 `pip install .`。
若目标机离线，可从已验证的源码构建 wheel，将 `dist/kenshi_test_cli-*.whl` 传入目标机，
用目标机 Python 执行 `python -m pip install --no-index <wheel文件>`；运行时没有额外依赖。

有游戏的电脑也必须先通过同样的 Mock 验收。设置 `game.executable` 只用于检查所配置文件是否存在：

```powershell
Copy-Item kenshi-test.example.toml kenshi-test.toml
# 在自己的配置中填写实际路径，或设置 KENSHI_TEST_GAME_EXECUTABLE 环境变量。
kenshi-test doctor --adapter kenshi
kenshi-test run --adapter kenshi --suite armor
```

第一阶段路径缺失时返回 `5`；路径文件存在时返回 `6`（未实现）。不会启动文件、发送按键或截图。
必须完成 [第二阶段适配器约定](real-adapter.md) 后，才能进行真实 Kenshi 测试。

## 常见问题

- 找不到 `python`：确认已安装兼容版本，或改用 `py -3.12` 创建虚拟环境。
- 找不到 `kenshi-test`：使用 `.\.venv\Scripts\kenshi-test.exe`，并确认安装命令成功。
- pip 安装失败：检查网络和所用 Python 版本，保留错误日志；无需修改全局安全配置。
- `doctor` 显示游戏缺失：默认 Mock 模式允许，这是当前开发机的预期情况。
- 报告目录无法写入：使用 `--reports-dir` 指向自己有写入权限的目录。
- `report --latest` 没有报告：先运行 `run` 或 `check-assets`，并使用同一配置/报告目录。
- 静态检查报缺文件：清单引用相对清单所在目录；示例只提供路径格式，不附带资产。
- pytest 的系统临时目录拒绝访问：指定项目内的全新目录，例如
  `python -m pytest --basetemp=reports/pytest-local-01`。该目录只用于测试；pytest 会清理它，
  不要指向包含个人文件的目录。本项目无需修改系统临时目录权限。
