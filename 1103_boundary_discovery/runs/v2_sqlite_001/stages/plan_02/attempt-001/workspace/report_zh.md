# plan_02 计划记录

## 决策

选择 E04：在与 E03 相同的 240 行轨迹中，改变唯一活动 reader 获取 snapshot 的写入前缀位置。E03 的 12/12 配对在 snapshot 位置相同的情况下得到相同的 2/26 checkpointed frames；因此年龄效应已经被局部反例削弱，但 end-mark 位置效应仍未被检验。SQLite 文档已经说明 reader end mark 可限制 checkpoint，此计划检验该已知机制在当前本地轨迹中的可测操作化，不主张新颖性。

备选 E05 在 2,400 行较大突发上重复同一种位置干预，可查看该关系是否依赖写入规模；它同时改变了研究总体，并且在 E03 的直接缺口上不如 E04 清晰，所以本轮优先 E04。两个计划均未执行。

## 预注册分类

各计划使用 12 个预先列明的种子，种子内条件顺序由该种子初始化的伪随机数发生器打乱。每条件使用独立 fresh DB。控制条件固定 SQLite build（复用当前项目环境的 sqlite3）、page size 4096、WAL、synchronous=NORMAL、wal_autocheckpoint=0、240 次总插入、每次事务 10 行、相同数据形状及相同末端 log_frames/WAL bytes。仅 reader 开启时点随条件改变；reader 在 checkpoint 时保持活动。记录 snapshot 建立事件、前缀提交数、busy、log_frames、checkpointed_frames、WAL bytes 与调用耗时。测量控制不匹配的配对标无效，不替换种子；有效配对少于 10/12 则归为 uncertain。

主要量为每个种子 late-prefix 减 early-prefix 的 checkpointed_frames。position_order 类要求至少 10/12 有效种子差值严格大于零，且至少 10/12 的中间位置结果不低于 early。position_flat 类要求至少 10/12 的 early/late 差值为零。二者互斥；未达到任一规则、出现相反方向或控制/精度不足均为 uncertain。计时仅为次要描述量，不改变分类。若扫描所有位置的实测 checkpoint 进度非单调但有差异，单列在原始数据中并归 uncertain，不事后改阈值。

## 解释边界

观察是 SQLite 返回的帧数和受控事务轨迹；position_order 或 position_flat 是预定分类；关于调度表示是否有用属于解释。官方文档已记载 reader end-mark 机制，重复得到 position_order 仅是该局部条件下的已知机制再现。position_flat 也只限制此处写入形状、SQLite build 与测量接口，不能推翻一般文档机制。任何策略收益、普遍边界或世界新颖性都不由该实验检验。
