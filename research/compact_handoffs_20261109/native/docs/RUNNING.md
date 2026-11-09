# 运行与查看结果

当前统一修正后的研究者协作使用 `historical_inquiry/fish_inquiry.py --run-id inquiry_v2_001`，完整配置、请求协议和验证记录见 [开放补学与探索 v2](../historical_inquiry/OPEN_INQUIRY_V2_CN.md)。旧 `fish_pilot.py` 用于冻结协议复查；新入口使用新 run-id。

持续学习与共同提问使用 `src/learning_lab.py`，说明见 [learning_lab/README.md](../learning_lab/README.md)，两组实际结果见 [RESULTS_CN.md](../learning_lab/RESULTS_CN.md)。CLI 与原生角色交接共享同一持久记忆和结果接口；原生接续用 `--executor queue`。

当前以构建 idea 为主的任务使用 [idea builder → check agent](IDEA_CHECK.md) 入口：先提出研究想法，再检查相近已有工作与明显数学错误。下面是原有 V1/V2 实验流程。

新 checker 使用 claim-centric-v2。历史复查可用 `src/idea_check.py --idea <原候选JSON> --evaluation-context <按idea ID映射的上下文JSON> --run-dir <新目录>`，在上下文中记录参考时间与每篇来源的对应结论是否隐藏；上下文仅用于最终检查。未提供时按当前文献范围检查。旧报告不回写。

最新 V2/V2.1 的启动、恢复和从证据快照继续运行，见 [V2_ARCHITECTURE_CN.md](V2_ARCHITECTURE_CN.md)。最新结果见 [V2_RESULTS.md](../V2_RESULTS.md)。下文保留 V1 首轮的原运行命令。

首轮已完成，当前结果见 `INITIAL_RESULTS.md` 和 `runs/pilot_001/final/REPORT.md`。原始 c07 汇总已被更正，详情见 `REPORTING_CORRECTION.json`。

## 本次首轮

```bash
cd /Applications/ideas/1103_boundary_discovery
.venv/bin/python -u src/discover.py \
  --brief bootstrap/PILOT_BRIEF.md \
  --run-dir runs/pilot_001 \
  --max-actions 7 --model gpt-6-luna --effort high --timeout 900
```

需要已有 Codex CLI 登录和联网权限。运行器不读取、保存或打印登录凭据。模型名称为实际请求的名称，不能从客户端独立核验服务端模型权重。

协调者每轮读取累计证据，选择一个研究角色及其具体任务。研究角色实际使用工具、保存结果，随后再次唤醒协调者。达到动作预算后写总结；预算结束不等于发现成功。

## 查看进展

- `runs/pilot_001/events.jsonl`：每个模型阶段开始、结束、成功或失败。
- `runs/pilot_001/discovery_state.json`：协调决策与各角色的研究结果。
- `runs/pilot_001/manifest.json`：调用模型、耗时、用量、文件哈希和结果位置。
- `runs/pilot_001/stages/<阶段>/attempt-001/prompt.txt`：完整任务。
- 同目录 `command.json`、`events.jsonl`、`stderr.log`、`completion.json`：调用及工具记录。
- 同目录 `workspace/`：该角色的代码、公开数据、分析、报告和 `result.json`。

`success` 只表示该阶段正常返回并写出必需结果字段。科学结论的状态在结果和报告中单独说明。

## 中断后恢复

确认旧进程已经退出，再执行相同命令。成功且输入输出哈希仍一致的阶段会复用；失败重试进入新的 attempt 目录，旧记录保留。已结束的探索不会自动重跑。

要探索新问题，复制 brief 并换一个 run 目录。不要修改进行中 run 的任务、证据或工作目录。初版只支持一个控制进程操作一个 run。

可从 `docs/NEW_DISCOVERY_BRIEF.md` 开始，将命令中的 brief 改为该文件或它的副本，run 目录改为 `runs/pilot_002`。这会真正调用模型和工具。

## 协作与优先级调整

另一个角色在独立工作目录完成研究后，可以向 run 的 `contributions/` 添加一个新的 JSON 文件，写明状态、来源、报告路径、结果路径和哈希。后续调用会把这些贡献加入输入；旧贡献不覆盖，完成记录明确替代之前的 running 记录。首轮的两个并行科学分支由本聊天主控派发，顺序循环由协调模型自行派发。

需要调整执行优先级时，新增 `OPERATOR_STEERING_v2.md` 等版本文件，不改写已被调用读取的旧版本。运行器读取字典序最后一个版本并记录其哈希。该入口适合调整资源和探索顺序，不应写入期望的科学答案。

每个角色收到实际时间预算，并应在截止前保存部分结果。研究角色超时会作为明确的执行失败返回协调者，供缩小任务或转向；认证/传输和格式错误仍需恢复，不能当科学证据。

## 扩展

六种角色是协调、边界识别、跨域联系、理论构造、实验与质疑。它们按证据需要反复调用，首版以顺序共享文件的方式协作，不将角色数当作并行数。协议没有固定变量菜单或公式语法；agent 可以写任意合理的本地分析代码并检索新的公开来源。

当前本机计算足够。后续需要服务器时，通过独立执行适配器提交计算，模型调用仍由本机控制；凭据不进入研究日志或候选材料。
