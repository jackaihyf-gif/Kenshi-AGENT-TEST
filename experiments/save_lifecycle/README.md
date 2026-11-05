# 保存借用与世界重置保护候选

用户当前只推进资源/长期稳定性；其他功能留晚间人工验收。本候选没有free路径、没有返还/清零预算，16/32/128保持。

save_reader.c由此前未接入生产的reader/epoch/lease候选引入，保持原shadow保存ABI；新增每代借用计数、SEH finally释放、clear/forget退役不覆盖在途读者、128占用上限、异常锁存和退休token。原生生命周期回收尚未授权：lease只覆盖模组保存读者，不覆盖引擎/渲染，也不允许调用回收。修复了quarantine时generation查询仍返回有效代号的旧候选缺口：现在-3且输出0。测试采用已有断言审计的隔离夹具，各溢出场景只在所有线程join后的Mock里重新初始化，生产无清零API；旧非隔离测试在显式断言下会因上个场景残留tombstone失败，不能关断言绕过。

reset_guard只针对准确EXE SHA504b362c…：原始转储的pdata有界展开和逐层call位置核对显示FactionManager::clearAndDestroy→Platoon析构→ActivePlatoon析构→GameWorld::destroy→树容器操作；0x7990d5虚调用返回NULL，0x7990db加0x3d0、0x28b83a读+8导致访问0x3d8。guard经AddHook插入0x7990db，NULL且当前线程正在FactionManager::clearAndDestroy时，只跳过这一项对不存在容器的erase，到0x7990ea继续原清理；非NULL、其他线程、非reset均回原trampoline。没有取消角色析构/重置，也不改对象字段。vtable方法具体语义及更上游导致NULL原因尚未确认，不能称所有读档崩溃根因已解决。

启动同时核EXE哈希、两个hook字节、TEB thread-id与系统API一致，pin模块；部分hook失败锁存不重试。汇编不改RSP，除条件标志/R11外不改寄存器；R11在被替换的原生调用中是volatile。无逐帧轮询。clear hook finally恢复线程/嵌套深度，不等待引擎reader或做额外删除。

本机构建：配置KENSHI_TEST_ZIG为Zig0.13.0 cc、KENSHI_LIFECYCLE_BUILD_OUT为独立可写目录，运行python -X utf8 build_local.py。显式-UNDEBUG且测试拒NDEBUG；native Mock覆盖借用/清除/异常/16并发/租约/隔离溢出及generation quarantine、真实汇编NULL分支/非NULL/不同线程/非reset与clear异常退栈。Mock不能代替实机。具体产物哈希见offline-result.json；DLL只留本机，不入Git。

实机部署和多轮保存/读回结果尚未填写，先提交候选以绑定被测SHA。生产资源回收未完成，不把reader数0或护栏命中当free证明。
