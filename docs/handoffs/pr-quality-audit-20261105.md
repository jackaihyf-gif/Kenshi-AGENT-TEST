# 远端PR质量审计与修复（2026-11-05）

用户指出最近多个PR持续出错。核对远端后确认PR5/6/9/10/11/12的最新检查均在Lint阶段失败，后续打包、完整pytest与CLI验收被跳过；PR1历史快照也失败。没有发现这些PR的新增审查评论。PR7 4c6bb22a25f724fdb31dae9622fef3c0f3dcbc86和PR8 c79192003acb622bc5b4c06ae56b9a5ffcc28462本已通过CI，但没有同步到本机后续分支，这是本机交付遗漏，不能用子集通过或文档注明替代修复。

本轮在原有独立修复/仪器分支上追加提交，不合并main、不覆盖分析机原分支。回移PR7/8的格式和覆盖率测试；实际Python运行模块bridge/cli AST相同，安装器按展开不变digest表达式/导入归一化后AST相同，PR8两文件AST相同。未改Lua生产载荷或原生DLL。

源码分支还保留两项严格XFAIL：腰甲误读上衣、session查询先耗时导致请求过期。已从既有实测PR2 7712d57d755a5f5cc3377e2781e4bad35d8c5376移植正确的腰槽14识别、发请求时算expires、session一致性和保留字段校验及回归，移除对应XFAIL。可选Lua武器Mock改用同一环境变量和作者合成夹具，避免测试依赖本机绝对DLL路径。不把这些Python接口修复称为生产外观free完成。

新增Windows CI：源码家族的visibility生命周期真实C Mock（-UNDEBUG、sentinel、-DNDEBUG编译必须拒绝）；PR11新增保存reader/reset真实汇编Mock。现有仪器家族的私有ownership Mock CI保留。只上传合成JSON摘要，无DLL、游戏、存档或原始报告。当前游戏中装好的C/.mod/资产完全未换，也没有因这次质量修复启动游戏；既有实际被测SHA及安装回执保留。

本机独立wheel环境与CI版本一致（Python3.12.10、Ruff0.17.3、pytest9.2.0、coverage7.17.2）。完整构建源码/轮子、安装轮子后pytest和CLI smoke均通过：源码家族139项中130通过/9可选Lua跳过/0失败/0XFAIL；仪器家族127项中117通过/10可选Lua跳过/0失败/0XFAIL；均92.42%覆盖，85%门槛不变。本机另显式提供已存在LuaJIT DLL执行实际合成Lua回归，不能拿CI跳过项算执行通过。原生visibility及save/reset Mock也在本机完整执行，无游戏。

PR1在独立干净工作树处理，src/scripts/tests Python内容与完整验证的源码家族逐文件相同；原测试目录75份历史未提交脚本未改。历史pytest-of-*临时工程里有旧安装器副本，保留原始文件，仅将这类根目录临时产物加入.gitignore，不忽略任何tracked源码或正式fixtures。第一次本地完整测试因过深的测试临时根超过Windows路径长度而失败；改用本工作区内较短、独立的新临时根后，同一个Unicode/空格路径测试和全套测试通过，未删除或弱化用例。

AGENTS.md新增完整提交门禁：全仓Ruff、源码/轮子与安装后完整pytest及85%覆盖率、CLI smoke、原生改动必须有CI断言Mock；核准确HEAD的远端CI后才报告交付，失败先修，不再以仅改动文件或26项子集代替。未提交脚本及原始现场必须保留，必要时隔离工作树检查。

本文件写入时远端新HEAD的CI尚待核对；最终每个分支SHA与Actions结论记录在结果分支同名交接及证据JSON，以准确HEAD为准，不沿用旧绿灯。用户仍让第4项资源/读档稳定性为主，其余功能留晚间人工验收；本轮质量审计完成后回到第4项。
