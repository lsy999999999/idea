# V2 首轮研究报告：SQLite WAL checkpoint 可观测性

## 结论

本轮从一个实践缺口出发：WAL 字节数、写入量及 `busy=0` 并不能唯一描述 checkpoint 可推进程度；在 reader 释放和写入突发交错时，允许观察的信息能否指导有净收益的 PASSIVE 调度仍未知。报告比较了聚合遥测、reader 生命周期/年龄与 snapshot 相对 WAL 写入前缀的位置表示。

执行结果显示，在本地 SQLite 3.51.3 的固定 240 行轨迹中，snapshot 前缀较晚时 PASSIVE 帧进度较高；单独延长 reader 墙钟年龄没有改变帧数。生命周期策略在唯一 held-out 轨迹上的净成本优势未成立。前缀效应符合 SQLite 已公开的 end-mark 机制。因此，本轮没有支持的新关系、新机制或新颖性发现，也没有证据说明 V2 优于 V1 或单 agent；没有运行受控方法比较。

## 复核状态

**Reviewer 的 `review_status` 字段为 `null`，不是 `needs_review`。** 三个实验的冻结分类均经独立重算为有效。尽管如此，E03 对 B1 的账本映射只能说明固定 snapshot 下未见年龄惩罚，不能作为 B1 的 snapshot-position 预测已验证的证据；下表按此限制表述。没有任何结论依赖未复核结果。

## 假说与实验覆盖

| ID | 类型 | 问题 / 操作性分歧 | 结果与证据 | 状态及解释边界 |
|---|---|---|---|---|
| A1 | 假说 | 即时进度是否由 WAL head 与最老 reader snapshot end mark 的相对位置刻画？ | 未直接指定该假说的实验；E04 提供相关的本地前缀位置观察。来源：`runs/v2_sqlite_001/ledger.json`；E04 原始数据 `runs/v2_sqlite_001/stages/experiment_02/attempt-001/workspace/raw_trials.json`。 | 账本仍为 `untested`。E04 与之相容，但单一固定轨迹不足以验证“最小有用状态”或外推。 |
| A2 | 假说 | reader 释放时序或可用生命周期信号能否预测 checkpoint 机会并改善固定成本策略？ | E02 比较 lifecycle、固定周期、WAL-growth 策略。来源：`runs/v2_sqlite_001/stages/experiment_00/attempt-001/workspace/classification.json`。 | `untested`。E02 未证明净收益；一个 held-out shape 不足以检验完整预测。 |
| B1 | 假说 | 固定写入量和 WAL head 时，checkpoint 前缀位置比 reader 年龄更能解释可推进帧数？ | E03 的 12/12 配对年龄差均为 0；E04 的 early/mid/late 为 2/14/25。来源：E03/E04 `classification.json` 及 reviewer `recomputation.json`。 | 账本标 `supported` 的依据是 E03 的 `no_age_penalty` 映射；reviewer 明确指出 E03 未改变 snapshot 前缀，故这不是 B1 位置预测的直接支持。E04 提供相邻但局部的前缀证据。 |
| B2 | 假说 | 聚合 checkpoint 遥测与 WAL bytes 是否不足以决定下一次 PASSIVE 时机？ | E02 检验一种 lifecycle 策略；未测试匹配聚合状态但不同释放顺序的不可区分轨迹。来源：E02 `raw_trials.json`、`classification.json`。 | `untested`。结果不证明聚合信息不足或新增信号有价值。 |
| C1 | 假说 | lifecycle 信号能否在工作完成与服务结果不劣时降低 checkpoint 成本？ | E02 heldout_H1：lifecycle 减 fixed-period 时间差 95% CI `[-0.0296, 0.0796] ms`；减 WAL-growth 为 `[-0.0301, 0.0669] ms`，两者均含零。末次 API `(log,checkpointed)` 为 lifecycle `(4,4)`、两基线 `(6,6)` 与 `(24,24)`；均无残余帧。来源：E02 `classification.json`、reviewer `recomputation.json`。 | `inconclusive`，冻结分类 `uncertain_or_tradeoff`。一个 held-out shape、末次 API 帧数而非跨 WAL reset 累计量、串行延迟限制结论。不得称 lifecycle 有收益。 |
| C2 | 假说 | 固定周期或 WAL 大小基线是否已足够，额外 lifecycle 信息无净成本收益？ | 同一 E02 数字；heldout_H1 成本差区间含零，lifecycle 的末次 API checkpointed 数低于基线。来源同 C1。 | `inconclusive`。E02 不支持 lifecycle 优势，也未达到冻结的 `baseline_sufficient` 明确类；不能据此确认基线一般充分。 |
| C3 | 假说 | snapshot/head 固定时，reader 墙钟年龄本身是否降低可 checkpoint 帧数？ | E03 12/12 配对控制有效，短龄和长龄均为 `2/26`，长龄减短龄 Δ 全为 0；年龄等待实测约 1.12–1.33 ms 与 100.73–105.04 ms。来源：E03 `raw_trials.json`、`classification.json`。 | 冻结分类 `no_age_penalty`，账本 `contradicted`。只限该 build、burst 和单次 PASSIVE；不检验 snapshot 位置。 |
| D1 | 假说 | 更晚 snapshot 前缀在固定总写入与 WAL head 下是否允许更大 PASSIVE 进度？ | E04 12/12 种子均 early/mid/late=`2/14/25` 帧，log=`26`，checkpoint 前 WAL=`107152` bytes，reader 活动且 `busy=0`。来源：E04 `raw_trials.json`、`classification.json`。 | 冻结分类 `position_order`，账本 `supported`。仅支持所测 SQLite 3.51.3 和固定轨迹；是已知 end-mark 机制的实测重现，不是新发现。 |
| D2 | 假说 | 在该固定轨迹中 snapshot 前缀是否不会产生稳定帧数差？ | 与 D1 同一 E04 观测；规则 `position_flat` 计数为 0/12。来源同 D1。 | 冻结分类 `position_order`，账本 `contradicted`。仅否定该局部竞争预测，不否定其他配置或其他状态量。 |
| E02 | 实验 | 比较 lifecycle 与固定周期、WAL-growth 策略。 | 72 次运行、204 次 PASSIVE；heldout_H1 两个成本 CI 均含零，末次 API 帧数分别 4、6、24。来源：`runs/v2_sqlite_001/stages/experiment_00/attempt-001/workspace/raw_trials.json`、reviewer `recomputation.json`。 | `completed`；分类有效但为 `uncertain_or_tradeoff`。冻结的明确类需要两个 held-out shape，实际只运行一个；不能判断策略胜负。 |
| E03 | 实验 | 在固定 snapshot 下比较短、长 reader 年龄。 | 24 次运行、12/12 有效配对，checkpointed_frames 均为 2，Δ=0。来源：`runs/v2_sqlite_001/stages/experiment_01/attempt-001/workspace/raw_trials.json`、reviewer `recomputation.json`。 | `completed`；分类有效为 `no_age_penalty`。只区分年龄效应，不区分 snapshot 位置。 |
| E04 | 实验 | 固定 240 行轨迹，比较第 0、12、23 批后建立的 reader snapshot。 | 36 次运行、12/12 有效种子，early/mid/late=`2/14/25` 帧；两项 `position_order` 规则均 12/12。来源：`runs/v2_sqlite_001/stages/experiment_02/attempt-001/workspace/raw_trials.json`、reviewer `recomputation.json`。 | `completed`；分类有效。种子只随机化条件执行顺序，未抽取不同 workload；SQL/schema 是执行时披露的工程解析。局部重现已知 end-mark 行为。 |

## 表示变化、失败预测与已知依据

最初问题关注聚合观测（WAL bytes、写入数、busy/log/checkpointed）是否足以调度。假说随后分成三种表示：reader 生命周期与释放时点（A2、B2、C1/C2），固定 snapshot 下的墙钟年龄（B1/C3 对照），以及 snapshot 相对提交前缀的位置与 WAL head（A1、D1/D2）。真正被直接操纵并测得区分的是年龄与前缀位置：E03 年龄差为零；E04 前缀位置出现 2/14/25 的顺序差。

失败或未检验的预测包括：E02 未显示 lifecycle 的明确成本优势，亦未满足可确认基线充分的条件；C3 的额外年龄惩罚预测在该轨迹失败；A2/B2 的信息充分性与释放时序预测未被直接检验；A1 的“最小有用状态”及跨配置适用性未验证。D2 的局部平坦预测失败。以上属于本轮有限轨迹结果，不构成对一般 SQLite 行为的断言。

SQLite 官方 WAL 文档说明 reader end mark 在事务期间固定且会限制 checkpoint；checkpoint API 文档说明 PASSIVE 尽可能推进而不等待，遇并发 reader/writer 可留下未完成工作。这为 E04 提供已知解释。复核还发现相邻工作 Walack（DOI: `10.1109/ICpADS60453.2023.00179`）涉及 WAL 自适应 checkpoint，但未取得摘要或全文；目前不是全面新颖性检索。资料：`https://www.sqlite.org/wal.html`、`https://www.sqlite.org/c3ref/wal_checkpoint_v2.html`、`https://doi.org/10.1109/icpads60453.2023.00179`。

## 最强后续问题

下一轮优先回答：**在至少两个预先冻结、release/burst 排列不同的新 workload 上，策略可见的 reader lifecycle 信号能否在匹配累计 checkpoint 完成工作及 reader/writer 延迟后，降低总 PASSIVE 调用成本？** 运行前修订 E02 的 held-out 数量矛盾，定义可跨 WAL reset 比较的累计完成量，保持未来 release 不可见，并冻结成本、延迟与未完成工作规则。若研究重点改为基础机制外推，则另设独立的新 workload/page layout 位置效应复验；不能把它并入策略收益证据。本轮无剩余实验槽，因此两项都未执行。

本轮所有 SQLite 实测由 Python `sqlite3` 执行；请求模型记录为 GPT-6 Luna，实验未调用模型推理，也未核验后端权重。
