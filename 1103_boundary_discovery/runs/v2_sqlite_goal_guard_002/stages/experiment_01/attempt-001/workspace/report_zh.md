# E03 实验报告

## 执行与观测

使用项目 `.venv/bin/python` 与真实临时 SQLite WAL 数据库，完成 72 次运行：H2、H3 各 12 个种子，每种子三策略按冻结种子随机排列，每次新建数据库。SQLite build 为 3.51.3；page_size=4096、synchronous=NORMAL、wal_autocheckpoint=0。每次均提交 24 次事务、共 240 行；同一 shape 的全部策略/种子内容 SHA-256 相同；所有运行最终 residual_frames=0。PASSIVE 返回 tuple 按策略/shape 固定：H2 fixed (0,6,6)、WAL-growth (0,16,16)、lifecycle (0,10,10)；H3 分别为 (0,12,12)、(0,16,16)、(0,14,14)。

以最终冻结 seed=3104 的 10,000 次配对 bootstrap 计算，H2 lifecycle 减 fixed 的 checkpoint 时间均值差为 -0.080 ms，95% CI [-0.117,-0.050]；减 WAL-growth 为 -0.021 ms，CI [-0.070,+0.017]。H3 相应为 -0.047 ms，CI [-0.176,+0.085]；及 +0.155 ms，CI [+0.050,+0.269]。

延迟条件未通过。例如 H2 lifecycle 减 fixed 的 writer p95 CI 上界为 +0.004 ms，H2 lifecycle 减 WAL-growth 的 reader 最大完成延迟上界为 +0.068 ms；H3 lifecycle 减 fixed 的 writer p95/p99 上界分别为 +0.021/+0.031 ms，H3 lifecycle 减 WAL-growth 的 reader 最大完成延迟上界为 +0.181 ms。其余各差值与完整区间见 `classification.json`。

## 按冻结规则分类

观测分类为 `uncertain_or_tradeoff`。`lifecycle_gain` 不成立：H2 lifecycle 对 WAL-growth 时间区间跨零，H3 相对 fixed-period 区间跨零且相对 WAL-growth 的时间成本更高，另有多项延迟区间上界大于零。`baseline_sufficient` 也不成立：它要求每个 shape 延迟匹配，现有延迟区间不满足上界均 <=0。相同工作和 residual 控制通过，但这不足以满足任一明确 outcome rule。按合同，不据此提出假说状态更新。

## 操作化及限制

冻结计划只给出 H2/H3 的定性形状。为执行而预先固定事件表：H2 两个写突发为 commits 1–6 与 15–24；读者 A 在 commit 2 后开始、commit 6 后释放，随后 quiet commits 7–14；读者 B 在 commit 15 后开始、commit 16 后释放。H3 突发为 commits 1–8、11–16、21–24；短读者 A 在 commit 5 后开始、commit 10 后释放；长读者 B 在 commit 18 后开始、commit 24 后释放。间隔 2 ms，burst 内提交间隔 0.25 ms。该事件表保存在代码及原始数据中。

精确偏离/操作化：冻结计划给出 H2/H3 的定性顺序，没有逐提交索引。执行前将其落实为上列提交索引事件表；没有改变策略、触发阈值、24 次提交、种子区间、重复数或结果分类规则。未出现命令失败或缺失试次。策略串行运行，测得延迟不是多客户端并发服务分布；仅适用于本次 SQLite build、小型本地轨迹，不表示生产性能或世界新颖性。
