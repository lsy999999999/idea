# V2：让解释分歧决定下一项实验

V2 沿用真实 Luna 调用与独立工作目录，在 `src/discover_v2.py` 增加研究控制逻辑。V1 代码和首轮科学产物保留。

## 一轮如何运行

1. 两个研究者分别从同一份问题与初测材料出发，在不同上下文中提出解释。提示要求它们不查看彼此结果；这不是操作系统强制的读取隔离。
2. 跨域研究者读取两组解释及真实文献，指出已知内容、解释是否相容，以及可能需要的新测量或表示。
3. 计划者读取最新解释账本，提出至少两个可行实验，按能区分的解释、数据可得性和成本选择一个。它可以新增或修订解释，避免搜索被初始候选限制。
4. 程序检查计划结构，保存冻结的预测、分类条件、预期影响和时间记录。科学上是否真正可区分仍需检验；不同文字不自动等于不同预测。
5. 实验者执行真实程序或测量，保留逐次结果和代码，按预定条件报告结果类别。无法归类就返回不确定，不能改阈值。
6. 程序按照已冻结的影响映射更新解释状态。失败或部分执行不构成反证；相互冲突的结果保留为 mixed，明确声明的逻辑依赖被反驳会触发后继解释复查；修订来源本身不代表逻辑依赖。
7. 计划者读取更新后的账本再选择下一步。预算结束后，独立复核者重算关键结果并检查分类，报告者按完整账本汇总。

## 本轮试图改善什么

V1 把竞争解释和证据更新主要留在自然语言报告里。V2 把它们变成程序可检查的状态，特别防止：只有一条故事不断得到补充、实验没有区分对象、结果出来后改变判据、执行超时被写成科学失败，以及最终总结遗漏新证据。

没有预定义正确变量或公式。假说内容、操作性测量和实验设计由研究者提出。程序验证的是引用与结构、冻结计划及更新一致性，不能证明科学分类正确，更不能自动判定原创性。

## 文件入口

- `src/hypothesis_ledger.py`：不可覆盖的解释记录、预定实验映射、证据与依赖状态。
- `src/discover_v2.py`：生成、检索、计划、执行、更新、复核和报告的控制流程。
- `docs/V2_CONTRACT.md`：研究角色必须提交的结构。
- `bootstrap/v2_checks/`：离线状态与恢复测试，和科学实验分开。
- `runs/<run>/v2_state.json`：当前控制状态。
- `runs/<run>/frozen_plans/`：执行前保存的实验计划与哈希。
- `runs/<run>/snapshots/`：每轮计划所读取的解释账本。
- `runs/<run>/ledger.json`：包含最终复核标记的解释与实验记录。
- `runs/<run>/controller_source/`：启动时的控制代码与协议副本。

## 运行

```bash
cd /Applications/ideas/1103_boundary_discovery
.venv/bin/python -u src/discover_v2.py \
  --brief bootstrap/V2_BRIEF_20261104.md \
  --run-dir runs/v2_sqlite_001 \
  --max-experiments 3 --model gpt-6-luna --effort high --timeout 600
```

需要已有 Codex CLI 登录和公开网络访问。重复相同命令可恢复已完成阶段；已完成的 run 不会重新发起模型调用。不要同时启动两个控制进程操作同一个 run。

首轮目的是跑通一个能产生、区分、修订解释的完整案例。执行完成、一个现象得到解释、原创 idea 获得支持、方法优于单 agent，是四种不同结论。这个运行没有自动建立最后两项。

## V2.1：避免廉价的已知事实检验挤掉原问题

V2 的真实首轮发现一个调度缺陷：策略实验未得到明确结论后，计划者花了后续两个槽位检验 reader 年龄与 snapshot 位置，后者主要重现官方文档已解释的行为。`src/selection_guard.py` 因此增加了可选的目标约束。

每项候选实验须说明与固定研究目标的关系、已有工作解释到哪里、仍未解决什么，以及不同结果会改变哪个决定。计划分为直接检验目标、解除具体障碍、校准。存在可执行的目标实验时，程序不允许校准取代它；选择校准时，必须明确它解决了同一批候选中某个目标实验的哪个障碍。结构检查无法证明语义真实或创新性；角色仍可能误判研究价值，需要检查实际运行。

在新运行命令中添加 `--anchor-file <目标文本文件>` 即可启用。不要给一个已在运行的 run 临时改变该参数。固定目标文件应描述要解决的问题，不能规定正确的科学答案。

新任务建议启用这一选项，并为该任务另写 brief 和目标文件；例如从头运行本例可使用一个未存在的目录：

```bash
.venv/bin/python -u src/discover_v2.py \
  --brief bootstrap/V2_BRIEF_20261104.md \
  --run-dir runs/v2_sqlite_fresh_003 \
  --max-experiments 3 --model gpt-6-luna --effort high --timeout 600 \
  --anchor-file bootstrap/V2_ANCHOR_20261104.txt
```

本次继续运行从第一个策略实验后的证据快照出发，保留原三轮的全部产物：

```bash
.venv/bin/python src/fork_v2.py \
  --from-run runs/v2_sqlite_001 \
  --to-run runs/v2_sqlite_goal_guard_002 \
  --after-experiments 1 --max-new-experiments 1 \
  --anchor-file bootstrap/V2_ANCHOR_20261104.txt

.venv/bin/python -u src/discover_v2.py \
  --brief bootstrap/V2_BRIEF_20261104.md \
  --run-dir runs/v2_sqlite_goal_guard_002 \
  --max-experiments 2 --model gpt-6-luna --effort high --timeout 600 \
  --anchor-file bootstrap/V2_ANCHOR_20261104.txt
```

第一条命令只用于首次建立继续运行；目标目录已存在时会拒绝覆盖。第二条可单独用于恢复。总实验预算 2 包含继承的 1 项实验和新增的 1 项；`fork_provenance` 记录快照路径与哈希。这是基于失败分析的修订运行，不是随机对照，也不能单凭这一次选择变化估计发现率提升。

`src/summarize_v2.py <run目录> --output <输出JSON>` 可汇总实际调用、实验、状态与继续运行的来源。计数不等于发现质量。
