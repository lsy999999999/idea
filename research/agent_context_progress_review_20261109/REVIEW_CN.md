# 从其他系统看上下文组织与假说推进

2026-11-09。检查此前小规模复跑使用的官方代码快照，并核对 EvoScientist 所用的已安装 deepagents 依赖。没有启动模型、修改科研代码，或声称核验了最新上游版本。

用户澄清：当前应优先检验系统能否产生新假说，或通过纠正旧假说产生新假说，成本优化不是当前主目标。上一轮由控制端设定的 240,000 输入/20,000 输出限制不足以完成当前多阶段流程；不能把预算截断或材料接纳失败解释为假说发展失败。没有确定或执行新的预算数值。

## 源码中的实际做法

| 系统 | 上下文与历史 | 如何继续工作 | 对我们有用的部分 |
| --- | --- | --- | --- |
| ResearchAgent | 问题、方法、实验设计分别有角色提示；同一生成者在迭代中保留完整自身消息。每轮评审使用独立调用。 | 当前问题/理由及具体反馈进入下一次修订；之后把选定问题交给方法角色。 | 为当前研究产物提供针对性反馈和作者继续改写的机会。不能声称它只发增量，旧历史仍会传入。 |
| Virtual Lab | 本次议程、相关材料、此前会议摘要；会议内部保留完整讨论，按发言者附加其角色提示。 | PI 在轮间综合意见、作出研究方向判断并追问；研究者可反对，也可在没有新增内容时 pass。个别会议让 critic 对最近回答给出改进意见，再由作者回应。 | 围绕具体科学分歧组织下一轮，而不是只检查所有输出字段是否齐全。 |
| AI Scientist-v2 | draft、debug、improve 各自组装任务输入；debug 收到父节点代码、执行输出和反馈；improve 收到父节点方案及研究进展摘要。 | 以具体节点/结果为下一次工作的起点；journal 汇总成功和失败，提示未来改进。 | 保持研究问题、当前对象和下一步动作的连接。它主要推进实验代码，不应把其实现成功直接当作新假说能力。 |
| EvoScientist 应用 | 文件工具与共享记忆；自定义 memory 中间件在模型请求中注入 MEMORY.md，已安装 deepagents 提供上下文摘要中间件。 | 工具异常转成 error ToolMessage，由 agent 决定重试、换路线或报告失败。 | 工具失败应反馈给当前任务决策；不能说别人一律不重复记忆，也不能把其应用实现等同于论文完整机制。 |

其他系统也会重复长历史、再次调用模型、重新生成完整回答。没有证据支持“其他系统普遍只发增量、不做重试”的概括。关键区别是，输入和后续动作通常围绕当前研究对象，而不是把整个框架的操作计划和终评说明无差别交给所有角色。它们也有不同程度的失败处理局限：ResearchAgent 的客户端重试结束可直接返回错误字符串；Virtual Lab 的未知工具会抛异常，并非都能稳定恢复。

## 我们目前应怎样理解问题

`learning_lab.py` 的通用 call 函数无条件设置 `all_inputs = [brief, POLICY, LAB/'PLAN_SOURCE.md', ...]`，因而材料整理阶段也收到完整 IDEA_CHECK.md 和 PLAN_SOURCE.md。这个职责分配问题值得修正，理由是让 agent 聚焦当前工作，而不是为了把科研输入压得越短越好。

当前假说、关键前提、相关证据、同伴争议、前序推理和适用的长期记忆，应有充分空间进入研究上下文；原文和完整历史仍应可回查。不能把全部内容替换成几句摘要，再要求模型自行恢复细节。

研究推进应围绕活的假说内容：研究者先形成条件性解释；同伴讨论其中的关系、遗漏因素或另一种解释；补学、推导、类比或必要计算服务于其中一个具体困难；作者据此发展或改变假说。不同意批评或暂不修改也可以成立。所谓推进，要在真实内容中看到新的解释关系、机制、适用结构或由旧假说改造而来的新假说，不以新字段、更多版本或普通算术纠错代替。

这些是从已有代码和本项目执行记录得到的设计建议，不是证明它们必然提升创造性。首先应完成一次不被接口或过紧预算截断的假说发展过程，再判断内容瓶颈；之后才有条件比较机制或优化消耗。

## 下一次能力观察的范围

1. 修正已知材料接纳错误，按角色组织指令；保留历史知识边界和受控测量例外。
2. 给研究者足够材料和推理空间，走完初始假说、实际补学/讨论、作者发展与再次讨论。材料不完备可以记录为缺口，不要求先解决全部定义才能提出条件性假说。
3. 保存前后假说及实际输入，检查究竟产生了什么新的科学内容。若停滞，定位是资料未到达、关系未理解、理解没有进入假说，还是同一假说被反复润色。
4. 根据完整流程预留预算；接近额度时结合已完成阶段和实质进展决定后续，不能默认继续沿用 24 万输入/2 万输出。预算停止单独报告，不算科学失败。

本次没有启动下一次试验，也没有指定新上限。原有失败运行保留。

## 主要源码入口

- [ResearchAgent 生成与反馈修订](/Applications/ideas/research/replication_selection_20261108/sources/code/researchagent/code/pipelines/agents/problem_identifier.py:38)
- [Virtual Lab 会议上下文](/Applications/ideas/research/replication_selection_20261108/sources/code/virtual_lab/src/virtual_lab/run_meeting.py:187)；[综合与追问提示](/Applications/ideas/research/replication_selection_20261108/sources/code/virtual_lab/src/virtual_lab/prompts.py:26)
- [AI Scientist-v2 的 draft/debug/improve](/Applications/ideas/research/replication_selection_20261108/execution/upstream/AI-Scientist-v2-96bd51617cfdbb494a9fc283af00fe090edfae48/ai_scientist/treesearch/parallel_agent.py:453)
- [EvoScientist 记忆注入](/Applications/ideas/research/replication_selection_20261108/execution/upstream/EvoScientist-ab709d4ec042ecfeceb8bd85165b2d96cae5ac67/EvoScientist/middleware/memory.py:693)
- [我们的统一输入构造](/Users/LSY/.codex/worktrees/a57d/ideas/1103_boundary_discovery/src/learning_lab.py:195)

完整文件哈希见 SOURCES.json。
