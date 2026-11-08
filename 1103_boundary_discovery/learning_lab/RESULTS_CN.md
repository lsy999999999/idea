# 持续学习与共同提问：执行与两组测试结果

依据 `/Applications/ideas/agent_learn.md`，已实现并实际运行“持久研究者—独立理解—交流—针对性补学—再次交流—候选检查—记忆接续”的小型流程。两组测试共完成 **24 个逻辑阶段**，形成 **2 个候选**；最终检查均为 **已有相近方向、未见明显数学或逻辑错误**。本轮的明确成果是知识积累、问题细化与跨任务复用，尚未确认新的研究贡献。

测试使用公开论文材料，执行的是研究者学习与讨论流程。研究模型请求为 GPT-6 Luna。首段材料整理用 medium，后续用 low。两组首批成员由主控选定；讨论中实际出现的知识缺口决定补学内容，主控根据重复缺口安排了阅读分工。

## 结果概览

| 测试情境 | 最终候选 | 方向查重 | 数学/逻辑粗筛 |
| --- | --- | --- | --- |
| 微生物群落恢复 × 物理/动力学 | 重复扰动下回归、测量与预测状态的分层判读 | 已有相近方向 | 未见明显错误 |
| 免疫记忆 × 物理/动力学 | 群体响应预测与微观来源的可识别性 | 已有相近方向 | 未见明显错误 |

所有候选、未决分支和检查原文均保留。完整机器汇总见 [AUDIT.json](AUDIT.json)，操作说明见 [README.md](README.md)。

## 第一组：微生物群落恢复

共同材料包括 Renes 等的连续培养研究：[Disturbance History Shapes Microbial Community Assembly and Predictability in a Continuous Culture System](https://doi.org/10.1111/1462-2920.70430)，以及 [Fundamentals of Microbial Community Resistance and Resilience](https://doi.org/10.3389/fmicb.2012.00417)。主研究报告 50 天、26 个采样点的重复盐度扰动；其已发表观察、作者机制解释和检测阈值解释分别保留。

| 过程 | 实际出现的内容 |
| --- | --- |
| 生态学者初始理解 | 丰富度、组成和功能可能有不同的恢复轨迹；“恢复”要绑定观测量、参照和时间窗。 |
| 物理研究者初始理解 | 当前测得的变量是否足以预测下一次响应？同一观测值可能对应不同的未观测状态。 |
| 交流触发的缺口 | NST 究竟比较什么，能否把它当作群落状态或随机性的直接测量？ |
| 针对性补学 | 核对案例的 PF 零模型、999 次随机化；学习四个重复形成六个配对时的共享样本依赖。 |
| 再次交流 | 共同区分测序投影与检出过程、距离及零模型推断、针对未来响应的状态充分性；保留多个解释分支。 |

最终候选问：**当不同轨迹给出不同的“恢复”判断时，差异来自响应对象、测量过程、模型参照，还是预测状态遗漏？现有资料能区分到哪一层？**

查重找到 [On the dimensionality of ecological stability](https://doi.org/10.1111/ele.12086)，以及 [Random sampling associated with microbial profiling leads to overestimated stochasticity inference in community assembly](https://doi.org/10.3389/fmicb.2022.1011269)。它们分别覆盖多维稳定性判读、抽样对零模型推断的影响，因此本候选作为既有方向的具体化保留。

查看：[完整候选](../runs/learn_20261104_community/ideas.json)、[两项检查](../runs/learn_20261104_community/check_report.json)、[所有分支](../runs/learn_20261104_community/stages/06_candidates/native-001/workspace/BRANCHES.md)。

## 第二组：免疫记忆

共同材料为 [Trained immunity in recurrent Staphylococcus aureus infection promotes bacterial persistence](https://doi.org/10.1371/journal.ppat.1011918) 与 [The causes and consequences of trained immunity in myeloid cells](https://doi.org/10.3389/fimmu.2024.1365127)。保留了宿主炎症读数、细菌抗生素耐受终点及其不同实验支路，作者关于训练性免疫和代谢变化的解释作为文献知识输入。

| 过程 | 实际出现的内容 |
| --- | --- |
| 免疫学者初始理解 | 区分宿主髓系状态、细胞群体构成和细菌耐受表型。 |
| 物理研究者取回旧知识 | 实际使用第一组的 `state_memory_observability` v3，迁移“观测与预测目标”的提问框架。没有把 ASV、NST 或旧生态假说当作免疫事实。 |
| 交流触发的缺口 | 硫乙醇酸诱导的腹腔巨噬细胞是否是均一群体？平均读数如何区分细胞内变化与群体构成变化？ |
| 针对性补学 | 阅读 [Revisiting Mouse Peritoneal Macrophages: Heterogeneity, Development, and Function](https://doi.org/10.3389/fimmu.2015.00225)，学习 LPM/SPM 的异质性；用混合模型检查均值的非唯一解释。 |
| 再次交流 | 给混合关系补上可加性、检测线性、有效权重、存活和细胞间作用等条件；分别讨论群体预测与微观来源识别。 |

最终候选问：**明确刺激历史、取样流程和挑战条件后，群体读数能预测哪个功能终点？若要区分细胞内变化、有效组成权重、存活或细胞间作用，还需要哪些配对信息与测量条件？**

查重以 [SCDC: bulk gene expression deconvolution by multiple single-cell RNA sequencing references](https://doi.org/10.1093/bib/bbz166) 为最相近来源，判为已有方向。相近之处是混合 bulk 信号的组成分解及组成—表型关联；目标感染实验中的具体识别条件仍作为未决问题保留。

查看：[完整候选](../runs/learn_20261104_immune/ideas.json)、[两项检查](../runs/learn_20261104_immune/check_report.json)、[所有分支](../runs/learn_20261104_immune/stages/06_candidates/native-001/workspace/BRANCHES.md)。

## 持久知识是否真的被使用

第二组物理研究者的输入包实际取回了第一组的两条当前版本笔记：`state_memory_observability` v3、`microbial_nst_pairwise_dependence` v2。输出明确记录使用前一条及其适用边界。可以逐项对照 [取回输入](../runs/learn_20261104_immune/memory_retrieval/nonequilibrium_physicist.json) 与 [研究者输出](../runs/learn_20261104_immune/stages/02_initial_1/native-001/workspace/result.json)。

两组还分别执行了一个全新调用，仅用简短情境和取回的笔记接续。第二组新调用使用本组保存的观测边界、混合均值和检查经历记录，给出下面的教学例子：

| 情形 | 两类细胞的输出 | 权重 | 群体均值 |
| --- | --- | --- | --- |
| A | 8、2 | 0.25、0.75 | 3.5 |
| B | 5、2 | 0.5、0.5 | 3.5 |

在明确假定线性加权的条件下，相同均值与不同的细胞响应和组成相容。接续问题因而是：需要哪些额外观测，才能区分这些来源？数字是学习构造，未用于推断原实验的细胞组成。

查看：[第一组接续](../runs/learn_20261104_community/stages/08_fresh_continuation/native-001/workspace/CONTINUATION.md)、[第二组接续](../runs/learn_20261104_immune/stages/08_fresh_continuation/native-001/workspace/CONTINUATION.md)。这证明了本轮确实发生知识取回和使用；相对于无记忆流程的效果差异尚未做对照。

## 留下了什么

| 稳定研究者 | 当前记录数 | 保存的版本总数 |
| --- | ---: | ---: |
| 微生物生态研究者 | 3 | 6 |
| 物理/动力学研究者 | 6 | 10 |
| 免疫学研究者 | 5 | 7 |
| 合计 | **14** | **23** |

14 条当前记录包括 10 条概念/理解记录和 4 条研究经历记录。每条含来源任务、原结果路径、知识类型、解释或使用例子、适用条件和疑问。研究经历同时保存最终查重与数学判断；旧版本和原始输出保留。

可从 [研究者目录](researchers/) 和各任务的 `memory_retrieval/`、`native_dispatch/`、`stages/` 回看。检索目前采用词项匹配并提供知识索引；每次最多取回四条完整笔记。当前知识规模较小，尚未测试更大资料库下的检索质量。

## 质量检查与实际边界

- 11 项程序测试通过，覆盖版本保留、纠正、重复提交、来源改动检测和原生角色交接；见 [TEST_RESULT.json](TEST_RESULT.json)。
- 两组均为 `complete`，各 12 个逻辑阶段；78 项产物及记忆来源完整性核对通过，见 [AUDIT.json](AUDIT.json)。这些是工程完整性检查，候选质量由前面的两个独立判断说明。
- 发现一处学习自述把原本已知的 NST 模型依赖写成新纠正。对照初始笔记后，后续讨论和候选记录将实际增量限定为具体方法设置、配对依赖与书目订正。
- 修正了一个 DOI 拼写，并记录两处短文作者姓名错误。长期记录仍可追溯到原始来源与旧版本，综合报告按正确题名、DOI 引用。
- 第一组初始生态角色曾读取全局共享研究摘要，已在 [输入接触记录](../runs/learn_20261104_community/INPUT_EXPOSURE_NOTE.json) 中保留。两组都使用已发表论文及其解释，本轮不作为独立重发现或盲测。
- CLI 出现超时和 429 后，保留部分产物并通过原生 Luna 子代理接续；来源通道、派发输入及结果分别记录，见 [执行通道说明](EXECUTION_ADAPTER_CHANGE.md)。主控还参与了两次补学分工与质量纠正，本轮完成的是有人组织的小型研究过程。

本轮产出主要集中于测量解释和可识别性。两位研究者的问题确实随材料和交流变得具体，旧知识也进入了新的研究情境；两个最终候选都落在已有研究方向内，因此保留为学习与后续研究入口。
