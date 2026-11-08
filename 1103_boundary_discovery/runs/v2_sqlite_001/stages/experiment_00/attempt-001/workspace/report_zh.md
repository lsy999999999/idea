# E02 实验报告

**状态：completed；结果分类：`uncertain_or_tradeoff`。** 按冻结计划，12 个执行顺序种子、development 与 heldout_H1 两种轨迹形状、三种策略共完成 72 个独立临时数据库运行。SQLite 为 3.51.3；每次运行均提交 240 行。所有 204 次 PASSIVE 调用均返回 busy=0。各运行末尾残余帧均为 0。原始逐次数据和执行代码见同目录 `raw_trials.json` 与 `run_e02.py`；分类及配对 bootstrap 结果见 `classification.json`。

主要结果（lifecycle 减基线，ms；95% 配对 bootstrap 区间）：

- Development 对 fixed-period：checkpoint 时间差均值 -0.0793，区间 [-0.1174, -0.0419]；终端 API 帧数 lifecycle 为 10/10，fixed 为 6/6。对 WAL-growth：-0.0776，区间 [-0.2224, 0.0338]；终端帧数为 10/10 对 16/16。两者残余均为 0。
- Heldout_H1 对 fixed-period：+0.0202，区间 [-0.0296, 0.0796]；终端帧数 4/4 对 6/6。对 WAL-growth：+0.0174，区间 [-0.0301, 0.0669]；终端帧数 4/4 对 24/24。两者残余均为 0。Lifecycle 的 writer p95 相对 WAL-growth 高 0.0090 ms，区间 [0.0040, 0.0139]；reader 最大完成延迟差 -0.1357 ms，区间 [-0.2729, -0.0462]。

分类依据：实际数字不满足 `lifecycle_gain`，因为 heldout_H1 的两项 checkpoint 成本区间均包含 0，lifecycle 终端 checkpointed/log 帧数也较低；不满足 `baseline_sufficient`，因为不能据此确认每种策略完成帧和延迟匹配。按冻结规则，数据不足/完成量或延迟不匹配归入 `uncertain_or_tradeoff`。此外冻结干预只规定一个 held-out shape，而两个明确类别均要求两个 held-out shape；没有增造第二个 shape 来改变既定设计。故本次不能判断 C1/C2。

偏离及限制：冻结计划未给 trace 的具体位置或基线阈值，本次在测量前按 `preregistration.md` 固定为每 6 次提交尝试、WAL 自上次尝试增长 32768 bytes 触发、以及 reader 全部释放时尝试。事件串行回放，reader 延迟包括事件间 checkpoint 用时，不等价于并发客户端服务延迟。PASSIVE 返回的 terminal log/checkpointed 是 SQLite API 的末次报告值，不能跨 WAL 重启解释为累计帧数；因此同时报告相同行数与残余帧。仅有一个 held-out shape，且一个本地 SQLite build/文件系统；结果不是生产收益或新颖性证据。

下一项最小验证应先修订未来实验计划的形状数量歧义并冻结第二个 held-out release/burst shape，再以独立新数据库和相同分析规则复验；本报告不提出假说状态更新。
