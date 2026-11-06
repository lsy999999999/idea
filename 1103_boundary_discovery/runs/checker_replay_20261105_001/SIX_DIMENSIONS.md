# 六维目前怎么处理

六维是同一 checker 的比较框架；没有六个独立 agent、六个打分或加权总分。数学/逻辑粗筛另存。

## 第一层：原始 idea 的六项描述

`idea_card` 保存 problem、mechanism、contribution、assumptions、validation、application 六个字符串。缺失信息用 `not specified`，不补造算法、假设、成功结论或验证结果。

| 维度 | 要回答什么 | 未给出时的处理 |
| --- | --- | --- |
| Problem | 研究的具体问题是什么？ | 保留问题表述的歧义 |
| Mechanism | 提出什么方法、因果机制或工作原理？ | 未提出机制可以保持未知 |
| Contribution | 声称新增什么能力、关系、结论或问题？ | 从原文提取待研究主张 |
| Assumptions | 对哪些对象、条件和适用范围成立？ | 不假定隐含的更强或更弱条件 |
| Validation | 提出怎样的验证或识别设计？ | 尚未设计也不淘汰 idea |
| Application | 研究哪些领域、数据或场景？ | 作为比较背景，不独立决定新颖性 |

## 第二层：每篇近邻文献的六维比较

每个入选来源都有 `comparisons[].facets`，六项各存 `{relation, reason, evidence_ids}`。关系为 EQUIVALENT / PRIOR_COVERS_IDEA / PARTIAL_OVERLAP / RELATED_ONLY / DISTINCT / UNKNOWN。确定关系必须引用该来源的证据；信息不足写 UNKNOWN。程序核对来源快照存在、引文逐字出现和引用对应，语义是否成立仍由模型判断。

例如：相同免疫研究场景不能单独推出贡献已覆盖；论文摘要未写出候选的存活/互作细节，也不能据此断言该工作没有研究这些机制。需要定位到相应文本，或记未知。

## 第三层：原始核心主张与已有工作逐项比较

从原始候选抽取 1–5 条主张/问题，绑定原文片段。每篇来源对每条主张给覆盖关系。六维帮助模型形成这些比较，程序汇总的是主张覆盖，不是六维相似性。若贡献是理论结果，覆盖还要求已说明结论匹配与条件关系：候选条件蕴含先例条件，或二者等价。

逐主张：明确等价/已有工作覆盖 → COVERED；否则有部分重叠 → PARTIAL_OVERLAP；否则有未知或三类检索不齐 → UNKNOWN；其余 → NO_COVERAGE_FOUND。

整体：同一来源覆盖所有核心主张 → COVERED；任一主张已覆盖或部分重叠 → PARTIAL_OVERLAP；其余有未知 → UNCLEAR；其余 → NO_COVERAGE_FOUND。多篇分别覆盖模块不自动合成整合方案已存在的结论，原文有组合主张时单列。

`prior_work.verdict` 另外报告方向是否非常相近，因此“方向已有先例”和“仍有未确认的贡献差异”可以同时成立。当前程序并没有形式化证明器；六维关系与原文拆解的内容正确性是这轮真实复查需要检查的部分。
