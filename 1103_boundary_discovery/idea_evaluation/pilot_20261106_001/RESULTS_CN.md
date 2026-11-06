# 三维评分试评结果

状态：two_outputs_validated。

分数顺序为：研究价值 / 概念内容 / 研究生成力。没有加权总分。

| 材料 | 会话1 | 会话2 |
|---|---|---|
| 原候选：距离转移 | 2 / 2 / 2 | 2 / 2 / 2 |
| 原候选：历史预测 | 2 / 2 / 2 | 1 / 2 / 2 |
| 原候选：方向相似度 | 1 / 2 / 2 | 1 / 2 / 1 |
| 分析请求 | 1 / 0 / 1 | 1 / 0 / 1 |
| 方向性猜测 | 1 / 1 / 1 | 1 / 1 / 1 |
| 阶段解释假说 | 2 / 3 / 3 | 2 / 2 / 2 |
| 同一假说：润色扩写 | 2 / 3 / 3 | 2 / 2 / 2 |
| 同一假说：明确未完成 | 2 / 3 / 3 | 2 / 2 / 2 |
| 同一假说：问句表达 | 2 / 3 / 3 | 2 / 2 / 2 |
| 移除阶段解释 | 1 / 1 / 1 | 1 / 1 / 1 |
| 宏大愿景 | 0 / 0 / 0 | 0 / 0 / 0 |

## 预先固定的检查

- {"repeat": "r1", "kind": "invariance", "reference": "structural_hypothesis", "comparison": "polished_equivalent", "comparison_minus_reference": {"value": 0, "concept": 0, "generativity": 0}, "passes_predeclared_rule": true}
- {"repeat": "r1", "kind": "invariance", "reference": "structural_hypothesis", "comparison": "question_equivalent", "comparison_minus_reference": {"value": 0, "concept": 0, "generativity": 0}, "passes_predeclared_rule": true}
- {"repeat": "r1", "kind": "content", "reference": "structural_hypothesis", "comparison": "analysis_request", "comparison_minus_reference": {"value": -1, "concept": -3, "generativity": -2}, "passes_predeclared_rule": true}
- {"repeat": "r1", "kind": "content", "reference": "structural_hypothesis", "comparison": "directional_guess", "comparison_minus_reference": {"value": -1, "concept": -2, "generativity": -2}, "passes_predeclared_rule": true}
- {"repeat": "r1", "kind": "content", "reference": "structural_hypothesis", "comparison": "mechanism_removed", "comparison_minus_reference": {"value": -1, "concept": -2, "generativity": -2}, "passes_predeclared_rule": true}
- {"repeat": "r1", "kind": "maturity", "reference": "structural_hypothesis", "comparison": "explicitly_unfinished", "comparison_minus_reference": {"value": 0, "concept": 0, "generativity": 0}, "passes_predeclared_rule": true}
- {"repeat": "r1", "kind": "wish", "score": 0, "passes_predeclared_rule": true}
- {"repeat": "r2", "kind": "invariance", "reference": "structural_hypothesis", "comparison": "polished_equivalent", "comparison_minus_reference": {"value": 0, "concept": 0, "generativity": 0}, "passes_predeclared_rule": true}
- {"repeat": "r2", "kind": "invariance", "reference": "structural_hypothesis", "comparison": "question_equivalent", "comparison_minus_reference": {"value": 0, "concept": 0, "generativity": 0}, "passes_predeclared_rule": true}
- {"repeat": "r2", "kind": "content", "reference": "structural_hypothesis", "comparison": "analysis_request", "comparison_minus_reference": {"value": -1, "concept": -2, "generativity": -1}, "passes_predeclared_rule": true}
- {"repeat": "r2", "kind": "content", "reference": "structural_hypothesis", "comparison": "directional_guess", "comparison_minus_reference": {"value": -1, "concept": -1, "generativity": -1}, "passes_predeclared_rule": true}
- {"repeat": "r2", "kind": "content", "reference": "structural_hypothesis", "comparison": "mechanism_removed", "comparison_minus_reference": {"value": -1, "concept": -1, "generativity": -1}, "passes_predeclared_rule": true}
- {"repeat": "r2", "kind": "maturity", "reference": "structural_hypothesis", "comparison": "explicitly_unfinished", "comparison_minus_reference": {"value": 0, "concept": 0, "generativity": 0}, "passes_predeclared_rule": true}
- {"repeat": "r2", "kind": "wish", "score": 0, "passes_predeclared_rule": true}

## 重复一致性

完全相同的逐维评分：23 / 33。

## 范围

同一模型、单一领域、小量受控样例。不是世界新颖性检查，不建立长期潜力真值或研究调度有效性。原始评语见RESULTS.json。

## 对结果的解释

本节是控制器对评语的检查，不是第三位独立模型的评分。没有修改任何评分。

两次会话均满足预先固定的7项诊断规则，共14项：加入阶段解释后概念内容与生成力高于分析请求、方向性猜测及删除阶段解释的版本；润色与问句改写分数不变；明确未完成不扣分；宏大愿景未获高价值分。共66处逐字引文均通过自身候选子串校验。

这些结果支持本量表对本批受控样例中“仅有分析任务”和“包含阶段解释”的区别有所反应。在同一批材料内，指定的三种表达改动没有改变评分。两次会话共33个对应分数，23个完全相同，10个相差1分。没有未知评分。

但有三个具体问题：

1. **2分与3分边界不稳定。** 阶段解释及其三个等义变体在会话1均为2/3/3，在会话2均为2/2/2。两次对内容的概括相近，数值边界却不同。不能把1分差直接理解成确定的价值差。
2. **分析步骤被当成研究生成力。** 会话1对方向相似度生成力给2分，理由是“零位移处理和阈值敏感性检查等具体后续分析要求”；会话2给1分，指出未提出描述量之外的研究后果。会话1对历史预测生成力给2分时，也把“不能证明互动或集体记忆”当作推论。这些是实现检查或解释边界，不自动等于该idea产生了新的科学问题或关系。概念内容上，常规数学定义或模型比较因其具体程度就可得2分，也说明当前标准容易混合表达清楚与概念推进；本轮没有查新，不能以此认定它们为新贡献。
3. **同批候选有内容串入。** 会话1在P564（mechanism_removed）的core_claim中写“交互阶段差异可能解释部分历史预测作用”，uncertainties中写“历史带来预测增益的阶段解释只在前文提出”，但该候选已删除全部阶段解释。会话2的P108则没有这项归因。引文虽然全部来自正确候选，core_claim仍然可能从其他候选吸收内容，故引文校验不足以验证评语忠实性。

下一轮可以先保持三维结构，补清2/3分锚点，要求“研究生成力”列出的后果确实来自核心思想，并把候选逐条放进独立会话。以上是本轮结束后提出的修订建议，未回写冻结量表或重新计算分数。

本轮不评价长期潜力，也没有测试高、低排名分支经过调研后谁更有价值。尚无资格用本量表自动淘汰候选。

## 执行与保护

初次外部启动被自动审批拒绝后，用户于2026-11-06明确授权本批11条材料、共同背景及量表发送给GPT-6 Luna并执行两次试评。授权后的CLI请求返回401 / INVALID_API_KEY，失败日志保留；未读取或改动认证文件。

控制器随后使用原生GPT-6 Luna / low会话。会话1首次空白交付，保留记录后同会话补交完整JSON；会话2一次交付完整JSON。最终有2份有效评分输出，不是两种模型或两位人类专家。原生评审只收到评分规则、共同背景及本会话随机编号的候选，没有继承父会话或收到预期分数与控制标签。未观察到评审调用工具。

原生输出的next_development为数组；控制器仅在标准化副本中将该字段合并为换行字符串，以适配原输出模式。原始输出另存，分数、引文、理由不变。原生传输与CLI不同，单独记录在native_receipt.json和NATIVE_HANDOFF.json。

冻结输入、原候选文件哈希及候选覆盖通过校验。没有将评价回写研究者记忆或旧实验。

