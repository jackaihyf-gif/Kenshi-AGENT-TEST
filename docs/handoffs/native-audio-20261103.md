# 原版脚步与本地枪械声音：原生配置接线

用户最新要求保留原版脚步，不新增动力甲落脚或伺服层；枪声参考本地枪械mod。先前自有WAV/v112 bank仅离线研究，未向游戏安装，后续不自动启用。

## 原版机制与本地证据

- 原版使用Wwise；RE_Kenshi作者的[声音库说明](https://github.com/BFrizzleFoShizzle/RE_Kenshi/wiki/Using-RE_Kenshi-to-mod-sound-banks)提供自定义bank路线。本轮采用既有原生枚举，不需要新bank或播放脚本。
- 本机fcs.def的ANIMATION.events按动画百分比触发，原版左右脚事件均为Footsteps。ZoneManager原生导出`getGroundSound(GroundType,bool barefoot)`表明地面类型和赤脚状态参与选择，本轮原生日志也出现Surface_Material BFoot_Wood。不能据此说仅由鞋子的布/金属材质决定，日志本身不是逐人物归因证明。
- Armor_Worn是另一装甲材质分支，字符串表为Cloth/Leather/Chain/Plate；本机精确RE EXE静态代码0x5d1e20函数遍历装备，在slot==5分支取材质最大值写入角色+0x68c。它不是已证明的鞋材质开关。本轮没有调用这些地址，也没有改共享动画、种族barefoot、鞋或护甲材质/属性。
- 本地2333.mod的多款步枪/左轮为shoot sound=1，M36激光为0；其RE_Kenshi.json只声明插件，未声明SoundBanks，模组目录也未发现WAV/BNK。此结论限这些已检查文件，不推断所有枪械mod实现。
- 原生GunSounds枚举：0 CROSSBOW、1 HARPOON_GUN、2 CROSSBOW_TURRET、3 HARPOON_TURRET。两把本项目枪此前均为0。

## 唯一生产数据变更

高斯`110-JACK_EnergyWeapons.mod`的整数shoot sound从0变1；激光`100-JACK_EnergyWeapons.mod`保持0，与本地M36一致。不是专用激光/高斯科幻音色的完成证明。

源Energy模组SHA256为`7fde01d8e063ff1d99d338bd0824a23a22448da77f43b18b80a6a81ea78bc085`，候选/现装为`1307594e9132d2919caef549c7d739f174c15c3531131e9118ceef48c17b1d74`。二进制只在偏移8500改变一个字节；重新解析所有记录、字段和引用，除该整数外完全相同。伤害、弹匣、弹药和动作数据没有变化。见[可审查的精确数据配方](evidence/native-gun-sound-patch-20261103.json)。未上传.mod二进制或原版媒体。

测试桥源码仍为`8a3d993750f13604a66d23550fc7594ee290b64f` / PR4；声音数据变更属于上述独立内容哈希，不能把它说成已包含在8a3d993源码内。没有新C/DLL或音频hook。

## 首次失败、修正与实际执行

首次新建高斯独立局时，驱动仅等待editor=true就调用finish_editor，预览人物尚未建立，接口拒绝`No editor preview character`。3个RPC中1错误，0发；立即退出、停桥、恢复全部配置，并回滚声音数据。保留原失败，不算游戏崩溃或声音播放失败。

修正驱动等待editor=true、editor_count=1、editor_name为配置测试员；没有放宽接口门禁。另建全新证据目录和游戏会话：原生启动→既有new_test gauss→预览完整就绪→finish_editor→82骨稳定→单人禁自动保存→已有100000HP独立靶子→原生瞄准射击→结束spar/remove/halt→退出停桥。没有强制射击、写余弹或写存档。

实际观测7发容量，余弹序列含0→7→6→4，共观测3次原生减弹；93个RPC无错误。日志出现Weapons Bow、Reload、Attack及原版Footsteps/Surface_Material，**日志未证明独有Harpoon音色，也不能按首次去重日志推算每发音频次数**。本轮未人工试听或录制音频；只能确认原生数据配置与实射工作，最终音色、音量和区别仍未验证。

首轮29个、复测81个连续内存点；复测工作集峰值4562.78MiB、私有提交8080.21MiB、最低可用1.8986GiB，仅记录，不以2GiB中断，不据短测判泄漏或FPS。资源16/32/128不变，未增加常驻播放负担。

两轮均确认游戏退出、测试桥停用、18项T60生产哈希及COLD2不变、图形/自动保存/RE配置恢复原字节；临时LogAudio已恢复false。第二轮保留通过实射的数据枚举变更。首次错误和第二轮成功分开记录于[小型脱敏证据](evidence/native-gun-audio-20261103.json)及其中两份连续CSV；原始报告分别位于OBSERVER_WORKTREE/reports/native-gun-audio-20261103和reports/native-gun-audio2-20261103，不上传。

## 本机使用与下一步

现有试玩槽未改，下次正常启动会读取现装枪械数据。本机`release/Energy_native_sound_20261103`为数据增量，依赖完整已安装能量武器资源，不是独立模组；旧103文件整合候选保留原样，仍含旧声音字段。原始Energy.mod备份在MOD_RESEARCH_ROOT/research/audio_native_20261103/native_gun_sound。

原版脚步保持，不继续研发额外落脚声。用户可试听原生枪声；如需专用科幻音色，再独立处理合法声音库和隔离路由，不能将离线bank解析成功当游戏播放成功。分析机可检查本轮一字节数据配方及编辑器就绪条件；生产资源回收、跨区/倒地/自然AI制作仍按前交接推进，未自动合并main。
