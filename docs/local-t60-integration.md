# 本机 T-60 接入（更新至 2026-10-27）

> 此页为历史本机记录，部分命令依赖未共享的专项脚本。2026-11-03 的代码状态、能力边界、未验证项和双机分工以 [最新交接](handoffs/test-machine-latest.md) 为准；不要把本页中的旧源码提交当作实机运行包含的全部代码。

最新实机修复为 v0.8.3：缺失的 jog 别名已补齐，步行与慢跑实际激活；穿甲时选择装甲挂点表，脱甲恢复原挂点指针，已在新进程通过 82 → 30 → 82 往返。奔跑/格挡姿态和握点仍未通过视觉验收。实际截图在 `D:/JACK/KenshiArmorMod/验收/T60_v083_live/index.html`。以下 v0.8.2 段落保留历史观测。

`live wear --owner <owner> --enabled 0/1` 现使用实际库存/装备接口，不模拟按键。原自定义 F9 恢复键与游戏快速读档冲突，已改为 F11；F10 仍为恢复普通人并暂停穿甲。测试脚本 `scripts/verify_live_wear_roundtrip.py --mount-cache --output <report.json>` 核对装备、骨骼及挂点缓存往返。

`live mounts --owner <owner> --enabled 0` 只读挂点。`--enabled 1` 是仅限单个指定测试员的缓存诊断操作，不能代替穿脱控制器的自动恢复。正式控制器已经自动处理此逻辑。`sources` 返回动作第一帧指纹，可选命名助手存在时还返回全动作名称。不得据名称存在就声称动作姿态通过。

`scripts/verify_live_mount_cache.py` 是修复前的复现脚本；已自动刷新缓存的版本会拒绝“旧缓存复现”断言。当前版本的回归检查应使用上面的 roundtrip 脚本。

工具测试已达到 100 项通过。旧版原生启动器检查、单角色保护、会话/超时约束继续适用；所有本机截图、存档路径、桥接密钥和 Mod 实体均未推送。

源码提交：`55573b7e1f0c05b6aa538c514f24c2701b5c1727`。
已在独立 `.venv` 安装，原版 80 个测试和 installed CLI smoke 通过。

已新增可选 KenshiLua 后端：通过本机文件 RPC 在 GUI 主线程调用游戏 API，
不需要 computer-use、模拟鼠标键盘或网络服务。
原 armor 模拟套件的 I/E 不作为 Kenshi 的真实装备操作；它仍只用于模拟流程。

安装游戏端后，配置 `[game] bridge_dir` 为本机 `local-game/bridge` 目录。
重启并载入测试局后执行：

```powershell
# 直接启动，并自动确认已识别的 Mod 缺失/顺序警告。
.venv/Scripts/kenshi-test.exe start --skip-mod-warnings --timeout 60
# 如果已经停在本次启动器上：
.venv/Scripts/kenshi-test.exe start --attach-launcher --skip-mod-warnings --timeout 60
.venv/Scripts/kenshi-test.exe live status
# 使用 status 返回的 owner，不能猜测句柄。
.venv/Scripts/kenshi-test.exe live move --owner <owner> --gait walk --dx 20 --duration 10
.venv/Scripts/kenshi-test.exe live gait --owner <owner> --gait jog --duration 10
.venv/Scripts/kenshi-test.exe live halt --owner <owner>
.venv/Scripts/kenshi-test.exe live sheathe --owner <owner>
.venv/Scripts/kenshi-test.exe live release --owner <owner>
.venv/Scripts/kenshi-test.exe run --adapter kenshi --suite observe --timeout 10
```

控制只允许本机配置的测试角色；首次默认 `T-60 穿脱测试员`。
命令仅调用固定游戏 API，不执行任意 Lua 代码。每条控制指令绑定本次游戏会话，
过期请求不执行；单次移动限制 64 游戏坐标单位，速度档位有 1–30 秒租期，
到期恢复原档位、停止本次移动。若用户已手动改变速度，保留用户的新档位。
`release` 立即恢复本角色的租期设置。响应里的状态来自游戏接口回读，
移动请求成功只表示游戏接受了目标点，仍需后续 status 核对坐标变化。

适配器仅附加到已有游戏，不退出进程、不读取或保存存档。
`start` 使用 Win32 原生命令处理本游戏进程的启动器，不依赖截图、坐标或 computer-use。
识别条件包括 Kenshi 对话框、视频设置控件及其确认按钮；Mod 警告仅接受实际观测到的
“一个或多个mod已丢失或顺序错误。是否继续？”及对应英文版本。
确认警告后继续等待新的游戏端 RPC 回包，不能凭消息投递成功就报告启动成功。
2026-10-26 已实测中文警告自动确认后进入主菜单，获得 `simulated=false` 的新回包。
此时没有载入角色，状态 `waiting_for_test_save`，不能当作装备/动作验收通过。

已接入固定测试开局 `664-JACK_T60_WearLab.mod`，仅空主菜单允许创建；
人物编辑确认仅允许非中途整容、单个角色且名称与配置一致的测试编辑器。
真实截图调用游戏的 `screenshot` 命令，在 `_screens` 输出 JPG，非桌面截图或模拟图。
`camera` 使用游戏自身 reset/focus；私有模型的动态包围盒会干扰自动跟随，
因此记录器暂停实际姿势、重设镜头、截图，再恢复模拟。它是间隔姿势采样，不是连续录像。

```powershell
.venv/Scripts/kenshi-test.exe live new-test
.venv/Scripts/kenshi-test.exe live finish-editor
.venv/Scripts/kenshi-test.exe live pause
.venv/Scripts/kenshi-test.exe live camera --owner <owner> --zoom 55
.venv/Scripts/kenshi-test.exe live capture
.venv/Scripts/kenshi-test.exe live nearby --owner <owner>
# spar 会向指定 NPC 和测试员发出真实近战 AI 目标，测试员进入防御模式。
# 仅单个测试角色的独立局允许使用；30 秒后自动暂停并清理目标。
.venv/Scripts/kenshi-test.exe live spar --owner <owner> --target <nearby返回的NPC句柄>
.venv/Scripts/kenshi-test.exe live end-spar --owner <owner>
.venv/Scripts/python.exe scripts/record_live_motion.py --gait run --frames 10 --shuttle `
  --output reports/my-real-run
```

2026-10-26 已实际创建 v0.8.2 开局，自动确认人物编辑，观测 82 骨骼装甲，
采到权重 1 的 run lower/upper、walk lower/upper sword、blk front hi + stepback short。
空手步行/慢跑存在 idle 权重 1、下身权重 0 的滑行问题；慢跑档位仍未采到 jog lower 正常激活。
奔跑还有明显屈臂/前倾，格挡与背挂需要继续修正。不能标记为动作验收通过。

安装器默认要求退出游戏；显式 `--idle-upgrade` 可在零角色主菜单更新此桥接文件；
`--test-upgrade` 仅允许一个名称与配置匹配的可控测试员。每次更新备份并核对已有文件哈希。
实测热重载仅触及 `agent_test_bridge.lua`，不重载保存原人物快照的穿脱控制器。
本机采样代码与记录保留于本地，未推送远端。

未安装／未启动游戏时，RPC 超时返回 4，不能伪造在线状态。

```powershell
.venv/Scripts/kenshi-test.exe audit-motion --config kenshi-test.toml `
  --log D:/steam/steamapps/common/Kenshi/mods/KenshiLua/logs/KenshiLua.log `
  --fingerprints D:/JACK/KenshiArmorMod/previews/t60_v082/engine_after/engine_source_fingerprints.txt `
  --expected-version 0.8.2
```

此命令读取 MotionAudit 来源与播放日志，比较预期版本、轨道数及选定骨骼的第一帧指纹，
统计 lower 动作权重大于 0.5 的步行、慢跑、奔跑，以及格挡激活采样。
只采纳日志最后一次 KenshiLua 启动后的记录；保留输入副本和 SHA256，避免混用旧会话。
默认要求上述四类动作均采到；缺少采样返回 6，版本／指纹不符返回 1。

报告的 `game_verified` 始终为 false；`game_log_observation` 只代表实际日志观测，
不能证明姿势好看、蒙皮正确、背挂方向正确，也不代表当前仍有游戏进程在运行。
历史记录可以回归检查，不能当成本次实机验收。

本机路径和报告均留在 gitignored 配置／reports 目录，不上传游戏模型、存档或日志。
