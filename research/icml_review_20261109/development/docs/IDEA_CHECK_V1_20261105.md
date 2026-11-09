# Idea 构建与最终检查

当前任务是提出研究 idea。流程为 **idea builder → check agent**；讨论学习入口也复用同一个 checker。检查包含已有工作比较与明显数学／逻辑错误粗筛两项职责。idea 可以保留尚未解决的问题；证明、实现、数据、实验结果均不是保留候选的条件。

## 贡献覆盖检查：claim-centric-v1（2026-11-05）

已有工作检查返回两层结论：

- `prior_work.verdict`：研究方向是否非常相近。`already_done` 表示方向已有先例，不代表所有具体贡献均已被覆盖。
- `novelty`：哪些原始核心主张被哪些来源覆盖，依据是什么，哪些差异仍待核验。

例如：先例已经研究模型结构发现，但尚未确认是否覆盖候选提出的更弱识别条件。可以同时记录 `already_done` 和 `PARTIAL_OVERLAP`。同主题、同数据或共享通用技术本身不足以判定非常相近。

### 同一 checker 内的三个步骤

1. **忠实拆解。** 从原始 idea 提取 1–5 条核心研究主张／问题，每条绑定原文 `idea_quote`。已有明确主张才拆解；缺少机制、假设或验证设计时记 `not specified`，不替作者补出更强方案。若原始主张声称整合产生新机制／能力，单列 `combination` 主张。提出问题、研究未知关系也是合法主张；不要求先有结论。
2. **多角度检索。** 从 problem、mechanism、contribution 分别生成短关键词和同义查询。初始计划每个 idea 4–6 个查询，候选池目标 30–50 篇去重记录，读 8–10 篇摘要，深入比较最相关的 3–5 篇。按可能覆盖主张的程度筛选，保留各检索角度的近邻与筛选理由。实际引擎、候选、失败和下载内容写进本地检索台账；有语义检索工具时才记录为语义检索。允许一轮针对未决主张的补检，最多两个查询。
3. **证据比较。** 对入选的每个来源分别作六维比较和逐主张比较。保存来源文本、证据位置、逐字引文和解释；复杂细节按实际读到的方法、定理或实验段落判断。

数量是工程预算，受每个角色的时间限制约束。保存实际完成量；不凑数，也不以达到数量证明检索完整。明确先例覆盖全部核心贡献时可以提前结束。遇到访问／时间限制，保存未决问题和停止原因。否定式结论需有三个检索角度均已完成的记录；检索不足返回 `unclear`。

V1 的三个步骤由提示词组织在一次 checker 会话内，候选池、筛选与下载由该角色执行。当前没有新增固定的检索后端或 embedding 检索器。

### 六维解释与有向覆盖

| 维度 | 比较对象 |
| --- | --- |
| problem | 科学问题／目标 |
| mechanism | 方法、因果机制、工作原理 |
| contribution | 提议的新结果、理论、能力或研究问题 |
| assumptions | 条件、对象、范围、量词与可识别性 |
| validation | 验证设计或证据贡献；尚未设计可记未知 |
| application | 场景、数据、领域 |

六维不加权求和。假设放宽或验证方法本身可以是核心贡献，重要性由原始主张决定。

六维与逐主张比较均使用同一组关系标签：`EQUIVALENT`、`PRIOR_COVERS_IDEA`、`PARTIAL_OVERLAP`、`RELATED_ONLY`、`DISTINCT`、`UNKNOWN`。`DISTINCT` 需要实质差异的证据；摘要未提到某细节只能支持未知，不能直接支持差异。关系标签与证据层级分别记录，不使用混合标签 `POTENTIALLY_COVERED`。

对于理论 `C_I ⇒ R` 与 `C_P ⇒ R`，若结论和研究对象确实匹配且 `C_I ⇒ C_P`，已有结果可覆盖候选特例。比较时明确对象对应、结论、量词和条件；难以判断蕴含时记 `unknown`，不要求证明器。现有推导或经验结果也不自动覆盖一个更强的理论保证。

各模块分别已有先例，不自动建立整合方案已有先例；有组合主张时按完整机制／能力比较。原文只把熟悉模块并列，也不自动构成新的组合贡献。

### 证据层级

`evidence_level` 为 `full_text`、`abstract`、`metadata_only` 或 `unavailable`。摘要的明确陈述可支持其范围内的覆盖；定理条件、实验设置等细节需要相应段落。全文可访问不意味着每个主张都有证据。

保存原始下载响应与用于引用的 UTF-8 文本（PDF/XML/倒排摘要等需另存提取文本），来源中记录实际 URL 和阅读日期。每条证据绑定 `source_id`、`quote`、`locator`；`snapshot_path` 使用绝对路径，引用必须逐字出现在保存文本中。`locator` 可为摘要、节名、页码或定理号。元数据或访问失败不足以建立实质覆盖。

程序能核对引文存在、ID 对应、结果聚合和字段完整性；来源真实性、摘录是否忠实于下载原文、引文能否支撑解释仍依赖实际检索与模型判断。

## JSON 输出契约

顶层包含 `schema_version: "claim-centric-v1"`、`searches`、`checks`，以及 runtime 的六个标准字段 `summary, artifacts, evidence, claims, limitations, next_actions`。顶层 `claims` 是运行器通用记录，各 idea 的原子主张放在 `checks[].novelty.claims`。

`searches` 每条包含：

```text
query, url, status: completed/failed, idea_ids: [原始ID],
facet: problem/mechanism/contribution, round: 1/2,
snapshot_path: 已完成查询保存响应的绝对路径,
failure_reason: 失败原因（仅 failed 必需）
```

每条 `checks` 包含 `idea_id`、`prior_work`、`math`、`novelty`：

```text
prior_work:
  verdict: already_done/no_close_work_found/unclear
  reason: 中文理由
  sources: [
    {source_id, title, url, accessed_on, content_note,
     similarity: very_similar/related_only,
     evidence_level: full_text/abstract/metadata_only/unavailable,
     snapshot_path: 绝对路径；unavailable 时为 null}
  ]
math:
  verdict: no_obvious_error/obvious_error/unclear
  reason: 中文理由
  errors: [{claim: 错误原句或公式, explanation: 原因}]
novelty:
  idea_card:
    {problem, mechanism, contribution, assumptions, validation, application}
  claims: [
    {claim_id, text, idea_quote,
     kind: method/theory/scientific_finding/question/combination/other,
     coverage: COVERED/PARTIAL_OVERLAP/UNKNOWN/NO_COVERAGE_FOUND}
  ]
  evidence: [{evidence_id, source_id, quote, locator}]
  comparisons: [
    {source_id,
     facets: {
       problem: {relation, reason, evidence_ids},
       mechanism: {relation, reason, evidence_ids},
       contribution: {relation, reason, evidence_ids},
       assumptions: {relation, reason, evidence_ids},
       validation: {relation, reason, evidence_ids},
       application: {relation, reason, evidence_ids}
     },
     claim_relations: [
       {claim_id, relation, reason, evidence_ids,
        conditions: {
          relation: idea_implies_prior/prior_implies_idea/equivalent/
                    incomparable/unknown/not_applicable,
          reason: 条件映射与判断依据
        }}
     ]}
  ]
  overall_status: COVERED/PARTIAL_OVERLAP/UNCLEAR/NO_COVERAGE_FOUND
  combination_assessment:
    {status: assessed_as_claims/not_claimed,
     claim_ids: 所有 combination 主张ID的排序数组,
     reason: 组合贡献的判断}
  remaining_difference: [{claim_id, description}]
  recommended_action: INSPECT_PRIOR/TARGETED_SEARCH/CONTINUE_EXPLORATION/REFINE_PROPOSAL
  next_step: 建议与科学理由
  search_exhaustive: false
  search_summary:
    {stop_reason: budget_reached/sufficient_coverage/access_limited/planned_searches_complete,
     limitations: 实际完成情况、台账路径及未覆盖范围}
```

所有 `sources` 均有六维与全部核心主张的比较。缺内容的字段用 `UNKNOWN` 和理由保留。确定的关系标签需绑定同一来源的引文证据；`UNKNOWN` 可无证据。理论覆盖的条件关系必须是 `idea_implies_prior` 或 `equivalent`。

逐主张聚合顺序：有明确 `EQUIVALENT/PRIOR_COVERS_IDEA` → `COVERED`；否则有部分重叠 → `PARTIAL_OVERLAP`；否则存在未知或三类检索未齐 → `UNKNOWN`；其余 → `NO_COVERAGE_FOUND`。

整体聚合：同一来源覆盖全部核心主张 → `COVERED`；有任何已覆盖／部分重叠主张 → `PARTIAL_OVERLAP`（包括多篇分别覆盖各模块）；其余存在未知 → `UNCLEAR`；其余 → `NO_COVERAGE_FOUND`。`COVERED` 必须同时标记已有方向 `already_done`。该整体规则保守地将分散先例交给组合分析，不以单篇检索失败宣告组合创新。

没有 `NOVEL` 标签。`remaining_difference` 只列尚未被确认覆盖的原始核心主张；“本次未找到”与“证据不足”由其 `coverage` 区分。未知应引导补检。修改建议须保留原始科学目标，并说明差异为何有意义。V1 返回建议，主流程不自动改写或启动 refinement 循环；原始候选和历史分支全部保留。

## 数学／逻辑粗筛

检查明显的算术、代数、量纲、概率或逻辑矛盾；指出原句／公式与原因。没有公式的概念性方向也可以通过。未证明的猜想、未知的效果、未取得的数据、实现成本或暂时不能验证均不构成错误。两项判断各自保存。

## 使用与兼容

在项目目录运行，输入和新运行目录都放在项目内。已有 Codex 登录，默认请求 GPT-6 Luna，每个角色默认最多 600 秒。

```bash
.venv/bin/python src/idea_check.py --brief docs/NEW_DISCOVERY_BRIEF.md --run-dir runs/ideas_002 --count 3
.venv/bin/python src/idea_check.py --idea runs/ideas_001/ideas.json --run-dir runs/check_003
```

输入 JSON 仍只必需 `id`、`title`、`idea` 三个非空字符串。Markdown 作为一个完整 idea 输入。无需作者先填写贡献表。

结果位于 `ideas.json` 和 `check_report.json`，完整角色输出、检索台账、来源快照和中文 `CHECK.md` 在 `stages/`。新调用必须通过 claim-centric 契约；旧报告继续用旧契约读取，不回写、不重新解释历史结论。调用失败保留原始记录，可用运行器 `--config` 恢复 dispatch，或在新目录重新检查已保存候选。

`src/idea_check.py`、`src/cross_domain_ideas.py`、`src/learning_lab.py` 的新 checker 调用均接入本契约。检索数量、语义召回和内容判定由角色执行；软件校验不构成文献评测效果的验证。
