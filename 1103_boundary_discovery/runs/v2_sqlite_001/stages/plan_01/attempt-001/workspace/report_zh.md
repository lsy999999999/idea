# plan_01 规划报告

## 当前证据

- ledger_01 中 A1/B1 描述的是 SQLite 文档已知的 reader end-mark 限制；A2/B2 与 C1/C2 是尚未解决的调度问题。C3 是未检验的强代理假说：固定 snapshot position、reader 活动状态和 WAL head 后，较老 reader 仍会单独降低 PASSIVE 进度。
- bridge 与已核验 SQLite WAL 文档将 end-mark 机制视为已知，不能作为新发现。
- experiment_00 的 E02 实际完成 72 次真实 SQLite 回放，冻结分类为 `uncertain_or_tradeoff`。Heldout_H1 生命周期策略与两基线的 checkpoint 时间区间均包含零；所有运行末尾报告零残余帧。原计划 outcome 类要求两个 held-out shape，但只执行一个，因此该结果不能支持明确策略类别。

## 备选与选择

提出 E03：在配对新数据库中固定 reader snapshot、写入、WAL head 和 checkpoint 时点，只改变 reader 在写入 burst 前的存续等待时间，检验 C3 与 B1 对年龄是否有独立作用的相反预测。提出 E04：冻结第二个不同 release/burst 形状，以 12 个新执行顺序种子补做 C1/C2 的策略比较，专门处理 E02 的单一 held-out shape 缺口。

选择 E03。它直接隔离当前最容易被误当成信号的 reader age，并以真实 PASSIVE frame 计数给出可分类的结果；所需事务很少。E04 可行且关乎实际策略，但重跑三策略并使用一条新轨迹，成本更高，且 E02 暴露的串行回放与成本解释限制仍在。E03 即使得到年龄无效结果，也会收窄可用表示；它不构成 SQLite 文档机制的新发现或世界新颖性证据。

没有在本规划阶段运行实验。两计划的种子、分类和无效数据规则已写入 result.json，供后续实验角色冻结执行。
