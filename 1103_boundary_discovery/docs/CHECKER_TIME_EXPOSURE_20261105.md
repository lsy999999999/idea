# Checker v2：历史新颖性与隐藏来源重发现

用户确定的规则：按来源论文公开时点区分先例和后续研究；保留尚未被实质覆盖的贡献；生成 agent 未接触来源中的对应 idea 时，与一篇或多篇来源论文相同的 idea 仍可以具有任务内新颖性。

## 实现

- `src/novelty_scope.py` 根据控制端冻结的 `evaluation_context`、来源日期区间及 idea 内容暴露记录，确定文献的时间位置与先例资格。日期和确定的暴露状态都需要项目内快照及逐字证据。
- 隐藏来源完整匹配可以得到 `INDEPENDENT_REDISCOVERY`，候选保留；其文献身份仍记录为 `world_novelty: EXISTING_MATCH`。隐藏是对应 idea／结论未通过生成输入、工具或记忆暴露，不是只缺全文。
- 历史时点之后的工作单列；时间或可见性不明时保留未决。控制端明确多来源任务的参考时间，checker 不猜测截止时间。
- `prior_work.verdict` 从含混的 `already_done` 改为 `close_direction_found`。新颖性范围内只有同一合格先例完整覆盖所有核心贡献时，才得到 `CORE_ALREADY_KNOWN`。六维比较不采用机械的全同／一维不同投票。
- `src/idea_check.py --evaluation-context` 接收按 idea ID 映射的控制端上下文，生成阶段不把该文件作为输入。check-only 也可读取候选 JSON 中已有的上下文。跨学科和学习入口使用同一新版 checker，默认 current 范围；历史复查通过 check-only 入口进行。
- 生成角色不能自行声明隐藏或历史时间。程序重新计算来源资格和所有聚合字段，核对报告中的上下文副本，拒绝模型篡改。

完整结构、时间区间规则和结论含义见 `IDEA_CHECK.md`。旧规则另存 `IDEA_CHECK_V1_20261105.md`，V1 和更早报告仍可读取；新调用不能降级为旧协议。原实验输入、候选、角色输出和最终报告均未改写。

## 验证

63 项离线软件测试通过：新增时间／暴露测试 22 项，旧贡献契约测试 20 项，基础 checker 测试 7 项，跨学科交接测试 3 项，学习／记忆测试 11 项。新增场景包括：六维完全重合但隐藏来源仍保留；后续相同论文不否定历史新颖性；更早独立先例仍有效；日期区间交叠／日期缺失／暴露未知保留未决；上下文不可由 checker 改写；多来源、当前范围及 CLI 上下文交接。

两组已完成学习实验的 78 项完整性检查仍通过。检查通过只说明协议与兼容性行为符合这些测试场景。

本次没有调用模型或公开检索，也未将之前五个历史 idea 的结果改称为新版判定。按新版复查这些案例需要先核实各自的来源论文、首次公开时间，以及生成输入／工具／记忆是否包含对应结论。此前复查暴露的引文身份错误仍需单独修复；v2 的日期／暴露快照校验不会自动证明来源身份真实。

复现软件检查：

```bash
.venv/bin/python -m unittest discover -s bootstrap -p 'test_novelty_scope.py'
.venv/bin/python -m unittest discover -s bootstrap -p 'test_claim_novelty.py'
.venv/bin/python bootstrap/idea_check_contract_checks.py
.venv/bin/python -m unittest discover -s bootstrap -p 'test_cross_domain_handoff.py'
.venv/bin/python -m unittest discover -s tests -p 'test_learning*.py'
```
