# 持续学习与假说讨论接口

2026-11-06。当前通用协议为 `learning-inquiry-v2`。研究角色默认请求 GPT-6 Luna / low。

## 入口与职责

| 入口 | 用途 | 计算范围 |
| --- | --- | --- |
| `src/learning_lab.py` | 通用场景的独立学科研究者、补学、讨论、内部复核、记忆续接、最终检查 | 显式数值教学算例；其他操作返回能力缺口 |
| `wine_flow_fixes_20261106/run_wine_v2.py` | 葡萄酒场景，沿用旧试跑的两位学科身份与复制后的完整记忆 | 同通用入口 |
| `historical_inquiry/fish_inquiry.py` | 鱼类轨迹适配器，含任务日期与来源排除、原始轨迹分析 | 数组变量、条件比较、分段、滞后及线性拟合 |
| `src/import_learning_handoff.py` | 导入已明确调度的原生角色结果 | 验证输入哈希和结果结构，记录执行适配器 |

这些入口共享问题版本、假说分支和显式请求合并协议。通用入口没有通用 CSV 建模执行器。

## 启动、返回状态与恢复

从 `1103_boundary_discovery/` 执行；先创建 Python 环境并安装 `requirements.lock.txt` 中的依赖。

```bash
python src/learning_lab.py --case wine --executor queue --run-prefix inquiry_20261106

# 使用此次葡萄酒实测的完整记忆快照：
python wine_flow_fixes_20261106/run_wine_v2.py \
  --executor queue --run-id wine_inquiry_v2_001
```

`cli` 调用本地 Codex CLI。失败时保留执行记录并准备原生交接；`queue` 直接生成交接请求。两者都需要可用的模型执行后端。

| 返回 | 含义 | 下一步 |
| --- | --- | --- |
| 退出码 `0`、`learning_state.json.status=complete` | 候选生成与最终检查流程完成 | 阅读 `ideas.json`、`check_report.json` 和过程记录 |
| 退出码 `75`、`PENDING_NATIVE.json` | 等待一个真实原生角色执行 | 按请求的 model、effort、prompt、inputs、workspace 执行；导入后重复原启动命令 |
| `pending_controller` | 某个计算无法表达或执行 | 阅读具体原因，修订请求或补充执行能力；研究方向仍可保留 |
| `knowledge_status=unresolved` | 有界检索后未取得可读内容 | 依据实际缺口继续提问，不记为已学会 |
| 输入／输出／源码哈希错误 | 恢复所需的冻结条件发生变化 | 保留旧运行，修复问题或使用新 run-id |

原生执行者只读取 `PENDING_NATIVE.json.inputs`、相关来源和提供的记忆，把 `result.json` 写到其 `workspace`。完成真实执行后导入：

```bash
python src/import_learning_handoff.py \
  --run runs/wine_inquiry_v2_001 --agent actual-executor-id
```

导入只登记实际交付物，不代表 CLI 调用。不得用控制器代写科学回答冒充真实角色输出。

`admitted` 表示交付物已登记；重新运行入口还会核对科学阶段协议。若失败，保留原始
`result.json` 和登记记录，将具体校验错误交回原角色修正，再导入。已写入问题、假说事件或
记忆的结果不能直接改写。本次实测的未接纳交付恢复工具是
`wine_flow_fixes_20261106/reject_native_delivery.py`，仅用于其固定的 `wine_inquiry_v2_002`。

## 每个角色的结果结构

```json
{
  "summary": "非空字符串",
  "artifacts": ["NOTE.md"],
  "evidence": [],
  "claims": [],
  "limitations": [],
  "next_actions": [],
  "memory_notes": [],
  "memory_use": []
}
```

前六项为运行时约定；原生导入要求 artifacts 至少指向一个实际存在的产物。其余科学字段由各阶段请求决定。公开来源、解释、推断和未检验假说应明确区分。

## 个人问题和假说分支

第一次独立初读返回 `initial_question`。后续问题更新使用控制器提供的 `question_state`：

```json
{
  "personal_question_update": {
    "base": {"id":"personal:researcher_id","owner":"researcher_id","version":1},
    "action":"retain",
    "question":"与本次输入 self.question 完全一致",
    "reason":"保留当前问题的具体理由",
    "influenced_by":[]
  },
  "shared_question_update":null
}
```

`revise` 可以更改自己的问题，包括采纳同伴方向，并引用输入中的实际 ref。共享问题独立版本化；更改共享问题不会覆盖个人问题。`question_before/question_after` 不再作为有效更新字段。

可选假说更新：

```json
{
  "hypothesis_updates": [{
    "key":"local_branch_key",
    "base_version":0,
    "assumption":"一个明确标为暂定的关系、解释、表示或构造原则",
    "motivation":"引出设想的具体现象或困难",
    "conceptual_move":null,
    "implications":[],
    "open_questions":[],
    "status":"developing",
    "reason":"为什么提出或发展这条分支",
    "influenced_by":[]
  }]
}
```

已有分支使用输入中的版本；新 key 可保留替代方向。状态可为 `developing/parked`。空更新不删除旧分支。早期假说允许概念动作或后果尚未明确，不要求证明、实现或实验可行性。引用和所有权由控制器核验。

`hypothesis_state` 是控制器输入，研究者输出使用顶层 `hypothesis_updates`。
问题的 `influenced_by` 只能引用问题 refs；假说的 `influenced_by` 只能引用假说 refs。
两类引用不能混用。个人问题的 `base` 从 `question_state.self.ref` 原样复制，不能用 null
代替已经存在的问题，也不能根据同伴输出重建自己的历史。

## 补学与计算

```json
{
  "learning_request": {
    "needed":true,
    "gap":"一个具体知识缺口",
    "why_now":"它会怎样帮助当前理解或假说",
    "queries":["研究者自己提出的查询"],
    "urls":[],
    "source_ids":[],
    "record_ids":[],
    "operations":[]
  }
}
```

旧 `search_terms` 在通用服务中映射为 queries。显式计算可写在 operations，或顶层 `analysis_plan`（单对象／对象数组）。完全相同的方案在一次回答内只执行一次。`needed:false` 不取消显式计算，也不会因此激活未申请的文献检索。

通用算例：

```json
{
  "analysis_plan": {
    "kind":"calculation",
    "question":"核对一个教学例子的数值关系",
    "bindings":{"x":[2,4,6]},
    "expression":"mean(x)",
    "expected":4
  }
}
```

结果包含 `actual`、`matches_expected` 与范围说明；无法执行时返回 `pending_controller` 和具体原因。实际读取材料后，研究者按 source_id 返回 `source_use`，区分 `direct/method/irrelevant/not_read`，并解释理由。检索返回数量不代表学会的知识数量。

补学回复的 `source_use` 需与该次 `services/replies/*.json` 的 `sources` ID 完全对应，
每个 ID 一次。已有共同材料另行讨论；不加入该数组。回复 `sources:[]` 时返回
`source_use:[]`，不能给失败日志自行创造来源 ID。

## 长期记忆与内部核查

`memory_notes` 沿用稳定 key、kind、mastery、understanding、conditions、example、open_questions、tags、sources 等字段。同键修订要求 revision_reason；旧版本和来源结果哈希保留。详见 `src/learning_memory.py`、`src/learning_lab.py:NOTE_SCHEMA`。

内部 reviewer 对当前输出给出带准确引文、source_stage、受影响 note_keys 的具体发现；算例可以附可复算表达式。研究者返回 verification_responses，逐项 `accept/rebut/unresolved`。受影响的本人笔记另存同键 correction/dispute 版本并引用核查报告。未被证明的假说不属于算术或逻辑错误。

## 输出与评价边界

| 路径 | 内容 |
| --- | --- |
| `learning_state.json` | 协议、源码／配置哈希与已接纳阶段 |
| `source_catalog.json`、`MATERIAL_COVERAGE.json` | 实际材料及仍未补齐的领域背景 |
| `memory_retrieval/`、`researcher_context/` | 每次调用实际收到的记忆、问题和假说 |
| `question_state/`、`hypothesis_state/` | 所有者、版本和来源事件 |
| `services/` | 研究者请求、检索尝试、来源文本与算例结果 |
| `internal_review/` | 生成期核查输入及结果 |
| `candidate_history.json`、`ideas.json` | 实际发展轨迹、全部保存分支与最终候选 |
| `GENERATION_FREEZE.json` | 最终评价前冻结的生成文件与记忆哈希 |
| `check_report.json`、`EVALUATION_ISOLATION.json` | 最后两项检查及隔离核对 |

最终 checker 只做已有工作比较和明显数学／逻辑错误检查；它不回写新研究记忆，也不触发后续生成。程序测试通过、检索无近似结果和真实 idea 质量提升是三种不同的结论。

历史记录可能包含机器相关的绝对路径。下载仓库不等于能够原路径恢复所有旧运行；新运行应使用新 run-id，并保留旧版本和来源文件。
