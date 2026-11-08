# 持续协作与研究问题形成：实现思路及相关工作

日期：2026-11-04。对应用户问题：这段过程是否通过 prompt 完成，以及是否已有研究——材料引起注意，研究者表达困惑，交流改变理解，继续学习，再形成原先未明确提出的问题。

这是定向文献核查与设计讨论。本次没有修改 agent_learn.md、启动研究角色或实现新流程。

## 实现判断

第一版可以采用现有模型，以 prompt 引导每次认知动作，以程序维护来源、问题线索、回应、版本和后续任务。以下职责需要分开：

| 环节 | 模型与 prompt 的工作 | 程序的工作 |
|---|---|---|
| 注意到值得讨论的材料 | 结合领域知识指出困惑、联系或前提，给出简短依据 | 提供相关原文与知识记忆，保存引用 |
| 表达疑问 | 说明当前理解、不确定之处及想请别人帮助理解的部分 | 为线索分配稳定标识，链接原材料 |
| 他人回应 | 澄清、追问、补充知识、提出不同理解或说明类比不成立 | 把回应连接到具体线索，并交回相关研究者 |
| 修改理解 | 解释哪些观点保留、改变、分支或仍不确定 | 保留前后版本及回应关系，不覆盖不同观点 |
| 补充学习 | 指出缺口，学习后说明新增理解 | 实际执行检索/阅读，保存资料，恢复待讨论线索 |
| 形成 idea | 将逐渐清晰的问题或假说写出来 | 保留形成过程，随后执行用户规定的两项最终检查 |

程序可以确保这些动作确实发生并且可追溯；科学理解是否改变、问题是否有价值，不能由字段完整或调用成功推断。

建议先围绕一条可修改的问题线索做原型，而不从全员轮流发言或完整科研流程开始。线索保留材料引用、当前理解、疑问和版本；回应标明针对哪条线索、带来什么依据、建议怎样理解。字段只作为轻量记录，不要求每条发言都重新生成完整 idea。

一个可用的交流模式是：A 提出困惑；B 针对某个具体前提提出追问或不同解释；A 回应哪些理解发生变化，或解释为何保持原判断；需要时双方补充学习，随后继续同一条线索。研究者可以直接提出替代解释，不必每次机械复述对方，也不强迫接受批评。只记录可交流的解释、依据和改写，不把模型生成的解释当成不可见内部推理的真实记录。

协调工作维护待回应的疑问及学习请求，给相关研究者发送有针对性的上下文。允许回到原始材料、保留分支、撤回线索或邀请新领域。先保留少量互动操作，再依据真实讨论决定哪些需要固定。最终 check 仍只处理方向近似已有工作和明显数学/逻辑错误。

## 本轮核查到的工作

### 1. CoQuest / How AI Processing Delays Foster Creativity

- 正式发表题名：*How AI Processing Delays Foster Creativity: Exploring Research Question Co-Creation with an LLM-based Agent*，CHI 2024。
- DOI：https://doi.org/10.1145/3613904.3642698
- 作者公开稿题名：*CoQuest: Exploring Research Question Co-Creation with an LLM-based Agent*；本轮读取 https://arxiv.org/html/2310.06155v3 。
- 重点阅读：§5.1–5.2，尤其 §5.2.1；核对研究设计与摘要。
- 直接机制：研究问题流程图、论文图、问题之间的生成解释；用户基于具体问题提供反馈，系统可以横向扩展或纵向深入。后端采用 ReAct 风格的动作选择，允许文献发现、假想使用情境、缩小范围、与已有工作比较；输出动作由 Python 函数执行，再把结果加入下一步上下文。
- 与我们关系：直接研究问题怎样在人机往返中形成，是“只有 prompt 吗”的具体实现参考。
- 范围：20 位 HCI 研究者的人机研究，不能据此推断多个持久领域 agent 已能自主共同发现新问题。展示的生成解释也不等于模型内部认知过程。

### 2. IdeaSynth

- *IdeaSynth: Iterative Research Idea Development Through Evolving and Composing Idea Facets with Literature-Grounded Feedback*，CHI 2025。
- DOI：https://doi.org/10.1145/3706598.3714057
- 本轮读取作者公开稿 https://arxiv.org/html/2410.04025v1 ，Crossref 核对正式发表信息；版本可能与会议终稿不同。
- 重点阅读：§4.1 的使用情境、§4.2 节点画布、§4.3 文献支撑反馈、§4.4 实现。
- 直接机制：把问题、方案等组成部分表示为可编辑节点；生成澄清问题、替代版本和扩展建议；依据用户收集文献提供节点级反馈，连接和组合不同节点。使用提示模板、外部文献处理、交互记忆与界面共同实现。
- 与我们关系：非常接近“共享一个可修改对象，交流后更新局部理解”。值得借用节点、版本、文献依据和局部反馈，没必要照搬其完整论文项目构成。
- 范围：人主导的 idea 发展，作者报告 20 人实验室研究及 7 人部署研究；不是自主多 agent 交流能力的证据。

### 3. ResearchAgent

- *ResearchAgent: Iterative Research Idea Generation over Scientific Literature with Large Language Models*，NAACL 2025。
- 论文页：https://aclanthology.org/2025.naacl-long.342/
- 原文：https://aclanthology.org/2025.naacl-long.342.pdf
- 重点阅读：正式论文 §3，尤其文献/实体知识增强和 Iterative Research Idea Refinements；摘要及方法中的提示模板说明。
- 直接机制：从核心论文及引用关系扩展文献，使用实体共现知识库补充跨域概念，生成问题、方法、实验设计；多个 ReviewingAgents 提供反馈，ResearchAgent 根据反馈修订。模型参数通常固定，任务通过模板与上下文实例化。
- 与我们关系：明确生成研究问题并让其他 agent 的反馈改变提案，属于直接近邻，不能把它概括成只回答预先给定的问题。
- 范围：主要组织为“生成者—评审者—修订”。本文未据此确认具备我们讨论的跨任务持续学习领域研究者，或逐条困惑双向演变的完整机制。

### 4. Virtual Lab

- *The Virtual Lab of AI agents designs new SARS-CoV-2 nanobodies*，Nature 2025。
- 论文：https://doi.org/10.1038/s41586-025-09442-9
- 官方代码与公开讨论：https://github.com/zou-group/virtual_lab
- 本轮阅读：正式网页摘要、代码可用性说明、部分扩展图说明与官方 README。Nature 网页仅提供订阅预览，未读完整正文、会议执行源码或复现结果。
- 直接机制：Principal Investigator 与专业研究者开展团队会议和单独会议，人类提供高层指导。README 说明团队会议讨论人类提出的议程，个人会议处理具体研究任务。
- 与我们关系：提供真实公开的多角色科研会议与执行过程，是观察交流怎样承接的入口。
- 范围：论文的具体示范是既定纳米抗体设计任务，不能直接等同从开放科学情境自主形成研究问题。

### 5. Towards an AI co-scientist

- 本轮读取 2025 年公开稿：https://arxiv.org/html/2502.18864v1
- 重点阅读：§3.1–3.3.2。
- 直接机制：定制 prompt 的生成、反思、排序、演化等 agent；Supervisor 管理异步队列与资源；持久 context memory 保存系统状态；Meta-review 的反馈加入后续 prompt。生成模块还包含模拟讨论与逐步识别假设。
- 与我们关系：直接说明 prompt、持久记忆、任务调度是互补部件，也说明通过反馈更新下一轮上下文已有具体实现。
- 范围：以科学家给定研究目标为入口，通过假说生成、评审、锦标赛与演化推进。部分研究任务有实验验证，并不意味着全部新颖性判断或自治问题形成均已解决。本条按所读公开稿描述，不以此声称核查了最新期刊版本。

### 6. Towards AI Agents Supported Research Problem Formulation

- 2026 IEEE/ACM Workshop on Methodological Issues with Empirical Studies in Software Engineering (WSESE)。
- DOI：https://doi.org/10.1145/3786149.3788302
- 作者公开稿：https://arxiv.org/html/2512.12719v1
- 重点阅读：摘要、§3.1 的五阶段设想及场景说明；Crossref 核对 workshop 出处。
- 直接内容：基于 Lean Research Inception 的问题看板，讨论 AI 如何帮助整理背景、对齐不同参与者视角、修订研究问题和辅助决定。
- 与我们关系：主题直接涉及“通过协作形成问题”。
- 范围：作者明确称为 vision paper，使用描述性场景评估，并要求后续经验验证；不能当作已经验证有效的自主协作系统。其可行性/应用价值评分也不应移植成我们候选的新增门槛。

## 如何使用这些工作

优先从 CoQuest 学习“围绕一条研究问题继续行动”，从 IdeaSynth 学习“可修改的共同研究对象”，从 ResearchAgent 和 Virtual Lab 阅读具体反馈或会议记录，从 AI co-scientist 理解持久状态与任务调度怎样接在 prompt 周围。

我们提出的“围绕线索持续协作”与上述方向存在实质重合。本轮没有建立一个无人研究的空白，也没有找到足够证据认定用户所描述的整条能力已经被完整解决。当前值得落实的是一个轻量、可接续的交流过程，观察疑问如何实际被理解和改写；不急于给它增加论文评测或原创性标签。

## 检索与访问记录

使用 Crossref、OpenAlex、arXiv API、ACL Anthology、Nature 和作者官方仓库定向核查。检索包含 CoQuest、IdeaSynth、Virtual Lab 题名，以及 collaborative scientific problem formulation agents。另检索到 AgenticSciML、SCION 和 Hearsay-II，当前仅作线索，不用于本报告的详细机制判断。

ResearchAgent PDF 两次整文件下载超时，之后续传成功，能够完整提取正文；保留完成的 PDF。IdeaSynth 的首次 Crossref 响应异常，改用简短题名重试后成功。Virtual Lab 官方 README 首次请求超时，重试成功。未把未读完整的方法或索引摘要表述为完整复现。原文快照、提取文本和索引记录见 raw/ 与 SOURCES.json。
