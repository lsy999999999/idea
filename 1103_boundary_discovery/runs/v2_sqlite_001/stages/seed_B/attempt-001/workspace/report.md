# Seed B 独立提案

## 结论

当前 scout 观测与 SQLite 已知 WAL 语义相符，不支持新机制或性能结论。相同写入量和 WAL 文件字节数下，scout 的 PASSIVE 返回值从无读者时 `(busy=0, log=143, checkpointed=143)` 变为旧读者存在时 `(0,143,2)`；事务结束后 TRUNCATE 得到 `(0,0,0)`。文件长度不是剩余 checkpoint 工作量的充分指标。

最强简单解释是读者快照的 end mark 限制可 checkpoint 的 WAL 前缀。读者年龄本身不是合适的变量：在相同活动时长下，快照建立时 WAL 的位置不同，可能允许不同进度。一个值得明确检验的表示边界是：`busy/log/checkpointed`、WAL 字节数与写入计数没有编码活动读者快照位置，也不含未来释放时间。

已有强基线：Zhu、Hu、Wang 的 2023 Walack 研究 WAL 存储中的异步、自适应 checkpoint；已读 OpenAlex 收录摘要称其观察读写请求并在线调整频率，报告降低尾延迟。该工作摘要不是全文审阅，也没有验证它在 SQLite 原生 PASSIVE 与不同读者 end mark 条件下的效果。故不能把自适应调度或读写负载感知称为新概念。

## 提案

- **B1（已知机制的可检验边界）**：固定写入与总 WAL 帧数时，PASSIVE 的可完成前缀由最老活动读者的快照 end mark 约束；只匹配读者持续时间会混淆快照位置。测量每次 PASSIVE 的 `(busy, log_frames, checkpointed_frames)`，并记录事务开始时点、结束时点和写入前缀；条件预测为较早 end mark 对应较少的 checkpointed frames，释放唯一最老读者后进度可跨过其原有边界。最强替代解释是 WAL 帧/页布局及 checkpoint 已完成前缀主导观察到的差异。具体关系属 SQLite 文档已述机制，不是新发现。
- **B2（当前遥测的决策充分性）**：聚合遥测相同的时点仍可能对应不同活动读者快照或不同释放顺序，因此只根据最近 `(busy, log, checkpointed)`、WAL 字节与写入量制定“何时再试”的策略可能不能预测短期增量进度。操作测量是在相同决策时点记录上述遥测，并从事务事件日志获得快照起点与释放时间作为解释变量；条件预测是即使这些公开聚合量匹配，分层后的下一次 PASSIVE 帧增量仍随快照位置/释放事件而变。最强替代解释是简单 WAL 大小阈值或按读写请求率调整的 Walack 类策略已经捕获可利用变化。该提案若仅证实信息缺失，也只是实现范围内的可观测性反例。

## 下一步

冻结一条短轨迹：总行数、事务边界和写入到达完全相同，仅改变读者在写入前缀后的快照开始/释放顺序；新数据库上随机化顺序并重复。比较固定周期、WAL 大小触发和只用公开读写请求率调整频率的策略，另记录仅作诊断的读者 end mark/生命周期。按完整性匹配 WAL checkpointed frames，再分别报告 checkpoint 调用耗时、提交尾延迟和读者完成延迟。先用开发轨迹调试，另留出不同释放/突发形状；在冻结预测前不解读 held-out 结果。当前阶段没有执行新实验。

## 来源与检索范围

- SQLite, “Write-Ahead Logging,” https://www.sqlite.org/wal.html 。项目已有已验证副本，提及读者 end mark、checkpoint 截止与自动阈值。
- SQLite, “Checkpoint a database,” https://www.sqlite.org/c3ref/wal_checkpoint_v2.html 。项目已有已验证副本，说明 PASSIVE 不等待且可能未完成，并给出 log/checkpointed 帧计数。
- Li Zhu, Yanpeng Hu, Chundong Wang, “Asynchronous and Adaptive Checkpoint for WAL-based Data Storage Systems,” 2023 IEEE ICPADS, pp. 1238–1245, https://doi.org/10.1109/icpads60453.2023.00179 。2026-11-04 检索 OpenAlex 记录与 Crossref DOI 元数据；只检查了索引摘要/元数据。摘要描述 Walack 按读写请求在线调整 checkpoint 频率。未取得全文，不据此作新颖性判断。
- OpenAlex 检索：https://api.openalex.org/works?search=adaptive%20checkpoint%20database%20WAL%20checkpoint&per-page=8&select=title,publication_year,doi,id 。命中上述 Walack 记录及其他异质领域 checkpoint 文献；搜索排序不视为系统综述。

状态：1 份单次、本机 SQLite 3.51.3 探测支持现象描述；proposal B1/B2 尚未测试。工作负载局部、无 held-out 轨迹、无策略比较、无全文综述。没有确认新表示的充分性或性能收益。
