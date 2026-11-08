# 科研 idea agent：第一批复现选择

核查日期：2026-11-08（Asia/Shanghai）。本轮完成文献选择、官网与代码核查、固定版本源码及输入快照；尚未运行研究模型实验。

## 选择结论

建议选择 **ResearchAgent、Virtual Lab、AI Scientist-v2、EvoScientist** 四篇，首先启动前两篇。前三篇覆盖文献驱动迭代、学科角色协作、端到端科研系统的构思环节；EvoScientist 补上 2026 年持续记忆与演化方向，但须先确定论文对应实现版本。

本项目关注：agent 能否形成并发展新的研究问题、假设与解释；学习和他人质询能否引起有内容的理解变化。新 idea 不以立即可实现、已证明或已完成实验为保留条件。下面的“诊断问题”均为待检验问题，不是预先认定的系统缺陷。

| 工作 | 时间与地位 | 为什么选 | 第一轮复现范围 | 重点诊断 |
|---|---|---|---|---|
| [ResearchAgent](https://aclanthology.org/2025.naacl-long.342/) | NAACL 2025 主会；最初预印本为 2024 年 4 月 | 直接围绕文献生成问题、方法、实验设计，并接受多个 reviewer 的迭代反馈；最接近基础对照 | 原始输入中的小样本，跑完整三阶段迭代，保存每一轮而不只保存最后胜出者 | reviewer 分数提高时，问题、假设和推导后果是否实质改变？最初论文是否造成持续锚定？ |
| [The Virtual Lab](https://www.nature.com/articles/s41586-025-09442-9) | Nature，2025-07-29 | PI、不同学科专家和 critic 通过团队／个人会议合作，与我们的共同研究工作台接近 | 先重现官方会议示例与公开研究议程，再在相同材料下测试协作讨论；纳米抗体实验另计 | 专家的发言是否改变其他人的解释、假设或后续动作？PI 是否过早收敛？ |
| [The AI Scientist-v2](https://arxiv.org/abs/2504.08066) | 2025-04-10 预印本；知名的全流程系统 | 给我们一个强、广为使用的系统对照，区分“会构思”与“能把项目推进成论文” | 先复现官方 ideation/reflection 模块；完整树搜索、训练和写论文另立实验 | 对可执行项目的偏好是否影响研究问题的跨度？反思带来什么新增内容？ |
| [EvoScientist](https://arxiv.org/abs/2603.08127) | 2026-03 首发，当前正文 v2 为 2026-10-05；本轮按预印本引用 | 有持久 ideation memory、experiment memory 与演化管理，最适合检验我们的持续学习设想 | 先核对论文三角色／两类记忆与代码版本，再跑原论文 idea 任务及带／不带记忆比较 | 历史经验帮助跨任务迁移，还是不断复用旧方向？学习到的内容是否改变假设及其后果？ |

AI Scientist-v2 所说的 workshop 接收是**系统生成的一篇论文**的接收，不能写成系统方法论文获得 ICLR 主会接收。EvoScientist 正文带 KDD 会议信息，但本轮未独立核实会议论文集，因此不以正式录用作为选择依据。

## “出名”的证据

以下是当天公开指标快照，用于判断关注度，不代表科研能力或复现质量。

| 工作 | OpenAlex 对应记录引用数 | 官方 GitHub stars |
|---|---:|---:|
| ResearchAgent | 287 | 74 |
| Virtual Lab | 352 | 767 |
| AI Scientist-v2 | 629 | 7,477 |
| EvoScientist | 74 | 4,938 |

OpenAlex 数字对应本轮返回的单条记录，未合并预印本与会议版本。原始响应保存在 `sources/`，日期与来源见各 manifest。

## 三个需要保留的相近工作

**[MotivGraph-SoIQ（EMNLP 2025 Findings）](https://aclanthology.org/2025.findings-emnlp.158/)**：与“质询暴露理解缺口—补充检索—修订想法及理由”高度相近，应作为机制层面的重点对照。本轮官方论文页和正文没有找到官方源码链接；GitHub 搜索命中一个未确认归属的小仓库。若按论文重新实现，应标注“方法重实现”，不能称官方代码复现。其新颖性、可行性、合理性质询和最终拒绝机制应先忠实保留，再单独做保留未成熟 idea 的改动实验。

**[Co-Scientist（Nature，2026-05-19）](https://www.nature.com/articles/s41586-026-10644-y)**：有文献探索、科学辩论、反思、演化、锦标赛及上下文记忆，研究目标很接近，OpenAlex 快照引用数 947。论文 Code availability 明确说完整代码未公开。可细读并重实现公开机制，当前不纳入“可运行官方完整实现”的主复现清单。

**[Idea-Catalyst（2026-03）](https://arxiv.org/abs/2603.12226)**：有[作者代码与数据](https://github.com/pkargupta/idea_catalyst)，围绕领域无关问题提炼、跨领域检索及 idea fragments，贴近我们强调的早期跨学科构思。公开影响力较小（本轮引用数 7、stars 60），适合在前三个基线之后补做。官方说明默认 Qwen3-14B，并需要 Semantic Scholar 接入；具体显存需求未核定。

另查到 [Robin（Nature，2026-05-19）](https://www.nature.com/articles/s41586-026-10652-y)，有[官方代码](https://github.com/Future-House/robin)及十种疾病样例。其目标更集中于疾病、实验检测体系和治疗候选；部分路径依赖 Edison 平台，完整结果涉及湿实验，故本轮暂不优先。

## 已核实的复现条件

### ResearchAgent

- [官方仓库](https://github.com/JinheonBaek/ResearchAgent)，固定快照 `babb49b51ebfcebedc39ccde12c9785be7bef46c`。
- 已保存全部 Python 源码及三个数据文件：`papers.jsonl` 为 6,417 条，`knowledge.jsonl` 为 37,903 条，`references.jsonl` 为 43,674 条。它们分别是论文记录、知识记录、参考文献记录，不是相同口径的独立实验样本。
- 入口 `code/main.py`；官方流程默认各阶段迭代三轮，默认模型 `gpt-4o`。实际仍请求 Semantic Scholar 的摘要、参考文献与 embedding，下载输入文件不能保证在线检索可用。
- 源码将模型调用重试失败后的异常转换成普通字符串返回。试跑时须在外围明确记录调用失败，防止把服务报错当成研究内容或 agent 科学能力失败。
- 后续应保留官方输出与失败记录，再评估是否需要独立的接口适配副本。不能悄悄修改原始源码。

### Virtual Lab

- [官方仓库](https://github.com/zou-group/virtual-lab)，固定快照 `8a3a4fd9ccc0cd297bd523751e03bc9527c91832`。
- 已保存核心会议实现和依赖声明；官方还提供纳米抗体研究记录和代码。
- 当前仓库默认模型已改为 `gpt-5.2`，不能将默认运行称为复现 2025 年论文的原始模型设置。正式试跑要回查论文／历史版本并记录模型差别。
- 协作会议可独立评估；复现会议不等于复现纳米抗体生物学实验。

### AI Scientist-v2

- [官方仓库](https://github.com/SakanaAI/AI-Scientist-v2)，固定快照 `96bd51617cfdbb494a9fc283af00fe090edfae48`。
- 已保存构思模块及其模型／检索接口和依赖说明；本地是源码审计子集，未作为完整安装包。
- 官方完整环境按 Linux、NVIDIA GPU、CUDA/PyTorch 配置。当前机器是 macOS ARM，不能承诺在本机复现完整训练链。
- 构思子模块与完整系统须分开命名、计费和报告，不能用子模块结果概括端到端树搜索表现。

### EvoScientist

- [论文指向的官方仓库](https://github.com/EvoScientist/EvoScientist)及当前版本树、commit 已保存。
- 当前 README 描述 plan、research、code、debug、analyze、write 六个角色，论文描述 Researcher、Engineer、Evolution Manager 三角色和两类记忆。需要找到论文实验对应版本或逐项核对实现。
- 论文当前版本写明 idea generation 使用 Gemini-2.5-Pro，代码生成使用 Claude-4.5-Haiku，记忆检索使用 Ollama 的 mxbai-embed-large。作者使用 30 条研究查询评估构思；原始材料与脚本覆盖程度仍待核实。

## 实验安排

1. **原方法复现检查**：每套系统先跑一个官方样例，保留原始角色、提示、停止规则与评价设置；接口或历史模型不可用时，将具体偏差列入运行记录。先确认系统确实在工作。
2. **共同任务诊断**：先用三个有真实来源材料的场景，每个场景重复三次。配一个同模型、同材料的单 agent＋检索对照，记录实际调用数、输入输出 token、检索量与耗时，并设置共同预算上限。这是诊断规模，扩大样本前不做普遍优越性判断。
3. **评价构思过程**：保存最初想法、每次补查、每轮质询、修改后的关键假设、最终及被丢弃分支。给每一次实质修改写出“改前是什么—新材料／质询是什么—改后是什么—新增什么推导后果”。
4. **分别回答三个问题**：有没有改变问题或解释；有没有提出有内容的新假设及后果；这些方向与既有研究的重合程度怎样。最终查重与明显数学／逻辑错误检查继续分开记录。
5. **故障归因**：检索失败、模型调用失败、上下文截断单列；不能据此直接认定 agent 不会创新。模型自评分与独立阅读评价分列，保留正面、负面和不确定结果。
6. **记忆实验**：EvoScientist 的连续任务采用多个任务顺序，比较相同已见材料下的带／不带记忆结果，检查是否只是重复以前的想法或泄露后续任务信息。这个实验在实现版本核实后启动。

候选研究方向本身不必先证明或实现。原论文的 feasibility 评分可为忠实复现保留，但共同任务评价不能把缺少立即实现方案等同于明显逻辑错误。

## 一篇直接研究局限的阅读材料

[AI Research Agents Narrow Scientific Exploration](https://arxiv.org/abs/2605.27905)，2026-05 首发，当前 v2 为 2026-07-11。作者报告用五类 agent 框架和五个 LLM 生成 219,655 个有效 idea，并研究探索集中、靠近起始文献、与后来研究方向的关系等问题。

适合借鉴其“探索范围／距离”和“新问题还是新方法”的诊断。其影响力指标来自邻近已发表论文的引用代理值，不能据此认定某个未实施 idea 的真实未来影响力。正文提供对照设计线索；本轮未重跑其大规模生成或指标，也未完成对各框架适配忠实性的核查。

## 当前交付和执行状态

- 77 次公开来源获取全部完成；保留 URL、获取时间和 SHA-256。
- 已锁定三套首批代码的版本并保存 28 个 Python 文件，完成语法解析和 ResearchAgent 数据记录数检查。这个检查不代表安装成功或科学结果复现成功。
- 当前 shell 中没有可用的 OpenAI／Anthropic API key，未搜索私人凭据文件；当前 Python 环境也未安装 openai 包。真实模型运行尚未开始，模型调用数为 0。
- 下一次执行优先从 ResearchAgent 与 Virtual Lab 的官方小样例开始；先确定可用模型接入，并明确原论文模型复现与统一模型比较的区别。

来源索引：`papers_manifest.json`、`repositories_manifest.json`、`code_audit_manifest.json`、`code_files_manifest.json`。静态检查结果：`AUDIT.json`。旧实验和已有研究者记忆未改动。
