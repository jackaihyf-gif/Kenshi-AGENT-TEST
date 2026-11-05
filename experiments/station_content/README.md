# 本机弹药与制造站内容配方

仅共享本项目自编的转换、校验及安装脚本，供分析机审查；不是可独立运行的发行包。游戏数据、Blender插件、GLB、模型、DDS及二进制mod均不在仓库内，不从这些脚本推断其分发许可。

本机配置键：MOD_PROJECT_ROOT（模组工程）、GAME_ROOT（真实游戏）、AUDIT_READER（现有FCS读取器）；当前脚本仍有机器专用路径。分析机不要直接执行安装器。所有安装前提与原SHA断言保持，禁止删断言以在已有安装上重跑。

顺序为export_station.py导出、build_material.py转换贴图、compress_dds.py压缩、build_mips.py生成mip、export_install_mesh.py补开口背面、build_candidates.py校验并写候选、install_candidate.py原子顺序安装。需要本机Blender4.4.3、现有Ogre导出插件及Pillow。保留输出、禁止覆盖旧候选；回滚仅使用本轮备份和精确哈希。两类弹药stackable=100，单包重量和charges不变；只替换本模组工作台自有building的parts引用，新增自有part/material记录，原版共享记录不改。

详见docs/handoffs/station-ammo-20261103.md。静态字节与字段比较、真实资源加载、受控原生制作、实际模型显示、自然科研/施工/AI搬料分别记录。固定夹具注料与供电不能作为自然获取证明；未执行项写未验证。
