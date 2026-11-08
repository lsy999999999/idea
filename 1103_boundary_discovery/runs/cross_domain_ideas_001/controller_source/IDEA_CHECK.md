# Idea 构建与最终检查

当前任务：提出新的研究 idea。流程为 **idea builder → check agent**。idea 可以保留尚未解决的核心问题；完整证明、可运行实现、可获得的数据和实验结果均不作为提出 idea 的条件。

## Check agent 的两项职责

1. **有没有人做过相近方向。** 检索论文、项目或技术资料，比较研究问题与核心思路。方向很相近就标“做过”，无需逐个实现细节完全一致。更换名称、应用场景或参数不足以避开这一判断。附来源链接、阅读日期、内容摘录或具体要点，以及相近在哪里。仅共享宽泛关键词不算方向很相近。
2. **数学上是否大体说得通。** 检查明显的算术、代数、方程、量纲和逻辑矛盾，例如 `1 + 1 = 3`。有明确错误时，指出原句或公式和错误原因。没有明显矛盾，就通过粗筛。没有公式的概念性 idea 也可以通过。

未证明的猜想、未知的效果、未取得的数据、较高实现成本或暂时不能验证，都不构成这里的数学错误。检查在这两项判断后结束。

## 输出

每个 idea 保留两个独立结论，原始候选全部保存：

| 项目 | 状态 |
| --- | --- |
| 已有工作 | `already_done` 做过；`no_close_work_found` 暂未找到相近工作；`unclear` 检索或证据不足 |
| 数学粗筛 | `no_obvious_error` 未见明显错误；`obvious_error` 有明确错误；`unclear` 核心表述不足以理解 |

“暂未找到”表示本次检索结果。检索失败用“检索不足”。缺少完整推导本身不触发 `unclear`。两个判断均附简短理由；做过的方向附非常相近的实际来源，有数学错误则附具体错误位置。

## 使用

在项目目录运行，输入和新运行目录都放在项目内。使用已有的 Codex 登录，默认请求 GPT-6 Luna。每个角色默认最多 600 秒。

从研究任务生成 3 个 idea，再统一检查：

```bash
.venv/bin/python src/idea_check.py \
  --brief docs/NEW_DISCOVERY_BRIEF.md \
  --run-dir runs/ideas_001 --count 3
```

只检查已有 idea，可输入 Markdown，或包含 `ideas` 数组的 JSON：

```bash
.venv/bin/python src/idea_check.py \
  --idea runs/ideas_001/ideas.json \
  --run-dir runs/check_002
```

JSON 中每个 idea 只必需 `id`、`title`、`idea` 三个非空字符串。公式、完整解法和实验计划均为可选。Markdown 作为一个完整 idea 输入。

结果位于新运行目录的 `ideas.json` 和 `check_report.json`。完整角色输出及中文说明在 `stages/` 中，检索记录随检查结果保存。调用失败保留原始记录；使用运行器的 `--config` 恢复对应 dispatch，成功后可在新目录重新检查已保存的 `ideas.json`。

旧 V1/V2 入口保留其原有实验协议；当前以构建 idea 为主的任务使用此入口。程序只核对结果字段、候选覆盖和来源记录结构，具体相近程度与数学判断由 check agent 给出。
