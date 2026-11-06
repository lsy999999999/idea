# 计划阶段报告

## 决策

选择 `experiment`，冻结候选计划 `E02`：比较当前应用可见的活动读者生命周期信号与固定周期、WAL 大小触发策略。此阶段不执行实验。选择理由是它直接检验 brief 的残余问题，即额外可观察状态能否在工作完成量与服务延迟可比时降低 checkpoint 成本。

## 证据基础

- 当前账本 `snapshots/ledger_00.json` 中 A1/B1 是兼容的 end-mark 解释，A2/B2 是兼容的调度/遥测充分性问题；它们不是彼此相斥的预测。
- `bootstrap/v2_scout/result.json` 报告单次本地配对：SQLite 3.51.3，两个条件均为 143 log frames、589192 WAL bytes、busy=0；无 reader 时 checkpointed=143，持有 reader 时为 2。该结果与已知 end-mark 行为一致，单次测量不能验证释放时机的策略收益。
- Seed A retry 与 Seed B 的结果文件均只提出未测试解释。Bridge 已成功完成，未产生新实验；原 Seed A 首次运行超时。
- SQLite WAL 与 checkpoint API 官方文档以及 Walack 摘要已被前序阶段查阅。长 reader 限制 checkpoint 是已知机制；通用读写负载自适应也是已有基线。Walack 全文未查阅，因此不作新颖性判断。

## 比较的行动

`E01` 检验快照位置相同、读事务仍活动时，单纯增加 reader 已存续时间是否改变当前 PASSIVE 进度。它能约束“reader age 可作为当前进度代理”的强说法，但可能只重现已知快照语义。

`E02` 在相同真实 SQLite 回放轨迹上比较固定周期、WAL 大小触发和应用能够观察到的活动 reader 生命周期策略。计入 checkpoint 调用及耗时、完成帧数、reader 完成延迟和 writer commit 尾延迟；未来释放时刻只用于结果分层，不输入策略。

E02 的预注册分类、配对随机化、不同 trace shape 与重复规则见 `result.json`。小型临时 WAL 数据库及项目 Python/SQLite 环境已由 scout 证明可用；执行时须使用新数据库，先冻结轨迹与阈值，并确认总预算内运行。

## 解释范围

没有新增科学解释。E02 下的 C1/C2 是 A2/B2 的明确竞争修订：reader 生命周期信号可带来成本匹配收益，或简单公开遥测基线已足够。它们不是已观察结果，也不支持世界新颖性。当前最小下一步是执行冻结的 E02，然后按同一规则复核分类。
