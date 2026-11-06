# 独立复核

复核了冻结计划 E02、E03、E04、三个实验的 runtime completion 记录、原始测量和分类文件。阶段记录均为 success，实验 observation 均为 completed。未改动先前产物。独立重算保存在 `recompute_review.py` 和 `recomputation.json`。

| 实验 | 分类复核 | 结论 |
|---|---|---|
| E02 | `uncertain_or_tradeoff`，有效 | 从 heldout_H1 的 12 个配对种子独立重算，lifecycle−fixed checkpoint 时间均值为 +0.020153 ms，95% bootstrap 区间 [-0.029562, 0.079587]；lifecycle−WAL-growth 为 +0.017358 ms，区间 [-0.030080, 0.066861]。两区间均含零；终端 API tuple 分别为 lifecycle (0,4,4)、fixed (0,6,6)、WAL-growth (0,24,24)。冻结计划的明确分类需要两个 held-out shape，但仅规定并执行一个；按计划数据不足条件应为 uncertain。主要限制：末次 API 帧数不能代表跨 WAL reset 的累计工作，且串行回放的 reader 延迟不是并发服务延迟。 |
| E03 | `no_age_penalty`，有效 | 从原始测量重算 12/12 配对有效，Δ=长龄−短龄 checkpointed_frames 均为 0，达到冻结的至少 10 个非负配对规则。它检验的是固定 reader snapshot 下的等待年龄，不是 snapshot 位置；因此映射到 B1 的支持仅是“不见年龄额外惩罚”，不能作为 B1 的 end-mark 位置主张之独立证据。 |
| E04 | `position_order`，有效 | 从原始测量重算 12/12 种子有效，early/mid/late 每次均为 2/14/25；late>early 与 mid>=early 均为 12/12，符合冻结规则。独立 fresh DB 和随机条件顺序有助于排除运行顺序偏差，但 12 个种子只改变执行顺序，属于同一固定轨迹的重复，不是 12 个独立 workload 抽样。SQLite 官方文档已说明 end mark 固定且能限制 checkpoint；结果是已知机制的本地操作化复现，不是新关系证据。 |

干预与测量检查：E03/E04 在同一机器、SQLite 3.51.3、相同写入形状下使用 fresh DB，测量真实 `PRAGMA wal_checkpoint(PASSIVE)` tuple 与 WAL 长度。E03 只改变 reader snapshot 后等待时长；E04 改变建立 snapshot 的提交前缀，记录可见行数作为前缀核对。E02 比较的是不同触发策略；触发时点/次数本身构成策略差异，时间和完成量都应一起看。已保存的 SQLite 页面明确说明其观测机制；E02 所引 2023 checkpoint 论文只做了 Crossref 元数据核对，未取得摘要或全文，近邻策略关系仍待查。

综合：算术分类均符合各自冻结规则；这只验证预定分类，不验证机制的普遍性。E02 的策略优势未成立；E03 限定年龄不等同于 snapshot 位置；E04 在单一 workload 上复现已知 end-mark 约束。三个结果都没有支持世界新颖性。
