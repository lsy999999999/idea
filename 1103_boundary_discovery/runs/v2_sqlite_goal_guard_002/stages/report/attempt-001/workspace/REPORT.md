# V2 SQLite WAL 阶段报告

## 结论

本轮从 SQLite WAL checkpoint 进度为何不能由写入量、WAL 文件大小或 `busy` 单独解释出发，进一步问：在工作完成量和服务延迟受约束时，应用可见的 reader 生命周期信息，能否在不同 release/burst 轨迹上降低 PASSIVE checkpoint 总成本？当前答案仍未确定。E02、E03 均按预注册规则分类为 `uncertain_or_tradeoff`；没有新关系或策略获得支持，也没有世界新颖性结论。reader end-mark 对 checkpoint 的限制是 SQLite 文档已经说明的机制。

**审查状态：** reviewer 认定 E02、E03 的冻结分类有效，并独立重算核对 E03 的关键区间。reviewer 结果没有 `review_status` 字段，也没有标记 `needs_review` 的结论。分类有效只说明按规则归类正确，不表示两项实验已充分区分竞争解释。

## 问题与表示变化

最初的解释缺口是：固定写入量、相同 WAL 大小或相同聚合 checkpoint 状态，是否仍因 reader snapshot 的位置或释放时序不同而对应不同的可推进前缀；若是，生命周期信号能否带来计入全部调用成本、且不牺牲 reader/writer 延迟的策略收益。A1/B1 将状态表示从聚合遥测扩至最老活动 reader 的 snapshot end-mark 相对 WAL head 的位置。A2/B2 再将问题扩为跨多次 checkpoint 的 release/burst 时序和行动时点可见的 reader lifecycle。C1/C2 把这项表示争议改写成三个真实 SQLite 策略的成本、工作完成和延迟比较。C3 单独提出 reader 年龄是否在 snapshot 位置固定后仍有额外解释力。

实际执行测试的是 C1/C2 的策略争议，不是 A1/B1 的 end-mark 位置配对试验，也不是 C3 的年龄独立效应试验。因而现有策略结果不能验证或推翻 A1、B1、C3；A2/B2 所关心的信号价值也没有得到明确区分。检索边界包括 SQLite 官方 WAL、checkpoint API 与 PRAGMA 文档，以及 Walack 的摘要/元数据。SQLite 已知机制不构成新发现；Walack 全文未取得，不能判断其方法与生命周期信号的精确重合度，定向检索也不支持新颖性断言。

## 假说与实验覆盖

| ID | 核心主张或检验 | 状态与观测 | 来源 |
|---|---|---|---|
| A1 | 最老 reader snapshot 相对 WAL head 的位置限制当前 PASSIVE 进度；较早 snapshot 应少推进帧。 | 未测试。它是已知 end-mark 机制的最小实用表示问题，不是本轮的策略试验。 | ledger A1；SQLite WAL 文档：<https://www.sqlite.org/wal.html> |
| A2 | reader release 与 checkpoint 时点的相对关系可能决定后续推进机会；增加历史/预计窗口能否净改善成本未知。 | 未测试。E02/E03 测了当下生命周期策略，但结果不足以识别该解释。 | ledger A2；SQLite PASSIVE API：<https://www.sqlite.org/c3ref/wal_checkpoint_v2.html> |
| B1 | 固定写入量和 WAL head 时，最老 end-mark 而非 reader 年龄限制可推进前缀。 | 未测试；不得把官方文档所述机制当作本地实验验证。 | ledger B1；SQLite WAL 文档与 PASSIVE API |
| B2 | 聚合遥测/WAL 字节可能遗漏 snapshot 和 release 顺序，造成可观测性边界。 | 未测试为匹配观测历史的反例。E02/E03 的策略对比没有证明聚合表示不足。 | ledger B2；Walack 摘要/元数据边界见 reviewer `source_checks.json`；DOI: <https://doi.org/10.1109/icpads60453.2023.00179> |
| C1 | 在新轨迹上，reader lifecycle 策略可在相同工作和不劣延迟下同时胜过固定周期、WAL-growth 两基线。 | `inconclusive`。E02/E03 均未达到冻结的联合收益标准。 | E02、E03 原始试次和分类文件；ledger C1 |
| C2 | 完成量和服务结果匹配后，简单基线已足够，生命周期信息没有净成本收益。 | `inconclusive`。两项实验也都未达到冻结的基线充分标准。 | E02、E03 原始试次和分类文件；ledger C2 |
| C3 | snapshot 前缀、活动状态、写入和 WAL head 固定时，较长 reader 年龄仍降低当前 PASSIVE 帧数。 | 未测试；强代理假说没有证据。 | ledger C3；SQLite WAL 文档 |
| E02 | Development 与一个 heldout_H1 上比较 fixed-period、WAL-growth、reader_lifecycle；三策略各 12 个次序种子，共 72 次。 | 已完成。H1 lifecycle-minus-fixed 时间差均值 +0.0202 ms，95% CI [-0.0296,+0.0796]；minus-WAL-growth +0.0174 ms，CI [-0.0301,+0.0669]，均跨零。末次 `(log,checkpointed)` 为 fixed `(6,6)`、WAL-growth `(24,24)`、lifecycle `(4,4)`，各自 residual 为零；这些末次值不是跨 WAL 重启累计帧数。冻结分类 `uncertain_or_tradeoff`。 | `runs/v2_sqlite_001/stages/experiment_00/attempt-001/workspace/raw_trials.json`、`classification.json`；reviewer 复核 |
| E03 | 新 H2/H3 release/burst 形状，三策略、每形状 12 个 order seeds，共 72 次。 | 已完成；所有运行均提交 240 行、内容一致且终端 residual 为零。H2 lifecycle-minus-fixed 时间均值 -0.0798 ms，CI [-0.1170,-0.0504]；minus-WAL-growth -0.0213 ms，CI [-0.0700,+0.0167]。H3 相应 -0.0467 ms，CI [-0.1755,+0.0851]；+0.1552 ms，CI [+0.0502,+0.2688]。多项延迟差区间上界大于零。分类 `uncertain_or_tradeoff`。 | `runs/v2_sqlite_goal_guard_002/stages/experiment_01/attempt-001/workspace/raw_trials.json`、`classification.json`；`stages/review/attempt-001/workspace/recomputation.json`、reviewer result |

## 证据解释与限制

**已执行的结构行为：** 使用 SQLite 3.51.3、临时真实 WAL 数据库和关闭 autocheckpoint 的策略回放；E02 有 72 次运行及 204 次 PASSIVE 调用，E03 有 72 次运行。E03 在 H2/H3 内控制提交数据和最终残余帧，并随机化策略运行顺序。E03 的 `events.jsonl` 记录两次成功的完整脚本执行：操作者修正 bootstrap seeds 至冻结值 3104 后重新运行。最终 `raw_trials.json` 是第二次的 72 次测量；这不是仅执行过 72 次数据库运行，也不是两次独立确认。该重跑及归因来自 peer provenance 记录。

**暂定科学价值：** E03 的固定回放中，H2 lifecycle 相对 fixed-period 的 checkpoint 时间区间上界为负；但这不伴随对两种基线都成立的成本优势，H3 对 fixed-period 的区间跨零，且 lifecycle 对 WAL-growth 在 H2 跨零、H3 更慢。多项延迟差上界大于零，因此预注册的 lifecycle 联合收益和 baseline-sufficient 条件都失败。E02 只有一个 held-out shape，成本差区间跨零；其设计本身不足以达到要求两个 held-out shape 的明确分类。两轮结果都保持 C1/C2 为 `inconclusive`。

**适用边界：** E03 的 12 个 seeds 只随机化策略执行顺序，没有产生 12 个独立 workload realization；bootstrap 主要反映配对测量变化，不代表轨迹总体不确定性。所有回放串行推进，commit 计时和 reader completion delay 不能代表并发服务端 QoS。时间量级为亚毫秒。结果局限于这些合成轨迹、本地环境和 SQLite build。

**新颖性与方法比较：** 没有新的支持关系或已支持的策略边界。reader end-mark 行为是已知效果。本轮未对照 V1 或单 agent，也没有同预算方法比较，不能声称组织方式提升发现性能。Walack 全文和更完整的邻近工作尚未比较，因此世界新颖性未判定。

## 最强后续问题

在独立生成、而非只改变策略执行顺序的 release/burst workload 上，当前 reader lifecycle 输入能否在并发读写服务下，相对 fixed-period 与 WAL-growth 降低包含所有 PASSIVE 探测的总成本，同时完成相同数据库工作并保持 reader/writer 延迟不劣？下一项验证应以 workload realization 为独立重复单位，在执行前固定新轨迹、策略可见信息、完成量检查、延迟指标和互斥判定规则，并保存行动前可见遥测及全部调用成本。E02/E03 的轨迹应标记为已见，不再称为新证据。
