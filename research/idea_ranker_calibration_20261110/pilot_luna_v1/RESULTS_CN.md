# GPT-6 Luna 评价校准试验结果

完成于 2026-11-11。沿用此前原生 collaboration 的 GPT-6 Luna / low 调用方式，24 份独立上下文评价全部交付：机械、合成历史两个场景，各 6 个控制端编写版本，每条重复两次。没有调用 DeepSeek，也没有启动原科研运行。

## 当前结论

这套规则在本批简单对照上能区分具体关系、套壳和展示不足，且没有因为宏大愿景或显式“尚未验证”改变核心类别。它适合作为继续开发初筛的依据。尚未检验多个有实质内容的研究项目如何排序，也没有证明能判断长期研究价值。

## 观察到的表现

- 四项类别 novelty、contribution、display、priority 的重复一致为 **47/48**。唯一差异是同一条空泛历史候选的 contribution 被评为 limited 与 unclear；其余分类、两次项目优先类别一致。一致只说明重复稳定，不代表判断正确。
- 两个场景、两次重复中，等义改写和“未验证”声明均保持核心类别；追加宏大愿景也没有增加核心类别，并被指出外推缺依据。
- 4/4 套壳评价认定为 same_claim、low_increment。
- 4/4 空泛评价认定展示不足并要求 clarify；没有直接选为 develop。
- 24/24 原文引用确实出自各自候选；24/24 输出符合约定字段及枚举。每个评审只收到一条候选，无可观察的工具调用。
- 历史候选的具体机制被保留为有内容的待检验项目，没有因为缺少实验而被拒绝。

## 两轮逐项分类

左/右分别为第 1/2 次评价。new_relation 仅表示相对固定参照的关系增量，不是现实文献新颖性。

| 候选版本 | 包内增量 | 一步贡献 | 项目优先类别 |
|---|---|---|---|
| H1 具体关系 | new_relation / new_relation | specific / specific | develop / develop |
| H2 等义改写 | new_relation / new_relation | specific / specific | develop / develop |
| H3 追加愿景 | new_relation / new_relation | specific / specific | develop / develop |
| H4 套壳改名 | same_claim / same_claim | limited / limited | low_increment / low_increment |
| H5 展示不足 | unclear / unclear | limited / unclear | clarify / clarify |
| H6 声明未验证 | new_relation / new_relation | specific / specific | develop / develop |
| M1 具体关系 | new_relation / new_relation | specific / specific | develop / develop |
| M2 等义改写 | new_relation / new_relation | specific / specific | develop / develop |
| M3 追加愿景 | new_relation / new_relation | specific / specific | develop / develop |
| M4 套壳改名 | same_claim / same_claim | limited / limited | low_increment / low_increment |
| M5 展示不足 | unclear / unclear | limited / limited | clarify / clarify |
| M6 声明未验证 | new_relation / new_relation | specific / specific | develop / develop |

## 仍需处理的具体问题

### 1. “感性推一步”会滑向替空泛候选构造内容

四份空泛候选评价都在 one_step 中补出了原文没有的关系。机械候选只有“综合考虑摆角和耦合”，P32886 却写出将阈值位移除以摆角的分析；历史候选只有“重新理解复杂关系”，P79678 写出编辑筛选与署名增长并存的机制。这些均被标为 evaluator，且没有进入 core，但四份中仍有三份给了 limited 贡献。

因此问题不是已经证明跨候选串入，而是允许评价器推断的规则过宽。独立会话下，仅靠同一场景也足以补出一个更具体的候选。

建议：先恢复候选实际承诺的关系；如果缺少这条关系，一步贡献写“当前无法判断”。补充建议单列成新 idea，不纳入当前贡献。仅标 evaluator 不足以保证后续分数不被污染。

### 2. 附加条件、验证需求和无依据断言混在一起

部分 extra_premises 把核心假说本身当作额外前提，或把“取得原稿与刊稿”这类研究条件写进逻辑后果的前提。部分 unsupported 只是说核心假说尚未验证，例如 P39206；P51831 又把原候选未主张的“指数能说明单位角度影响不对称”列入 unsupported。

当前项目类别没有因此降低，但若以后把这些数组长度用于扣分，会误罚早期假说或候选没说过的话。

建议：分别记录核心暂定主张、推一步需要的新独立假说、执行条件，以及作者原文中无依据的确定断言；禁止按条目数量扣分。只有能够定位到原文主张的问题，才作为候选缺陷。

### 3. 来源标注还有边界不稳

等义机械版本 M2 的两次 one_step 来源分别标为 evaluator 与 candidate。来源标签需要按具体推理关系核对，不能仅依赖模型自述。

### 4. 这组材料没有覆盖“两个都值得做时怎么选”

每个领域只使用一个核心关系及其变体。16 份有明确关系的评价全部为 develop；这个结果符合本组对照设计，但不能说明已经具备细粒度项目排序能力。

下一项研究价值排序测试应使用同一真实问题下多个不同的实质候选，提供真实的最接近文献和领域问题背景，比较直接贡献及依赖条件。合成历史解释通过，也不能替代文学阐释、规范论证等其他文社科类型。

## 保存与审计

- 原始最终回复：`calls/<匿名编号>/raw.txt`；解析副本为同目录 `result.json`，未改判断、理由或引文。
- 每份 receipt 记录模型、low effort、原生子会话标识、最终消息来源及原文哈希。源子会话日志中的模型为 gpt-6-luna；这不是对后台权重的独立证明。
- 评审只收到冻结规则与单条匿名候选，未提供控制标签和预期结果。原生消息正文在日志中加密，不能独立重读实际明文；保留了准备输入、提交方式及会话关联，不声称已完成收发明文逐字校验。
- 初次任务名含大写导致一次创建失败，未启动模型；改为小写后执行。其后 24 次均首次交付有效 JSON，无重试、续问、内容修正或工具调用。
- 冻结材料哈希全部保持不变。统计和控制端语义检查分别记录在 SUMMARY.json；语义检查不是第三方独立评分。
- 实际 token 账户记录见 SUMMARY.json 的 recorded_usage，包含原生系统提示开销，非仅候选正文；不据公开单价估算该原生通道实际账单。

完整原始判断合并于 ALL_RESULTS.json。规则、对照文本和预先核查项仍在上级 PILOT_DRAFT_CN.md 与本目录 FROZEN_INPUTS.json 中。
