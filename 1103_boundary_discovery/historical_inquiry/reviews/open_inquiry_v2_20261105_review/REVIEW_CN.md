# fish_inquiry.py 实现审查

2026-11-05。审查范围：新入口、批准的统一修正记录、来源与记忆筛选、分析执行器、最终评价及现有测试。被审查实现的六个已登记源码／配置哈希全部与 `implementation_checks_20261105/VALIDATION_SUMMARY.json` 相同。

现有历史入口测试 47 项和学习／交接测试 11 项均复跑通过。另用最小实例复现以下 5 个问题；复现不调用模型或网络，不改动运行代码、既有记忆或冻结实验。测试结果不足以说明这些路径已经正确。

## 1. P1：核查笔记漏掉上游依赖，历史日期筛选可被绕过

位置：`fish_inquiry.py:421-425`，配合 `internal_verification.py:170-178`、`inquiry_services.py:156-165`。

`record_note_dependencies` 将核查报告的来源展开为 `affected_claims` 的直接 `basis.source_ids`。但是 `affected_claims` 是被查主张及其下游受影响主张，不含它所依赖的上游前提；也没有展开报告实际使用的 `evidence_refs`。因此引用报告的纠正笔记可以丢掉真正的文献依赖。

复现：一条研究决策通过 `depends_on` 依赖 2007 年文献，核查报告支持这条决策；其纠正笔记最终只记录 `measurements.json` 为依赖。把取回策略改成 2000 年之前，该笔记仍被接纳。这使笔记的历史资格与其知识来源不一致。

建议：从核查目标、其 `depends_on` 的祖先闭包及报告 `evidence_refs` 展开实际来源；跨报告、跨运行继承已有依赖证明。日期筛选应检查完整闭包。

## 2. P1：旧纠正笔记能被读取，却在再次写入时中断运行

位置：`fish_inquiry.py:426-435`，提交顺序在 `fish_inquiry.py:333-340`。

`validate` 会允许取回的旧笔记引用旧运行的核查报告；`record_note_dependencies` 只识别本次 `self.evidence.reports()` 中的报告。引用旧报告会落入 `Unverified memory dependency`。此检查发生在 `Memory.commit` 之后，因此留下“笔记已经提交、阶段尚未完成”的部分状态。

复现使用当前真正存在且经 `NoteGate` 接纳的 `coordinates_do_not_identify_behavior` 纠正笔记，保留其原来的两个报告引用。在初读阶段重新保存该笔记时出现上述异常；索引已有新笔记，但 `state.stages` 没有该阶段。现有测试只证明旧笔记取回成功，没有覆盖它随后进入新运行并继续更新。

建议：从取回包导入旧报告的依赖证明；将全部依赖验证放在持久化提交前，并确保阶段提交过程可恢复。

## 3. P1：`diff`／`norm` 默认轴与提供给研究者的协议不同

位置：`analysis_executor.py:23-25` 与 `analysis_executor.py:62-66`。

协议声明 `diff(x,n=1,axis=0)`、`norm(x,axis=-1)`，实现直接绑定 `np.diff` 和 `np.linalg.norm`。NumPy 的默认值分别是 `axis=-1` 和 `axis=None`。省略轴时，时间差分可能变成 x/y 坐标差，逐帧向量范数可能变成全数组的单一范数；调用仍返回成功。

复现输入 `[[0,10],[2,10],[4,10]]`：`diff(x)` 实际得到 `[[10],[8],[6]]`，按协议应为 `[[2,0],[2,0]]`；`norm(x)` 得到单一数值约 17.89，按协议应为三个逐行数值。

建议：使用显式默认参数的包装函数，或者要求每次写出轴并在缺省时拒绝；补上多维轨迹实例，而不仅是显式指定轴或线性回归的成功测试。

## 4. P1：最终评价绕过统一 checker，空证据也可判完整覆盖

位置：`fish_inquiry.py:271-281`、`fish_inquiry.py:546-558`。

新入口调用的是自定义 `historical_final_evaluator`，没有接入 `idea_check.validate_checks`／`claim-centric-v2`。它只比较研究过程中已经接纳的语料，输出契约也没有六维比较、逐条核心主张的证据绑定、时间／可见性上下文或独立重发现结论。

复现：`prior_work.sources=[]`、`novelty.core_claims=[]`、`coverage=covered` 的结果通过 `InquiryPilot.validate`。因此除了覆盖面不足，当前代码还允许没有覆盖证据的肯定性“已被覆盖”判断。文档披露了语料范围，但没有消除这一接受路径。

建议：冻结后调用公共 v2 checker 或复用完整验证契约，并由控制器提供真实时间／暴露上下文；评价所需的来源论文和后续工作只进入评价端。完整覆盖必须绑定实质主张和来源证据。有限研究语料内的检查可保留为内部核查，不能当作已接入统一新颖性规则。

## 5. P2：没有索引摘要的论文，即使有可读全文也不会尝试获取

位置：`knowledge_broker.py:142-148`。

程序在请求 PMC 全文之前先调用 `SourcePolicy.rejection`；空摘要会得到 `no_readable_content` 并直接 `continue`。因此日期合格、有正确 DOI 和 PMCID 的条目，只因搜索索引没有摘要就永远到不了全文读取分支。

复现中提供 2001 年、带 PMCID 的文献和可正常返回的正文 XML；broker 返回零来源，全文 URL 从未被请求。

建议：先筛日期与排除身份，再尝试摘要／正文获取，最后判断是否存在可读内容。新增“无摘要、有正文”的检索测试。

## 复现

`results.json` 保存本次五项复现结果，`SOURCE_HASHES.json` 固定审查时的实现。脚本将所有研究运行和记忆写入临时目录，仅更新本目录的复现结果：

```bash
cd /Applications/ideas/1103_boundary_discovery
.venv/bin/python historical_inquiry/reviews/open_inquiry_v2_20261105_review/reproduce.py
```

本次是实现审查，未启动新的科学探索或修改上述问题。建议在启动完整研究运行前先处理前四项。
