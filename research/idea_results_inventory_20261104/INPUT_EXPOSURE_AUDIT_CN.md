# Agent 是否看到原论文结果：输入核查

核查日期：2026-11-04。

**不能对所有实验作“agent 没看过原论文结果”的保证。** 必须区分作者的解释/结论与论文中的原始测量：原始测量本来就是研究输入。

| 实验 | 实际输入/访问设置 | 可以得出的判断 |
|---|---|---|
| RNA 首例、开发回放、V2 完整运行 | 研究输入包含选取的原论文实验测量；目标题名、DOI、摘要、作者机制和理论曲线隐藏。V2 背景检索截止 2025-05-12。 | 核查到的输入未直接提供目标论文的机制解释；但给了实测结果，不是“没有看过任何论文结果”。 |
| 六领域公开数据 | 核查 12 份实际 L1 初始输入，全部保留 UCI 官方数据说明和 intro_paper（题名/作者及部分 DOI），没有附原论文全文。L2 可收到 Crossref 文献题名及可得摘要。 | 没有设置统一的匿名论文盲测；不能声称来源身份与已有结论完全隔离。 |
| 葡萄酒/电商连续探索 | 六条序列首轮输入，以及全部 18 份逐轮 L1 输入，均含原论文题名与官方数据说明。后续允许 Crossref 检索。shopping_B/r1 的 L2 实际工具返回了电商来源论文题名与 DOI，摘要为空。 | 明确看到了论文身份线索；该次来源论文返回没有摘要。不能把整个实验称为未接触来源文献的独立发现。 |
| 河温 | 角色能联网阅读已有文献；实际理论分支保存并使用了 Fogg 等的摘要和其他论文。 | 已有结论属于允许查阅的背景。没有遮蔽目标答案的统一设置。 |
| SQLite | proposer/bridge 获准检索；实际角色报告引用 SQLite 官方 end-mark 机制和 Walack 摘要。 | reader 限制 checkpoint 的已知结论确实进入了研究过程；其重现不算独立恢复未知答案。 |

RNA 实际检查：`real_case_blind_20261102/agent_workspace`、`leader_rna_dev_v1_20261102/agent_visible`、`leader_rna_v2_20261102/runs/V2_full/inputs` 的已存文本中，未检出目标题名、目标 DOI 或 spinodal 关键词。关键词扫描是辅助核查，不等于完整的泄漏证明。运行隔离主要依靠输入白名单、角色协议与代理工具；也无法排除公开资料已进入模型训练。

本次汇总过程中读取的原论文及本报告，没有回传给这些已冻结研究角色。

核查来源：

- [六领域实际初始输入](/Applications/ideas/research/1031_question_boundary/cross_domain_idea_probe_20261102/runs/materials_1/inputs/L1.json)
- [葡萄酒实际初始输入](/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/format_recovery/runs/wine_B/r1/L1/input.json)
- [电商实际后续输入](/Applications/ideas/research/1031_question_boundary/idea_search_pilot_20261102/format_recovery/runs/shopping_B/r1/L2/input.json)
- [RNA V2 实际初始输入](/Applications/ideas/research/1031_question_boundary/leader_rna_v2_20261102/runs/V2_full/inputs/L1.json)
- [SQLite 检索角色任务](/Applications/ideas/1103_boundary_discovery/runs/v2_sqlite_001/dispatch/bridge.json)
- [河温角色已检索文献](/Applications/ideas/1103_boundary_discovery/runs/pilot_001/parallel_theory/sources/README.md)
- [机器可读输入核查](/Applications/ideas/research/idea_results_inventory_20261104/INPUT_EXPOSURE_AUDIT.json)
