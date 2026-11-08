# V2 计划阶段结论

## 决定

本阶段 `decision=finalize`，`plans=[]`，`selected_plan_id=null`：账本注明剩余实验槽为 0，故不冻结或派发新实验。这是资源约束下的诚实收尾，不代表新发现成立。

## 观察

- E02：72 次回放中，held-out 单一轨迹上 lifecycle 策略相对固定周期和 WAL-growth 策略的 checkpoint 时间配对区间均包含零；按预定规则为 `uncertain_or_tradeoff`。单一 held-out shape、串行延迟与 WAL 重启计数限制了结论。
- E03：12/12 配对在长、短 reader 年龄条件下均观测到 2/26 checkpointed frames，Δ=0；冻结分类为 `no_age_penalty`。这反驳该轨迹中的强年龄代理预测，但不检验 snapshot 前缀位置。
- E04：SQLite 3.51.3 的固定 240 行轨迹中，12/12 种子 early/mid/late 都是 2/14/25 帧，log_frames 均为 26，checkpoint 前 WAL 均为 107152 bytes。冻结分类为 `position_order`，支持 D1、反驳 D2。

## 解释与后续方向

SQLite WAL 官方文档已说明 reader end mark 会限制 checkpoint；E04 是该已知机制在一个受控本地轨迹中的重现，不是新机制或世界新颖性证据。E02 未显示 reader lifecycle 信号带来明确的策略成本收益。因此，本轮没有足够证据提出新的发现性假说。

曾考虑的两个可执行后续方向是：在新 workload 或 page layout 上检验 snapshot-position 结果是否外推；以及在至少两个新的 held-out release/burst shape 上重做策略成本、完成量和服务延迟比较。前者区分局部效应与跨配置效应，后者针对策略收益；本阶段无剩余槽，均不选择。下一轮应先为选定方向取得实验槽并冻结轨迹、分类规则和种子。

请求模型为 GPT-6 Luna；本计划阶段未调用模型推理，也未验证后端权重。
