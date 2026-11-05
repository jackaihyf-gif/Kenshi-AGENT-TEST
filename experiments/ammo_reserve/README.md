# 弹药包增量和激光小削

用户希望原版弩箭的多发包装方式也用于模组弹药。原版四类箭包charges为10/20/30/40，本模组两弹药ITEM的charges均1，枪CROSSBOW的num shots另为30/7；两字段不可混称。

用户随后明确要求一起实装：将Energy200核融合电池和Energy210的charges由1增到2，并将激光枪五个pierce damage字段统一乘0.85。低/高端两组范围75–105→63.75–89.25、110–150→93.5–127.5，共用基础字段30→25.5；高斯不改。保持两枪装填设置30/7、射速、声音、重量、格子、stack100、材料和制造速度。不把“物品charges2 × 枪num shots”直接宣称为实测射击次数；引擎消耗关系、已存在物品和旧档UI仍待用户验收。

构建（本机输入，不安装、不启动/接管游戏、不读写存档）：

```powershell
python experiments/ammo_reserve/build_candidate_local.py --game-root <game.root> --reader <local-reader.py> --output <new-private-output>
```

只提取已有作者FCS读写器定义，验证输入SHA、字节往返/回读和完整120+4加载序；最终合并必须仅七字段不同。产物留本机，仓库仅发布作者代码与摘要。旧包物品可能已有保存的剩余用量，不能承诺重启自动补满；旧枪实际伤害显示是否按新值重算也需验收，不修改玩家存档。
