# 机械迟滞场景：四架构 DeepSeek 短程实验

状态：**四套生成与独立终评全部 complete**。12 条原始候选均保存，包括出错、已有相近方向及未解决候选。

- [结果评阅与推荐继续的关系](/Applications/ideas/research/hysteron_baselines_deepseek_20261110/REVIEW_CN.md)
- [12 条候选的完整内容与逐条检查](/Applications/ideas/research/hysteron_baselines_deepseek_20261110/RESULTS_CN.md)
- [结构化全部结果](/Applications/ideas/research/hysteron_baselines_deepseek_20261110/ALL_RESULTS.json)
- [配置、架构流程和适配范围](/Applications/ideas/research/hysteron_baselines_deepseek_20261110/PROTOCOL_CN.md)
- [状态与实际调用用量](/Applications/ideas/research/hysteron_baselines_deepseek_20261110/STATUS.json)
- [冻结、输入、源码与执行核验](/Applications/ideas/research/hysteron_baselines_deepseek_20261110/VALIDATION.json)
- [运行故障与恢复记录](/Applications/ideas/research/hysteron_baselines_deepseek_20261110/RECOVERY_AUDIT.json)

四套为此前测试的 ResearchAgent、Virtual Lab、AI-Scientist-v2、EvoScientist；DeepSeek 官方 deepseek-flash / high。相同 123 行实测数据，文献严格早于 2024-09-12，中性事实服务与来源隔离保留。AI-Scientist-v2 复用原优先服务器，本机转发模型请求。

生成共 95 次已结算调用，1,562,718 输入、473,261 输出 token；终评及方向复核共 12 次，385,095 输入、92,276 输出 token。失败请求的实际计费未知。原停止实验保持停止，新运行和结果单独存放。

各系统的 `runs/<system>/native_result.json` 保存原版流程产物，`FINAL.json` 保存统一提取的候选，`GENERATION_FREEZE.json` 保存冻结清单，`calls/`、`tools/`、`knowledge/` 保存真实模型、数值计算与来源记录。独立检查位于 `runs/<system>_evaluation/`；共享宽口径检查位于 `runs/shared_prior_work_evaluation/`。控制端数值复算、检查校正和补充服务器执行位于 `controller_only/`。
