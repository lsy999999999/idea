# V2 研究输出约定

所有阶段保留 runtime 要求的 `summary`（字符串）、`artifacts`、`evidence`、`claims`、`limitations`、`next_actions`（五个数组）。下面的结构是额外字段。

## 独立解释 / 跨域检索

`proposals` 是数组。每项使用新的、全局唯一的 id：

```json
{
  "id": "A1",
  "statement": "具体解释及其适用范围",
  "representation": "它依赖哪些变量、状态或关系；与原描述的差别",
  "measurement": "怎样独立测量这些量，不能使用待预测结果构造输入",
  "predictions": ["一个能与其他解释区分的条件预测"],
  "alternatives": ["最强的已知替代解释"],
  "prior_work": [{"url": "实际查阅的来源", "relation": "已知部分与尚待检验部分"}],
  "status": "proposed"
}
```

修改已有解释须用新 id，并加 `parent_id`。它只记录修订来源，不代表新解释依赖旧解释成立。若一个解释逻辑上依赖其他解释，另外声明 `depends_on: ["已有解释ID"]`；只有这种依赖会传播失效或复核标记。不得覆盖旧解释；运行器根据证据管理状态。

## 计划者

除公共字段外，输出 `decision`（`experiment` / `finalize`）、`proposals`（可为空）、`plans`、`selected_plan_id`、`selection_reason`。

若选择实验，提出两个可行行动供比较，选定一个。每个计划遵循：

```json
{
  "id": "E01",
  "question": "本次要区分的具体问题",
  "hypothesis_ids": ["A1", "B1"],
  "intervention": "实际可以改变什么，其他哪些条件固定；具体实现与预算",
  "outcome_measure": "指标、对照、重复次数、不确定性、互斥分类阈值及不确定区间；在新实验之前确定",
  "predictions": [
    {"hypothesis_id": "A1", "expected_outcome": "A1 在干预下的预测", "outcome_id": "a"},
    {"hypothesis_id": "B1", "expected_outcome": "B1 在干预下的不同预测", "outcome_id": "b"}
  ],
  "outcome_classes": [
    {"id": "a", "description": "预先确定的可计算分类条件", "effects": {"A1": "supports", "B1": "contradicts"}},
    {"id": "b", "description": "另一互斥分类条件", "effects": {"A1": "contradicts", "B1": "supports"}},
    {"id": "uncertain", "description": "精度不足、两者皆可能或未覆盖情形", "effects": {"A1": "inconclusive", "B1": "inconclusive"}}
  ],
  "cost_minutes": 3,
  "feasibility": "已确认可用的数据、环境、工具；为什么能在预算内执行",
  "selection_reason": "相对另一个行动，哪些分歧更值得在这里检验",
  "replication": false
}
```

不同解释可以有不同参数或测量定义，但预测必须针对同一个可观测实验结果。不要人为夸大它们的差别，不能把尚未测得的阈值伪装成已有理论预测。若解释其实相容，先提出真正有区别的解释或修订观察方式。为拒绝一个关系过强的解释提供反例也有价值。

`finalize` 使用 `plans: []`、`selected_plan_id: null`。应说明是已完成阶段目标，还是当前资源无法区分。预算耗尽不代表发现成功。

## 实验者

先读冻结的计划，再执行。不能因结果不理想改变条件、阈值或效果映射。输出 `observation`：

```json
{
  "experiment_id": "E01",
  "execution_status": "completed",
  "observed_outcome_id": "a",
  "summary": "实际数字、分类依据与适用范围",
  "artifacts": ["保存的原始测量、逐次结果和可复现代码的路径"],
  "limitations": []
}
```

状态允许 `completed`、`partial`、`failed`。无法归入预先定义的类别时用 `unclassified`；不得强行选择最接近的类别。执行失败或不完整不能反驳科学假说。不要提交 `hypothesis_updates`。分类仍是需要检查的科学判断；程序只按预定映射更新账本。

## 复核与报告

复核角色读取各实验的冻结计划、实际代码与测量，检查分类是否成立，至少独立重算一个关键结论；检索最近邻工作，区分新关系、已知现象重现、局部工程变体。输出 `review_findings` 数组，每项为 `{experiment_id, classification_valid: true/false/null, reason, evidence_paths: []}`。不确定用 null。

最终报告必须覆盖账本中的每个解释及每个实验。`supported` 仅表示有结果被映射为支持，不等于机制成立或文献新颖。复核发现的问题保留并使相关结论转为需要复查；不能在报告中忽略。
