# 持续学习、相互质询与科学假说修订：相近工作核查

核查日期：2026-11-07（Asia/Shanghai）。范围：文献／知识驱动的假说修订、多 agent 质询、跨领域概念迁移、持续科研记忆，以及正式发表状态。使用公开搜索、OpenAlex 定位，随后读取 ACL 官方论文集、期刊页面及可获取正文。搜索摘要不作为录用证明。原始来源保存在 sources/；这是定向查新，不是穷尽性原创性认证。

## 主要判断

“发现知识缺口—补学—讨论—修订假说”已有直接相近方法，并有正式发表。“固定模型权重、通过上下文学习改进科研推理”也已有工作。先前把这一宽泛循环当作候选主贡献的定位需要收窄。

尤其接近的两套系统是 MotivGraph-SoIQ 和 Co-Scientist。前者明确把理解缺口、补充检索、理由与想法修订串联起来；后者包含文献学习、科学辩论、假设分解、反思、演化和上下文记忆。因此不能把已有工作概括成“只生成、打分”，从而制造与本项目的差别。

## 已核实正式发表

| 工作 | 正式来源 | 直接重合点 | 已读范围 |
|---|---|---|---|
| MotivGraph-SoIQ: Integrating Motivational Knowledge Graphs and Socratic Dialogue for Enhanced LLM Ideation | EMNLP 2025 Findings，2913–2933 | 导师追问暴露理解缺口，研究者补充检索，自主修订想法与理由 | 官方摘要／出版记录；arXiv 正文方法与评估部分 |
| Accelerating scientific discovery with Co-Scientist | Nature，2026-05-19，655:487–496 | 检索阅读、科学辩论、推理缺口修复、假说演化、持久上下文 | 期刊正文、方法、评估、讨论 |
| ResearchAgent: Iterative Research Idea Generation over Scientific Literature with Large Language Models | NAACL 2025 主会长文，6709–6738 | 文献和实体知识辅助形成问题，多 ReviewingAgents 反馈迭代修订 | 官方摘要／出版记录 |
| SciMON: Scientific Inspiration Machines Optimized for Novelty | ACL 2024 主会长文，279–299 | 检索启发，与已有论文比较并迭代更新 idea | 官方摘要／出版记录 |
| Literature Meets Data: A Synergistic Approach to Hypothesis Generation | ACL 2025 主会长文，245–281 | 文献知识与数据联合生成假说；评价下游预测及辅助人类判断 | 官方摘要／出版记录 |
| SciAgents: Automating Scientific Discovery Through Bioinspired Multi-Agent Intelligent Graph Reasoning | Advanced Materials，2024-12-18 在线；2025 年卷期 37(22):2413523 | 知识图谱、跨学科联系、科学家与 critic 角色、上下文学习和共享历史 | PMC 正文 |
| The Virtual Lab of AI agents designs new SARS-CoV-2 nanobodies | Nature，2025-07-29，646:716–723 | PI 与多个学科研究者开会协作，人类提供高层反馈 | 期刊摘要与出版记录，正文受订阅限制 |
| Differentiated memory and scientific cognition in AI research agents | Frontiers in Big Data，2026-08-05 | 长期研究记忆、来源敏感路由、批评和经验影响后续想法 | 期刊正文；文章类别为 Hypothesis and Theory，提出 Mnemo 研究框架，不是已完成的系统有效性验证 |

## 最值得细读的对应关系

### MotivGraph-SoIQ

官方来源：https://aclanthology.org/2025.findings-emnlp.158/

正文：https://arxiv.org/html/2509.21978

方法 2.2.2 明确写道：研究者在为 idea 辩护时，通过反思识别 concept 或 understanding 的缺口；随后可用 API 做 supplementary knowledge exploration；再提交 refined idea 与 updated rationale。导师只提问，不提供直接解答，也不代替作者修改想法。这与当前“质询触发补学，补学触发理解和假说修订”的宽泛设想高度重合。

原文证据：
> In defending its idea, the researcher agent may identify flaws or gaps in its concept or understanding through critical self-reflection.

> When this occurs, the researcher agent can perform supplementary knowledge exploration (utilizing the available API tools) to seek methods for addressing these weaknesses and gather supporting evidence.

区别：该方法以导师／研究者非对称互动为主；追问包括 innovation、feasibility、rationality，末尾可 ACCEPT／REJECT 并丢弃被拒想法。本项目保留不成熟分支、稳定学科身份、长期版本记忆。差异存在，但角色对称化和保留规则本身尚不能构成充分的方法新意。

评估：作者做了方法比较、消融、人类与模型评价。主要表格并不支持“所有指标都最好”的笼统说法，应按具体列看。训练：正文所述生成／对话使用现成模型；另有经过微调的 Fast-Reviewer 评估器。不能把评估器微调误写为研究者必须微调。

### Co-Scientist

来源：https://www.nature.com/articles/s41586-026-10644-y

Evolution agent 的 Enhancement through grounding 已包括：
> identifying weaknesses, generating search queries, retrieving and reading articles, suggesting improvements and elaborating on details to fill reasoning gaps.

Generation agent 同时采用文献探索、科学辩论、逐层识别中间假设、扩展研究方向。Meta-review 把反馈追加到后续提示；正文明确说明 learning without back-propagation（例如 fine-tuning 或 reinforcement learning）。上下文记忆保存系统与 agent 状态。

论文包含组件消融、专家评价及生物医学实验支持，且不同证据各有范围。不可把有限生物医学验证扩展成普遍科学发现能力。本项目若仅声称“阅读后改变推理”“不微调的持续改进”“多角色讨论”，不足以与它区分。

### Mnemo

来源：https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2026.1916523/full

提出 authored work、external reference、critique、experience、judgment 的分化记忆，强调 provenance 是路由依据，并通过不同记忆之间的受控联系生成新方向。

文章明确定位为研究议程：
> Mnemo should not be presented as a finished autonomous scientist. It is better understood as a research agenda organized around falsifiable architectural claims.

它使“有持续个人研究历史、批评影响后续思考、来源化记忆促进创意”也不能直接作为无人提出的概念。其形式是理论／框架文章，不能当作已经证明该架构有效。

## 非正式发表证据与待核实项

### Idea-Catalyst（高度相关）

Sparking Scientific Creativity via LLM-Driven Interdisciplinary Inspiration，2026-03-12。

来源：https://arxiv.org/abs/2603.12226

正文：https://arxiv.org/html/2603.12226v1

实际方法：把研究目标拆为问题；分析目标领域进展与未解决困难；改写成领域无关的概念问题；检索其他领域；把外部观点重新放回原问题中组合，生成 idea fragments。论文明确强调早期探索和避免过早按可行性裁剪，与用户偏好高度接近。

本轮查到 arXiv 和数据库记录，未确认正式录用。正文保留的通用 ACM 模板会议／日期占位符不是录用证据。论文报告新颖性和洞见评价收益，不直接等同于新机制经实验证实。

### AScience / ASCollab

Hypothesis Hunting with Evolving Networks of Autonomous Scientific Agents，2025-10-08。

来源：https://arxiv.org/abs/2510.08619

论文研究异质科研 agent 的持续探索、动态协作网络与同行评价；在癌症队列中积累专家评分的结果。与持续科研群体有关。本轮读取 arXiv 摘要；OpenReview 页面 https://openreview.net/forum?id=L1jwyORby0 出现浏览器验证，公开 API 返回 403，录用状态未确认。

### MAIL

检索数据库返回 Memory-driven, Adaptive, Incremental, and Literature-grounded framework for hypothesis generation in chemistry，DOI https://doi.org/10.1016/j.array.2026.101323 。出版社入口只返回跳转页，尚未独立核实正文／正式日期。本轮不把它列作已核实发表证据。

## 对本项目的影响

1. 这个方向有人做，也有顶会主会、Findings 和期刊发表；不能据此推断本项目已有足够贡献或能投同一层次。
2. “知识缺口—学习—推理变化”作为宏观描述已有直接覆盖。把 refinement 改叫 conceptual reconstruction 不会自动产生新意。
3. 值得继续研究的具体问题：在已有假说反复吸收材料、却仍维持旧框架的情况下，什么机制能促使 agent 合理修改关键假设、对象定义或关系结构？这是待验证的贡献方向，不是已确认空白。
4. 区分材料获取、知识理解、概念修订、生成新后果。现有电池试验的 URL 服务失败使后两步未被充分检验。
5. 若提出方法，需要与普通 RAG＋迭代修改、MotivGraph 式追问＋补查、Co-Scientist 式反思／演化比较；模型、材料和预算应尽量匹配。过程证据用于解释方法收益，不必把主研究转成 Ranker 或 benchmark。
6. 新想法无需先完成解答、证明、实现或实验。评估 agent 方法仍需要观察它是否比对照更能产生有内容的假说或后果，并清楚记录已有研究重合。

## 其他官方链接

- ResearchAgent：https://aclanthology.org/2025.naacl-long.342/
- SciMON：https://aclanthology.org/2024.acl-long.18/
- Literature Meets Data：https://aclanthology.org/2025.acl-long.12/
- SciAgents：https://pmc.ncbi.nlm.nih.gov/articles/PMC12138853/
- Virtual Lab：https://www.nature.com/articles/s41586-025-09442-9

本次未修改 agent 实现、冻结实验和研究者记忆，未发起新科学试跑。
