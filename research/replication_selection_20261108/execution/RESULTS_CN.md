# 四套科研 agent 的小规模实际运行结果

日期：2026-11-08。按“尽快得到结果、每套先跑一个案例”执行。本地完成三套，GPU 实验使用用户标注优先的服务器 `10.42.127.214`，未使用备用服务器。

四套均取得真实模型输出，其中 AI Scientist-v2 还执行了生成的 GPU 实验。采用同一个可用的快速模型 GPT-6 Luna，reasoning effort 为 low。这些是**官方流程的小规模适配运行**；模型、预算和部分输入接入方式与论文实验不同，结果不作为原论文表格数值的复现或方法排名。

## 完成情况

| 系统 | 位置 | 本轮范围 | 成功运行阶段用时 | 实际产物 |
|---|---|---|---:|---|
| ResearchAgent | 本机 | 一个电池文献案例；问题、方法、实验设计各两轮，保留五维 reviewer | 189 秒 | 问题、方法、实验设计及全部逐轮反馈；36 次模型响应 |
| Virtual Lab | 本机 | 同一材料；PI、electrochemist、dynamical systems researcher，一轮团队讨论加 PI 总结 | 110 秒 | 四次真实模型发言、会议记录与研究建议 |
| EvoScientist | 本机 | 官方发布期应用代码；一个材料案例，加一次新 graph／新会话读取已存记忆的续接 | 74 秒 | idea、独立记忆文件、续接后形成的另一方向，以及文件读取记录 |
| AI Scientist-v2 | 优先服务器 RTX 3090 | 一个 idea，原始 MinimalAgent 的一个实现节点、官方执行器和审阅；未运行完整四阶段搜索 | 165 秒；其中实验执行约 3.3 秒 | 生成的研究提案、训练代码、GPU 日志、指标、图、agent 审阅结果 |

时间列不含前期安装、接口修复和中断尝试。所有失败记录保留，未把服务／环境故障计作科学能力缺陷。

## 研究想法和具体观察

### ResearchAgent：生成了方向，修订主要使研究设计更具体

第一轮问题：能否以温度／SOC 感知且不确定性校准的 EIS 模型，使用快速、部分频率测量，同时估计电池 SOH 与主要退化模式，并推广到不同电池和老化协议？

第二轮保留这个方向，增加单一化学体系、两种受控老化协议、预先固定频率带、独立退化模式诊断、留出电池／协议、对照方法及预测区间覆盖率。方法部分进一步提出随机分组、批次控制、独立诊断和误差／覆盖率评价。

模型 reviewer 的问题 Originality 评分为 **3→3**，Feasibility 为 **3→4**。这是同模型的内部评分；直接可见的变化是研究边界和设计更具体，核心假设没有发生明显转向。这个案例没有显示“反复评审自然产生新的解释框架”。

另一个输入层面的观察：按原始知识共现公式检索的 30 个实体里，出现 Executive information system、Enterprise information system、State-owned enterprise 等与电池语境不匹配的实体，提示缩写／实体消歧值得单独检查。当前结果没有估计这些噪声对 idea 的因果影响。

原始结果：[result.json](/Applications/ideas/research/replication_selection_20261108/execution/runs/researchagent/result.json)。

### Virtual Lab：形成了有内容的学科互补

电化学角色强调：阻抗特征不是退化机制的唯一标识，SOC、温度、等效电路和非稳态因素会混在一起。动力系统角色把问题转向可辨识性，提出通过纵向测量区分缓慢老化与较快变化的工作条件。

PI 最终建议：**检验纵向 EIS 能否在未见过的电池和老化协议上，稳定识别独立于 SOC／温度变化的容量型 SOH。**

这轮讨论确实吸收了两个角色的意见，但输出仍围绕测量混杂、泛化和验证协议展开。它提供了研究方向，尚无新变量／新机制或世界新颖性的证据。

会议：[meeting.md](/Applications/ideas/research/replication_selection_20261108/execution/runs/virtual_lab/meeting.md)。

### EvoScientist：新会话确实读了记忆；假设修订由提示明确引导

初始 idea：**结合工作条件归一化和退化模式敏感表示，改善 EIS 的跨条件 SOH 估计。** 系统把经验写入独立的 `ideation-memory.md`。

第二次创建新的 graph／thread，仅给续接问题。工具记录显示，它实际读取了已存记忆和前一个 idea，随后改问：**温度／SOC 与老化是否真的可分离？条件归一化是否可能同时抹掉真实老化信号？** 新方向比较原始特征、条件归一化和显式条件×老化交互表示。

这次观察支持“文件记忆能被新会话使用，并参与修订”。续接提示明确要求修改一个假设，因此不能把变化全归因于记忆；本轮没有做无记忆对照，也没有复现论文三角色、两类记忆的完整效果实验。发布期官方应用仍是另一个实现层次，与论文角色划分的对应问题保留。

结果：[idea.md](/Applications/ideas/research/replication_selection_20261108/execution/runs/evoscientist/workspace/idea.md)、[continuation.md](/Applications/ideas/research/replication_selection_20261108/execution/runs/evoscientist/workspace/continuation.md)、[记忆](/Applications/ideas/research/replication_selection_20261108/execution/runs/evoscientist/memory/ideation-memory.md)。

### AI Scientist-v2：代码跑通，但研究问题与测量之间出现了错位

系统自主提出：**网络先学到捷径后，即使后期移除捷径，是否仍难以恢复对稳定信号的学习？**

生成的程序使用两维合成输入、小 MLP 和三个训练条件：从开始屏蔽捷径、持续暴露捷径、前三轮暴露后两轮屏蔽。每种条件训练五轮；程序自行使用了十个随机种子。每种子 2,048 个训练样本、512 个验证样本、2,048 个测试样本。日志确认 `Using device: cuda`。

程序打印的测试准确率：

| 条件 | 带随机捷径特征的测试准确率 | 验证集统一将捷径设为零后的准确率 |
|---|---:|---:|
| 从开始屏蔽捷径 | 82.6% | 83.8% |
| 持续暴露捷径 | 66.0% | 83.4% |
| 后期屏蔽捷径 | 65.2% | 83.5% |

**这些差值不能直接解释为“恢复学习的代价”。** 源码在训练时将部分条件的第二个输入设为零，但主测试让所有条件接收一个随机捷径输入，没有统一屏蔽它。因而测试同时测到了模型对随机捷径的响应；特别是后期屏蔽条件保留了早期学到的捷径响应。程序已有的统一屏蔽验证输出反而很接近。要回答恢复问题，需要重新对齐干预、评估输入与训练预算。

系统自己的审阅器将节点标记为 `is_buggy=true`，指出了训练与验证输入处理不一致；它的文本没有明确指出上述主测试与恢复估计的错位。原始节点和程序保持冻结，本轮不继续扩展搜索或修复科学设计。

这是本轮最具体的局限线索：**自动生成代码并成功执行，仍可能没有测到最初想问的东西；自动审阅能抓住一部分问题，但覆盖不完整。** 这一观察来自一个适配后的单节点案例。

程序：[code_attempt_0.py](/Applications/ideas/research/replication_selection_20261108/execution/runs/scientist_v2/server/code_attempt_0.py)；真实日志：[executions.json](/Applications/ideas/research/replication_selection_20261108/execution/runs/scientist_v2/server/executions.json)；agent 审阅：[node_attempt_0.json](/Applications/ideas/research/replication_selection_20261108/execution/runs/scientist_v2/server/node_attempt_0.json)。

## 数据、来源与复现偏差

三个电池案例均使用 ResearchAgent 原始论文列表中的综述 *State-of-health estimation of lithium-ion batteries based on electrochemical impedance spectroscopy: a review*，DOI [10.1186/s41601-023-00314-w](https://doi.org/10.1186/s41601-023-00314-w)。输入是原论文摘要、Semantic Scholar SPECTER-v2 余弦相似度选出的十篇参考文献摘要，以及原始知识库公式给出的三十个实体。**未使用原始电池测量数据。** 三套系统没有收到本项目历史候选或共享研究记忆。

- ResearchAgent 固定源码 `babb49b51ebfcebedc39ccde12c9785be7bef46c`；三阶段默认三轮减为两轮；原提示、五维评价和选择流程保留。NumPy 实现相同余弦／共现公式，排序替代 torch.topk。
- Virtual Lab 固定源码 `8a3a4fd9ccc0cd297bd523751e03bc9527c91832`；调用官方会议函数，角色配置和材料由本轮给定；未调用 PubMed，未复现抗体实验。
- AI Scientist-v2 固定源码 `96bd51617cfdbb494a9fc283af00fe090edfae48`；保留原构思、实现、执行与审阅函数；新增短计算预算输入；四次 Semantic Scholar 搜索均为 HTTP 429，文献查新未完成。
- EvoScientist 应用源码 `ab709d4ec042ecfeceb8bd85165b2d96cae5ac67`；使用 0.4.9 版 deepagents；独立工作目录与记忆，未修改项目既有记忆。首次缺少依赖、第二次 graph 步数上限过低的记录保留，修复后完成。
- 原流程的 Chat Completions 传输适配为已授权服务的 Responses；不支持的 temperature 参数未传，输出上限作了短运行调整。模型响应和实际 usage 保存在各 `calls/` 中；本轮不估算第三方计费。
- 服务器模型请求通过 SSH 交给本机发起；模型服务密钥没有写入服务器实验目录或结果文件。远端结果目录 `/home/lsy/ideas_replication_20261108/results` 已拉回本机。

## 下一步最值得复现的问题

优先围绕两个具体现象设计后续小对照：ResearchAgent 的 reviewer 如何影响问题收窄／转向；AI Scientist-v2 的实验审阅能否发现“程序运行成功但估计目标错位”。EvoScientist 已提供一个受引导的假设修订例子，后续可在相同提示下比较带／不带记忆。本轮没有给四套方法排名。
