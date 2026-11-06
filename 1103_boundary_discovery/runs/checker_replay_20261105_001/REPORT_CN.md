# 新版 checker 历史复查结果（2026-11-05）

**5 个原始 idea 已完成复查；2 个方向判断改变，数学粗筛均未改变。新版模型对全部候选的具体贡献均只确认部分重叠，未确认完整覆盖。**

保持 5 个原始 idea 原文不变，请求 GPT-6 Luna / low。完成 5 次初始检查及 1 次针对网络失败的有界恢复。原候选与旧检查报告的 SHA-256 均与冻结计划一致，历史文件未改写。用户已明确授权这 5 个 idea 通过已登录 Codex 发送给模型并公开检索关键词，见 `AUTHORIZATION.json`。

## 新旧判断

“已有相近方向”与“全部具体贡献已被覆盖”是不同层次，不能互换。

| 原始 idea | 旧方向判断 | 新方向判断 | 新增贡献覆盖判断 |
| --- | --- | --- | --- |
| [生态—演化稀有历史与路径切换](cases/cross_domain_ideas_001_01/check_report.json) | 本次暂未找到 | 已有相近方向 | 部分重叠 |
| [免疫记忆的分布式配置](cases/cross_domain_ideas_001_02/check_report.json) | 本次暂未找到 | 证据不足 | 部分重叠 |
| [生态位构建与制度可实施性](cases/cross_domain_ideas_001_03/check_report.json) | 已有相近方向 | 已有相近方向 | 部分重叠 |
| [群落恢复的分层判读](cases/learn_20261104_community_01/check_report_recovery.json) | 已有相近方向 | 已有相近方向 | 部分重叠 |
| [免疫群体预测与微观来源识别](cases/learn_20261104_immune_01/check_report.json) | 已有相近方向 | 已有相近方向 | 部分重叠 |

模型拆出的 15 条核心主张中：8 条为 `PARTIAL_OVERLAP`，7 条为 `UNKNOWN`，0 条为 `COVERED`。未知包括来源未读到相应细节与检索受限，不能解释为剩余主张已获新颖性确认。五项数学粗筛均为 `no_obvious_error`。

## 每个结果具体变在哪里

### 1. 生态—演化稀有历史与路径切换

有一项直接研究生态—演化反馈并以环境扰动后平衡态之间的演化历程为对象，构成宽泛研究方向的非常接近先例；其摘要未显示稀有联合路径及主导历史切换贡献已被覆盖。

- **C1 · PARTIAL_OVERLAP**：确定种群—环境互惠反馈下哪些罕见联合生态—演化历史触发状态转移。
- **C2 · UNKNOWN**：把韧性解释重点从局部平均恢复率转向离开状态的历史组织，并研究主导转移路径切换如何改变宏观韧性。
- **C3 · UNKNOWN**：研究相同平均状态或相同生态结果是否可能由不同历史到达，并对应不同恢复能力或扰动脆弱性。
- **C4 · PARTIAL_OVERLAP**：组合路径空间中的稀有转移分析与生态—演化反馈，借由比较竞争的联合历史解释相近平均状态下的韧性差异。

所列近邻来源：

- [Environmental perturbations and transitions between ecological and evolutionary equilibria: an eco-evolutionary feedback framework](https://doi.org/10.1101/509067)
- [Cryptic eco-evolutionary feedback in the city](https://doi.org/10.1111/1365-2656.13657)
- [Ecological indicators reveal historical regime shifts in the Black Sea ecosystem](https://doi.org/10.7717/peerj.15649)

### 2. 免疫记忆的分布式配置

发现免疫记忆历史更新和组织驻留细胞局部网络等相关研究，但当前只审阅两篇摘要且多个检索服务不可用；证据不足以判定该跨域配置方向已有非常相近的完整先例，也不足以作无近邻结论。

- **C1 · PARTIAL_OVERLAP**：将免疫记忆建模为由异质细胞局部因果响应规则构成、在无全局控制者时形成组织级配置的分布式制度。
- **C2 · PARTIAL_OVERLAP**：研究局部信号、募集、迁移与存活规则如何由不完整威胁信息形成整体免疫响应。
- **C3 · PARTIAL_OVERLAP**：研究克隆特异性记忆、训练性广谱反应和组织驻留之间如何配置细胞、空间和响应资源，以应对复发威胁并限制局部持续损伤。

所列近邻来源：

- [How a well-adapting immune system remembers](https://doi.org/10.1073/pnas.1812810116)
- [A local macrophage chemokine network sustains protective tissue-resident memory CD4 T cells](https://doi.org/10.21417/b71591)

第二项实际为 immuneACCESS 数据集记录，其描述可以提供背景证据，但本轮没有核实对应期刊论文；不能将其描述当成已核实的期刊论文摘要。

### 3. 生态位构建与制度可实施性

已检索到直接研究 population games 中策略与环境状态反馈、空间多主体共同演化及稳定性的论文，故广义方向已有非常相近先例。摘要没有显示其处理机制设计中的激励相容／可实施性、局部生态信息和长期生态可行性目标；这部分组合贡献尚未被确认覆盖。

- **C1 · PARTIAL_OVERLAP**：将生态环境作为制度参与者行动所改变、并反过来改变未来收益与可行行动集合的内生状态，研究机制规则与环境的动态反馈。
- **C2 · UNKNOWN**：研究当行动者通过生态位构建改变共同环境时，何种规则能稳定地产生可持续资源配置，并重新表述内生环境下的激励相容与稳定性。
- **C3 · UNKNOWN**：将局部信息、可行偏离和跨期生态结果放入同一问题结构，以区分无人愿意偏离与群体长期维持良好生态条件，并考察短期稳定如何侵蚀长期生态可行性。

所列近邻来源：

- [Spatial coevolutionary dynamics in population games with environmental feedbacks](https://doi.org/10.1103/k326-3y4g)
- [Niche construction: the neglected process in evolution](https://doi.org/10.1101/2017.02.19.113035)

**人工核对：第二项辅助来源的题名/DOI 与保存的 API 原始记录不一致，不作为可靠证据使用。主要方向近邻 S1 另有记录。模型原输出保留，具体身份核对见 `BIBLIOGRAPHY_AUDIT.json`。**

### 4. 群落恢复的分层判读

重复扰动下群落组成轨迹与功能抗性/恢复可分离，已有非常相近的实证研究方向，故方向层面标记 already_done。此判定不表示分层框架或预测状态充分性主张均被覆盖。

首次复查 6 条 OpenAlex 查询均连接超时，因此返回 unclear。这是执行限制而非推翻旧结论。保留初次报告，追加两条 Crossref 查询、最多三项来源的有界补查后，方向判定恢复为 already_done。表中采用补查结果。

- **C1 · PARTIAL_OVERLAP**：提出重复盐度扰动下的一套分层判读关系，将明确参照和时间窗的观测投影、测序检出、距离与 PF 零模型所定义的 NST 推断、以及未来响应预测充分性分开处理，避免合并成单一整体恢复结论。
- **C2 · UNKNOWN**：当轨迹不一致时，询问差异属于哪一层，以及现有资料能否区分这些解释，而不把它们统一解释为群落记忆或整体恢复。

所列近邻来源：

- [Repeated disturbances affect functional but not compositional resistance and resilience in an aquatic bacterioplankton community](https://doi.org/10.1111/1758-2229.12656)
- [Disturbance and recovery of microbial community structure and function following Hurricane Frances](https://doi.org/10.1111/j.1462-2920.2006.01173.x)
- [NST: Normalized Stochasticity Ratio](https://cran.r-project.org/web/packages/NST/index.html)

### 5. 免疫群体预测与微观来源识别

已有研究在训练免疫后测量巨噬细胞面对特定二次功能挑战的响应，与候选的指定挑战下功能响应问题构成非常相近的研究方向；当前摘要没有覆盖群体预测关系的微观来源识别，因此该判定不表示全部主张已完成。

- **C1 · PARTIAL_OVERLAP**：在规定训练历史、取样流程、静置间隔和挑战下，群体观测能否预测预先指定的功能终点？
- **C2 · UNKNOWN**：若存在群体预测关系，哪些细胞身份/组成、细胞分辨响应、存活或互作信息能区分可能的微观来源？
- **C3 · UNKNOWN**：将指定群体功能预测与预测来源的微观识别作为相关的两层问题加以整合。

所列近邻来源：

- [Trained innate immunity attenuates macrophage efferocytosis of cancer cells](https://doi.org/10.7554/elife.105206.1)
- [Peritoneal macrophage heterogeneity is associated with different peritoneal dialysis outcomes](https://doi.org/10.1016/j.kint.2016.10.030)
- [Trained immunity and macrophage reprogramming in allergic disorders](https://doi.org/10.1038/s41423-023-01005-0)

## 六维现在如何处理

六维是同一 checker 中的解释框架，不是六个角色或加权评分。处理顺序是：原始 idea 的六项描述 → 每篇来源的六项比较 → 对原始核心主张逐项判断覆盖 → 程序按主张关系汇总。数学／逻辑另判。

每个来源、每个维度保存 `relation + reason + evidence_ids`，关系为 `EQUIVALENT / PRIOR_COVERS_IDEA / PARTIAL_OVERLAP / RELATED_ONLY / DISTINCT / UNKNOWN`。确定关系需引用对应来源的原文；信息不足保留未知。

以下直接取自第三个 idea 对 *Spatial coevolutionary dynamics in population games with environmental feedbacks* 的输出：

| 维度 | 实际标签 | 解释 |
| --- | --- | --- |
| Problem | PARTIAL_OVERLAP | 都研究策略／行动—环境反馈，但候选进一步询问可持续配置和机制规则 |
| Mechanism | PARTIAL_OVERLAP | 先例有策略与环境共演，摘要不足以判断机制参与者未来可行集合 |
| Contribution | PARTIAL_OVERLAP | 先例有反馈模型与稳定性分析，激励相容／可实施性重述尚未确认 |
| Assumptions | UNKNOWN | 参与者信息、偏好、量词和生态可行性定义不足 |
| Validation | UNKNOWN | 先例有蒙特卡洛和均场分析，候选验证方案尚未指定 |
| Application | PARTIAL_OVERLAP | 都涉及人—自然系统／共同资源，具体场景未充分对应 |

因此它可同时得到“方向已有相近工作”和“具体贡献仅部分重叠”。候选没写验证方案时，对应维度未知，不构成淘汰理由。六维本身不投票；整体覆盖仍根据原始核心主张汇总。理论主张的覆盖还要说明结论对应与候选条件蕴含先例条件，程序仅核对该关系记录，不作形式化证明。

详细接口解释见 `SIX_DIMENSIONS.md` 和项目 `docs/IDEA_CHECK.md`。

## 本轮暴露的质量问题

1. **来源身份可被配错，结构校验仍通过。** I-03 的 S2 写为 *Niche construction: the neglected process in evolution*、DOI `10.1101/2017.02.19.113035`；保存的原始响应第一条实际为 *Niche construction in evolutionary theory: the construction of an academic niche?*、DOI `10.1101/109793`。其真实摘要片段被配到了错误身份，原文存在检查无法阻止这一错误。
2. **搜索记录不足以还原全部查询。** I-01 的 7 条“成功查询”均指向同一个事后检索台账，不是独立原始响应文件。执行日志能证明发生过多次实际请求，但结果 JSON 不是完整的检索调用台账。检索命令数包含直接文献请求，不能与报告中的搜索条数机械等同。
3. **检索失败会改变方向标签。** 群落恢复首次的 unclear 来自连接失败；补查才恢复方向已有先例。因此统计新旧变化时必须标出执行限制。
4. **两例读取历史记忆。** I-03 读取共享笔记并搜索 MEMORY.md；免疫群体预测案例也搜索了 MEMORY.md。旧报告未作为显式输入，但本轮不能视为隔离历史结论的盲审。记录见 `ARTIFACT_AUDIT.json`。
5. **大部分内容比较仍停留在摘要或元数据。** 13 项选入来源标记为 10 项 abstract、1 项 full_text、2 项 metadata_only；full_text 项为 NST 工具文档。不能将这些层级解释为已深读 13 篇论文。候选池与阅读量也没有普遍达到建议预算。

## 对当前 checker 的判断

新版能够把方向相近、部分贡献和未知内容分别呈现，改善了报告的可解释性。本轮没有人工标注的真值，也同时改变了提示词、检索结果及部分模型设置，因此不能据标签变化断言判断准确率提高。

当前适合作为研究讨论的辅助报告，自动否决仍缺少可靠的来源身份和检索执行记录。优先补上两项：由程序从原始检索响应固定 `source_id ↔ DOI/URL ↔ title ↔ 原文`；由程序记录查询、HTTP/API 状态和原始响应，模型在这些固定记录上比较。随后再检查六维语义判断和主张抽取是否忠实于原意。

## 文件与验证

- `PLAN.json`：预先固定的范围、输入哈希与预算；`CONTROLLER_QUESTIONS.json` 为结果前保存的人工检查问题，未给 checker 作为输入。
- `COMPARISON.json`：新旧结论、核心主张、来源与执行记录。
- `ARTIFACT_AUDIT.json`：输出契约、检索快照类型与显式历史读取记录。
- `BIBLIOGRAPHY_AUDIT.json`：来源身份与类型的人工核对。
- `cases/*/check_report.json`：五次初查，群落恢复另有 `check_report_recovery.json`；各阶段下保留模型原始输出、事件、命令和来源文件。

五个最终选用报告均通过当前 claim-centric-v1 契约；原始候选及旧报告哈希一致。契约通过与内容正确分别报告。第一次沙箱初始化失败和随后自动审批拒绝也保留；用户明确授权后完成上述模型检查。
