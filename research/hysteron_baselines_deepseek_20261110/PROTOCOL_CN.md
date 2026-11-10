# 同场景 DeepSeek 短程架构对照

日期：2026-11-10。用户指定沿用此前测试的四个架构，AI-Scientist-v2 使用原优先服务器。新目录不恢复已经停止的自有架构实验。

## 固定条件

与停止实验相同的 123 行实测 CSV、装置与协议 dossier，SHA256 记录于 INPUT_FREEZE.json。模型 deepseek-flash，官方 DeepSeek API，high 思考，温度不额外设置。一般知识严格早于 2024-09-12；隐藏原研究及版本继续隔离。相同的完整数据数值工具、日期筛选文献工具与独立中性定义服务对四系统开放。研究者输入不含旧假说、停止诊断或作者理论；旧运行仅提供只读代码和隔离定义服务的原始注册材料。

## 四个运行流程

| 系统 | 实际入口与短程范围 |
|---|---|
| ResearchAgent | 原版 ResearchPipeline，每个问题/方法/实验阶段一轮，保留每阶段五维独立 reviewer；追加一次原版 method refinement，使用真实反馈 |
| Virtual Lab | 原版 run_meeting：一轮团队会议、一轮理论成员与科学批评者个人会议、一轮团队综合；每轮按上游含最后发言，共 11 次角色发言 |
| AI-Scientist-v2 | 原服务器原版 generate_temp_free_idea，最多三次构想反思；原版 MinimalAgent draft 后 debug/improve，共两个 CPU 执行节点及执行评阅；完成报告 |
| EvoScientist | 原版 create_cli_agent、规划/委派角色、文件记忆及提取 middleware；一个研究 session，24 graph steps 后以实际轨迹交付。保留 native boundary 记录 |

共同最后汇总仅提取各系统已发展出的 1–3 个假说，不向系统注入其他系统的候选。随后分别进行独立两职责检查：已有相近方向及明显数学/逻辑错误。验证、完整证明与新颖性证明不是保留条件。

## 省用与交付

通过减少研究回合与上下文复制省用，不压缩 high 思考成容易截断的总额度。单次起始 16,384 token（含思考），遇 length 保存原回复并扩大到至少 65,536 重试。调用内容寻址缓存用于续跑，保留原始请求、响应、失败、工具和记账。工具用量边界留出直接交付机会。总预算配置继承宽裕上限，实际用量单列。

## 适配与比较范围

ResearchAgent 原始论文/实体输入改为共同匿名测量案例及字段；Virtual Lab 的原 PubMed 被共同筛选检索替代。EvoScientist 保留 native agent graph，外部检索改为共同工具，shell 改为隔离文件 backend 与受限数值工具；其自由代码执行能力因此有差异。AI-Scientist-v2 由本机 SSH 文件桥转发模型请求，密钥不上服务器；生成计算代码经过 AST 读写/导入检查，使用原执行器，最多 120 秒、4 CPU 线程，无训练。原始目录不修改。

这是同输入、同模型的短程案例对照，轮数和 native 角色数随架构不同，实际资源按账本报告。AI-Scientist-v2 是有限节点的官方核心流程，EvoScientist 使用受限工具适配；不将其等同于完整论文基准或各架构最高性能。
