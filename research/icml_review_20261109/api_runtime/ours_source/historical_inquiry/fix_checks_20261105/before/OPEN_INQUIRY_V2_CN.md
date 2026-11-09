# 统一修正的实施：开放补学与探索入口 v2

2026-11-05。当前入口为 `fish_inquiry.py`，依据 [统一修正记录](REVISION_DECISIONS_20261105_CN.md) 实施。研究角色继续请求 GPT-6 Luna。`fish_pilot.py`、原始测量、旧研究者笔记和已冻结试跑保留；新运行使用新的 run-id 和 `researchers_v2/` 分支。

## 已实现的要求

| 修正要求 | 当前行为 | 代码 |
| --- | --- | --- |
| 1. 来源与测量背景 | 提供 Dryad 数据 DOI、许可、数据发布日期、已核实的斑马鱼物种、追踪数组布局、单位、处理和质量说明；任务、年龄、场景和标定的真实未知项分别记录。按字段筛掉原始档案中的论文解释、结论与模型信息。 | `inquiry_services.py:measurement_context` |
| 2–3. 联网补学与任务日期 | 知识请求自动查 Europe PMC、Crossref、OpenAlex；记录查询、网络响应、出版日期依据、实际摘要/正文内容和获取时间。开放查询主题与材料类型。筛除来源论文标识或被屏蔽内容；未知日期、没有可读内容或接口失败时继续尝试其他来源。 | `knowledge_broker.py`、`configs/fish_v2.json` |
| 4. 扩大计算接口 | 保留原操作；增加可组合的数组表达式、临时变量、状态/条件定义、分段比较、分组统计、滞后/滚动操作和最小二乘拟合。请求保存问题、变量含义、单位、参数、执行器源码、结果及完整数组。 | `analysis_executor.py` |
| 4. 接口能力缺口 | 自然语言或暂不可执行的分析请求产生 `controller_task.json`；控制器用同一 Luna 调用适配成分析计划并执行。仍无法实现时明确保留待处理任务，交回共同讨论。 | `AnalysisExecutor.execute`、`InquiryPilot.plan_analysis` |
| 5. 持续学习 | 复用原 `Memory` 类和稳定身份。取回当前版本前审核来源、日期及内容依赖；原鱼类封闭试跑可通过冻结输入/输出/工具审计建立依赖闭包，其六条当前笔记已实际取回。其他旧任务笔记保留，待完整依赖审核后供应。 | `NoteGate`、`record_note_dependencies` |
| 5. 理解与阅读分别记录 | 沿用 `mastery=read/explained/used`；补学记录实际例子、适用条件及理解变化。无理解变化时允许空笔记；核查支持原判断时也允许只记录回应。 | `InquiryPilot.call/validate` |
| 6–7. 提问与继续探索 | 保留观察、期待、期待依据，以及个人/共享问题的独立版本。显式记录外部事实缺口、尚未选择的观察定义、接口缺口、下一动作及停滞理由。初读后、交流后、返回讨论后、核查回应后和新会话续接都可申请补学或计算。 | `fish_inquiry.py` |
| 7. 减少固定轮次重复 | 每轮保存实际理解变化、补学和待处理能力任务；全部研究者有明确停滞理由且没有学习或问题修订时暂置该线索。最大轮数是任务预算，默认 6，可配置。 | `InquiryPilot.progress` |
| 8. 核查推理及研究后果 | 优先检查具体疑点及停止/放弃分析的决策；同时核查前提与由此前提推出的行动。相同文字和后果的已查判断不重复占用预算。结果返回共同讨论，保留异议、未决问题和同键纠正版本。 | `RecordLedger.select`、`InquiryPilot.verification` |
| 8–9. 冻结与评价 | 候选及生成证据冻结后，最终评价独立运行两项检查；评价不回写研究记忆。新协议不能续写旧协议的运行。 | `GENERATION_FREEZE.json`、`EVALUATION_ISOLATION.json` |

## 启动

在项目目录执行：

```bash
cd /Applications/ideas/1103_boundary_discovery
.venv/bin/python -u historical_inquiry/fish_inquiry.py \
  --config historical_inquiry/configs/fish_v2.json \
  --run-id inquiry_v2_001
```

需要已登录的 Codex CLI 和公共网络访问。运行后记录位于 `historical_inquiry/cases/fish_001/runs/inquiry_v2_001/`。同一命令可恢复已接纳阶段，前提是代码、配置和输入输出哈希不变；更换配置或代码后使用新 run-id。

鱼类配置为知识材料 **2010-01-01 之前**，保留原始测量例外。未来任务在自己的配置里设置日期。来源论文排除名单属于控制器配置，不向研究角色提供被排除论文的身份。

研究角色通过结构化请求取得材料与计算。其隔离 CLI 继续关闭直接工具执行，控制器完成联网和计算并将筛选结果返回，避免绕过来源边界。

## 请求示例

知识请求：

```json
{"needed":true,"gap":"尚不能区分描述状态与行为状态","why_now":"需要选择可修改的观察定义","queries":["operational definition behavioral state time series"],"source_ids":[],"record_ids":[],"operations":[]}
```

计算请求由研究者指定问题和操作性定义，完整协议见 `analysis_executor.py:PLAN_PROTOCOL`。命名为 `analysis/segment/compare/state/model` 的操作均可使用同一组合计划；暂不可表达的方法可用 `custom` 请求交给执行控制器。拟合当前支持有截距的最小二乘及按行顺序切分的留出误差，更复杂方法进入具体能力任务。

`services/knowledge/controller_only/` 保存原始检索响应和排除记录；研究角色收到 `replies/` 中通过筛选的文本。`services/analysis/<请求>/` 保存参数、控制器计划、执行器源码、结果和数组。`broker/` 保存实际返回研究者的材料。`memory_retrieval/` 保存当次取回的笔记，内容/依赖审核记录位于控制器目录。

检索目前直接读取索引摘要和可访问的 PMC 文章正文片段（最多 50,000 字符）。其他材料类型通过开放查询寻找、核实；尚未取得可核实正文时如实返回缺口，继续请求替代来源。出版日期未知的材料不进入历史研究上下文。最终评价使用本任务实际接纳的语料，原创性覆盖不足时保持 `unclear`。

## 验证与实际运行状态

[实施检查目录](implementation_checks_20261105/) 保存以下结果：

- 真实联网接口返回了 5 份截止日期前材料，其中 4 份为索引摘要、1 份包含正文内容；Crossref/OpenAlex 连接失败以及部分正文不可访问的记录均保留。此项检查验证检索与筛选链路，材料与研究问题的相关性仍由研究者阅读判断。
- 真实 R01 轨迹上执行了研究者定义接口的距离变量与两个 80 帧分段的条件统计，参数、数组和结果可复查，见 `ACTUAL_COMPUTE.json`。
- 旧鱼类试跑六条当前笔记已审核并取回，原版本保留。
- 旧鱼类运行的 205 个冻结文件逐项哈希相同，原入口及依赖源码与旧快照相同，见 `IMPLEMENTATION_AUDIT.json`。

历史入口测试 **47 项通过**（含新 v2 测试 9 项），原持续记忆/交接测试 **11 项通过**。自动测试覆盖网络失败与替代检索、未知/越界日期、来源排除、正文身份匹配、表达式执行边界、条件比较、拟合、能力请求交回、旧笔记审核、推理后果优先级，以及补学→核查→共同回应→冻结→恢复的完整交接。模型回答使用 fixture。此次修改完成实现和接口验证；新的完整 Luna 科学探索尚未启动。

```bash
.venv/bin/python -m unittest discover -s historical_inquiry -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```
