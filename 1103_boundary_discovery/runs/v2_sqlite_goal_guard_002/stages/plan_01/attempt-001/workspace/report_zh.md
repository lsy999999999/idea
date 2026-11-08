# 计划阶段报告

## 账本证据与决策

当前 ledger 只有 E02 已执行：72 个真实 SQLite WAL 回放、两个 shape 中一个 held-out shape；heldout_H1 的 lifecycle 相对 fixed-period 与 WAL-growth 的 checkpoint 时间配对区间分别为 [-0.0296, 0.0796] ms 和 [-0.0301, 0.0669] ms，均包含零。三种策略末次 residual frames 均为零，但 lifecycle 末次 API 帧数低于基线。按冻结规则 E02 为 `uncertain_or_tradeoff`；一个 held-out shape 也不足以分类。不能据此声称策略有效或无效。

本阶段提出两个可执行的 anchor 目标测试。选择 E03：在两个全新 held-out release/burst 形状上复测三策略，使用新 order seeds、相同真实 SQLite 工作负载、同一完成量约束，并把每次 PASSIVE 调用都计入成本。E03 对结果的决策含义预先固定：若两形状均显示 lifecycle 在完成和延迟不劣时降低 checkpoint 时间，继续研究该信号的适用条件；若简单基线在两形状已匹配完成/延迟且成本不高，则停止把 lifecycle 当作这类轨迹的增益来源；其余结果保留为权衡或不确定。

## 解释边界

A1/B1 所述 end-mark 约束是 SQLite 文档已有机制；初始 scout 的单次对照与其方向一致，但不是新发现。A2/B2 及 C1/C2 仍是未解决的调度问题。E02 只使 C1/C2 inconclusive。当前计划不主张世界新颖性，也不将新 trace 的结果预先写成对任一策略的支持。

## 下一步

实验角色应先冻结 E03 计划，再用项目 `.venv/bin/python` 执行。保持 E02 两个已有形状不作确认性重复；E03 的两个 held-out 形状及 order seeds 必须在执行前写入 preregistration。按形状配对重采样，并严格执行完成量、reader/writer 延迟和成本分类规则。
