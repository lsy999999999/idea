# 定向学习：有序多评委评分的一致性与设计

## 缺口

交流前我把“取回逐位评分”视为解决中位数信息损失的首要数据补充，但还说不清：分数相似究竟指绝对值一致，还是样本排序一致；评委身份及交叉/重复设计又能识别哪些评分来源？

## 学到的关系

Hallgren (2012) 的方法教程区分了两类可被称为评分者间可靠性的目标：若关心评委给出的**绝对值是否相似**，使用 absolute-agreement 类 ICC；若关心评委对样本的**相对次序是否相似**，使用 consistency 类 ICC。两者可以不同，因为评委可对所有样本系统性偏高或偏低。教程同时提醒，ICC 选择要跟评分者如何抽样、同一批评委是否评相同对象、结果针对单个评委还是多个评委的平均分相匹配。

对序数评分，教程介绍按分歧幅度加权的 Cohen weighted kappa：高与低之间的差异可以比高与中之间惩罚更大。它是两评委方法；教程提到在特定假设下，quadratic weighted kappa 与 two-way mixed、single-measures consistency ICC 等价。这不自动说明该 ICC 最适合任何 0–10 评分，也不解决 3 名以上评委的序数聚合方案。

设计上，所有评委评价共同酒样的 fully crossed 结构可让评分者系统偏差被评估和控制；若每个酒样由不同的评委子集评价，评委身份与酒样构成可能混在一起。对葡萄酒问题，逐位评分应尽量带有酒样ID、评委ID；重复同一评委评分或跨批次重复酒样可进一步触及重测、批次和评委×酒样差异，但各分量如何估计仍要按具体采样结构建模。

## 学习算例

构造 5 个序数样本，评委 A 评分 `[1, 2, 3, 4, 5]`，评委 B 评分 `[2, 3, 4, 5, 6]`。B 每次都比 A 高 1 分，因此两人的样本排序完全一致（Spearman ρ = 1），但逐个样本的 exact agreement 为 0/5；平均有符号差为 +1。于是“排序一致”是完美的，“绝对值一致”却不完美。这个算例只验证目标区别，不是实际葡萄酒数据，也不计算 ICC 或 Kappa。

同理，若一项应用只关心把酒样排序，系统性评分偏移可能可接受；若要把不同评委的分数合并成可解释的共同等级，则偏移会实质影响绝对评分。这是目标与指标的对应关系，不是对 UCI 评分流程的事实判断。

一篇工程教育评估的摘要把“相差不超过 1 分”与“完全相同”分开报告：其七项评估中，前者 agreement 为 85%–100%，exact agreement 为 20%–60%。这说明容差阈值改变 agreement 的含义；该来源是不同领域的实例，不是葡萄酒证据或通用方法规范。

## 对初始理解的改变

我现在会把问题先写成待选择的 estimand：既定流程的中位数预测、绝对评分可互换性、样本排序一致性、评委分歧/稳定性，或潜在感官属性。逐位评分只恢复了分布层的信息；若不保留评委与酒样的链接，无法把系统性评委偏移与酒样反应分开。即使有这些链接，可靠性/一致性也不等于效度：评委可以高度一致但不一定测到所称的感官构念。

## 来源与获取

1. Hallgren, K. A. (2012). “Computing Inter-Rater Reliability for Observational Data: An Overview and Tutorial.” *Tutorials in Quantitative Methods for Psychology*, 8(1), 23–34. DOI: <https://doi.org/10.20982/tqmp.08.1.p023>. PMC: <https://pmc.ncbi.nlm.nih.gov/articles/PMC3402032/>. PMC 全文 HTML 成功获取并保存为 `source_hallgren_2012.html`；用 Pandoc 转为可读文本 `source_hallgren_2012.txt`。实际阅读段落：Primer on IRR、How are studies designed to assess IRR?、Cohen's weighted kappa、Common ICC variants。全文可用；它是行为观察教程，非感官/酒类综述。
2. “Establishing Inter-rater Agreement for TIDEE's Teamwork and Professional Development Assessments.” <https://doi.org/10.18260/1-2--17920>. 本地保存 `source_tidee_2020_abstract.txt`；仅有索引摘要。只用作 exact 与 within-one-point agreement 的领域实例，不迁移其数值结果。

我的首次 PMC 请求遇到 DNS 失败，随后授权网络调用成功取得 Hallgren 全文。另一次猜测性 PMC URL 实际返回无关的制剂颗粒测量文章，未用于学习；文件保留但不是本阶段证据。控制端检索另有多条候选摘要，我只实际阅读了其明确指定返回、且与 agreement 容差说明相符的 TIDEE 摘要及上述教程，不声称读完候选池。

## 仍未掌握

Hallgren 教程把 inter-rater reliability 与 inter-rater agreement 近似并称；它澄清 absolute agreement 与 consistency 的 ICC 类型，但没有给出足够一般的 agreement-versus-reliability 概念论证。教程的 ordinal weighted kappa 讨论限于两评委；UCI 有至少三评委且缺少个体数据。因此我仍不能推荐本数据的具体估计量、样本量、方差分解模型或潜在质量识别策略。当前也未获得酒类感官评审的专门方法来源。
