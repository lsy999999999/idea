# 定向学习：评分分布与评分者来源

## 缺口

交流显示，逐位评分可以恢复中位数丢失的分布信息，但去身份的分数不能说明分布差异来自酒样、评委严厉度，还是评分流程。需要理解评分记录结构能支持哪些判断。

## 读到的来源与访问状态

- UCI Wine Quality 文档：https://archive.ics.uci.edu/dataset/186/wine+quality。完整文本已在给定输入的 `winequality.names` 中读取；本阶段在 `sources/uci_winequality_measurement_excerpt.txt` 保存评分构造和字段边界的相关原文。文档说输出是至少三位专家评分的中位数，专家评分范围为 0–10；表格只包含理化输入与感官输出等可用变量，不提供专家个体信息。它是数据集说明，不是评委一致性方法论文。
- Europe PMC 搜索：https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%28wine%20sensory%20panel%20assessor%20repeatability%29&format=json&pageSize=5。尝试请求，DNS 解析失败；无摘要/全文。精确错误及 URL 记录在 `sources/retrieval_failures.txt`。
- Crossref 搜索：https://api.crossref.org/works?query=ordinal%20inter-rater%20agreement%20sensory%20panel&rows=3。尝试请求，DNS 解析失败；无元数据/摘要/全文。精确错误及 URL 同上。

- 检索恢复后读取了来源 `K6a6a58450c07c23e`，*Large Language Models as Examinees and Graders in Simulated General Surgery Oral Board-Style Cases: A Psychometric Pilot Study*，https://doi.org/10.7759/cureus.113882。返回内容级别为 article body excerpt；实际保存快照 `/Applications/ideas/1103_boundary_discovery/evaluation_20261106_wine/requested_retrieval/accepted/K6a6a58450c07c23e.json`。其中原文称：“Generalizability theory decomposes observed score variance into its underlying sources, such as examinee ability, case difficulty, rater stringency, and their interactions”。方法段称使用 fully crossed person-by-rater-by-case design 估计 variance components。
- 读取来源 `K118ec9a5b92de666`，*Multimodal Large Language Models Rate Wetlab Suturing Repeatably but Fail to Detect Training-Related Improvement: A Pilot Study With Expert Assessment*，https://doi.org/10.7759/cureus.117189。返回内容级别为 article body excerpt；实际保存快照 `/Applications/ideas/1103_boundary_discovery/evaluation_20261106_wine/requested_retrieval/accepted/K118ec9a5b92de666.json`。原文将 leniency、severity 与 central tendency 描述为系统性 rater effects；其限制部分说明只有一位 expert rater，因此不能估计 inter-rater reliability。该小型手术技能评分研究不是葡萄酒感官研究。

前两项 DNS 失败记录仍保存在 `sources/retrieval_failures.txt`；后续控制端 KnowledgeBroker 成功返回材料，并不改变初次失败事实。以上两项新来源均非有序葡萄酒评分方法论文，故不声称它们给出了适用的 ordinal agreement 系数。

## 概念关系与 worked example

UCI 的中位数是每个样本评分向量的一个汇总量。设同三位评委对样本 A 给出 `4, 5, 6`，样本 B 给出 `1, 5, 9`：两者中位数都为 5，极差却分别是 2 和 8。这个手算例子说明聚合分本身不决定评分分散程度；它不是 UCI 数据中的观察。

再看身份信息：如果只拿到两组无身份分数，能描述各组的分布，但无法知道某个低分是否总由同一位严厉评委给出。保留“评委 × 样本”的链接，才能按评委观察跨样本的打分倾向；同一酒样有多个评委评分，则可观察同一样本上的跨评委差异。来源 K6a6a58450c07c23e 的跨对象/评委/案例设计说明，交叉结构可用于拆解多个方差来源及其交互；它支持一般设计概念，但其对象是口试评分，不是葡萄酒。来源 K118ec9a5b92de666 中“only one expert rater”导致 inter-rater reliability could not be estimated 的限制，也具体说明单评委设计无法估计评委间可靠性。重复性还需同一评委/样本在不同时间或条件下重复观测。

**Worked design example (hypothetical):** 两个评委分别给酒样 A、B 打分。若记录只有 A 的中位数和 B 的中位数，评委偏严可能被误读为 A/B 差异；若有完整交叉矩阵 `A:(6,5), B:(8,7)`，可见评委 2 对两个酒样都高 2 分，而两个评委都给 B 比 A 高 2 分。这个极简加性例子能把一个稳定评委偏移与样本差异在算术上分开；它不能检验现实数据中的交互、评分误差或有序量表模型假设，也不是 UCI 数据或论文中的数据。

## 对原理解的改变

我的原问题把重点放在“理化指标的关联在个体评分与聚合分之间是否稳定”。同伴追问后，我意识到单有逐位评分并不自动给出可归因的“评委层效应”：标识和重复/交叉结构决定能否区分评委严厉度与样本特异反应。因而当前应先问数据设计和目标量，再选一致性或预测分析。合成中位数预测、评委分歧描述、独立潜在感官属性仍是不同分支，尚未选择。

## 仍未掌握

这次学习让我把“原始分数”具体化为“与评委和样本相链接的交叉评分”。我仍不能说明 ordinal agreement 与 reliability 的规范定义差异、哪种一致性系数适用于有序评分、不同系数的假设和偏差，也不能给出层级序数模型的识别条件。可读来源属于外科评估，迁移到葡萄酒感官的量表特性需要专门来源。不能从当前 UCI 表推断专家实际分歧、评审可靠性或真实酒样质量。
