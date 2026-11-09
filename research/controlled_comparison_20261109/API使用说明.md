# 模型接口与复跑

本轮实际使用 `gpt-6-luna`、Responses 接口、low 推理配置。配置在 [model_config.json](/Applications/ideas/research/controlled_comparison_20261109/model_config.json)，密钥没有写入实验产物。研究调用均经统一接口记账，API 可以替换。

换 DeepSeek 时创建一个新目录，保留本轮数据与失败历史。填写所用服务实际支持的模型 ID 和地址；模型服务密钥由环境变量 `RESEARCH_MODEL_API_KEY` 提供。下面的准备命令不会调用模型：

```bash
research/replication_selection_20261108/execution/.venv/bin/python \
  research/controlled_comparison_20261109/runtime/prepare_replay.py \
  --output /Applications/ideas/research/deepseek_comparison_new \
  --model YOUR_MODEL_ID \
  --base-url YOUR_API_BASE_URL \
  --api-style chat
```

`--api-style` 支持 `chat` 和 `responses`。只有服务明确支持时才设置 `--reasoning-effort`；不要假定不同厂商的推理配置含义一致。该准备步骤复制数据和适配代码，创建空运行目录，不复用 GPT 的结果或研究记忆。输出目录需放在 `/Applications/ideas/research/` 下，以复用已安装官方源码路径。

先检查准备好的命令，默认不会调用：

```bash
research/replication_selection_20261108/execution/.venv/bin/python \
  research/deepseek_comparison_new/runtime/run_suite.py \
  --cases wave --systems virtual_lab --phases generation correction
```

确认新配置后，在同一命令末尾加 `--execute` 才执行。调度器串行运行，自动启动、关闭统一接口；已有阶段不会自动覆盖或继续。首次可只运行一个系统和一个案例检验新服务兼容性。

当前适配器状态：ResearchAgent、Virtual Lab 的会议/评审已运行；AI Scientist-v2 复用优先服务器的既有环境，调用通过 SSH 文件桥接交给本机，服务密钥不上传；EvoScientist 已取得工具与研究输出，但本轮未完成整个主流程；旧试验中的我们的控制器曾发生来源交接和上下文问题；后续已修复适配层，并完成独立内审与工具验收，见[修复报告](/Applications/ideas/research/controlled_comparison_20261109/interface_repair/修复与验收.md)。换服务后的完整兼容性尚未验证。

共同预算只是上限。实际输入、输出、缓存、失败和子任务调用统一归入所属系统账本；失败请求的费用未知。计算时间、工具次数和内存目前没有统一硬隔离，不能仅凭相同配置声称等资源比较。

本轮结果已冻结。新适配层已支持文档与全数据工具；做方法比较前仍须对齐各系统的数据访问能力。不要覆盖本轮 `runs/`，也不要把旧结果当作新模型输出。


**接口修复后的复跑规则（2026-11-09）**

准备新目录时默认 `--knowledge online`，更新新副本的访问策略并启用公开文献补学；需要封闭语料时显式传 `--knowledge closed`。两种模式均保留完整 CSV 工具。调度器会读取新配置，也可用同名参数显式选择；准备和调度预览都不会调用模型。旧结果、研究记忆和运行目录不会复制，测量 CSV 保持不变。

修复包括短文档来源编号、按需/批量读取、完整 CSV 计算、提交前校验、会话恢复和预算记账。若代码、模型或传输配置改变，使用新目录；不要删除指纹文件来强行续跑。Responses 的推理条目保留已在现有服务测试；Chat/DeepSeek 路径仅完成协议层离线测试，需在新服务做小样本实测。若服务要求专属推理参数，在新配置里设置 `chat_reasoning_parameter` 和服务支持的值，不改全局登录配置。

批量读文档每次最多 8 页、24,000 字符；CSV 目前限制为 20 MB、20 万行，运算使用受限数值表达式。超限会明确报错，不会只用预览冒充完整数据。最终新版本尚未从头完成完整科研生成；验收范围与调试消耗见修复报告。
