# E03 实验报告

## 观察

按冻结计划完成 12 个配对、共 24 个独立临时 SQLite WAL 数据库运行。环境为 Python 项目环境中的 SQLite 3.51.3；固定 page size 4096、WAL 模式、`synchronous=NORMAL`、`wal_autocheckpoint=0`。每个数据库先建立 reader 事务并通过 `SELECT count(*)` 固定初始 snapshot，然后等待短龄或长龄间隔，执行相同的 24 次提交、每次 10 行（合计 240 行），reader 在唯一一次 `PRAGMA wal_checkpoint(PASSIVE)` 时仍活动。

12/12 配对在数据库设置、snapshot 构造、写入数、`log_frames` 与 WAL bytes 上匹配。两种条件所有运行均为 `log_frames=26`、checkpoint 前 WAL 文件 `107152` bytes、`checkpointed_frames=2`。每一配对的 Δ=长龄减短龄 `checkpointed_frames` 均为 0；负值 0 对，非负值 12 对，中位配对差 0 帧。实测 snapshot 至写入前等待时间：短龄 1.121–1.329 ms，长龄 100.733–105.035 ms。PASSIVE 调用耗时中位数：短龄 0.145 ms、长龄 0.452 ms；这是次要描述量，不作为帧数分类依据。

## 预定分类

观察结果满足冻结 outcome rule `no_age_penalty`：至少 10 个有效配对，且至少 10/12 配对 Δ≥0；实际为 12 个有效配对、12/12 非负。因此按冻结效果映射，结果对 B1 为 supports、对 C3 为 contradicts。这只是该局部轨迹和 SQLite build 上的实验分类，不是机制成立或新颖性结论。

## 与冻结方案的差异

计划没有指定固定写入 burst 的大小、表结构或 SQL。本执行采用 E02 已使用的轻量模式作为工程解析：24 次事务提交、每次插入 10 行，共 240 行；字段为 TEXT，固定 SQL `INSERT INTO sample(value) VALUES (?)`。同时将“固定同步设置”具体化为 `synchronous=NORMAL`。这些选择在本次实验前固定并对所有条件一致执行，没有依据本实验结果调整输入或分类阈值。其余计划项均执行：指定种子 20261116–20261127、每种子以 `random.Random(seed)` 决定短/长顺序、fresh DB、一次 PASSIVE、配对不匹配则无效。无无效配对。

## 限制

结果只检验一个小型、单 reader、固定 240 行突发及 SQLite 3.51.3 配置；不能推广到其他页布局、写入模式、build 或生产工作负载。两组 checkpoint 时均只推进 2/26 帧，显示活动 snapshot 对此执行点存在共同限制；结果未检验多种 snapshot 位置。调用时间受本地计时噪声影响，且非主要测量。数据库为新建临时数据库，未测试并发 writer 或生产存储。

## 可复现文件

- `run_e03.py`：实验执行与冻结规则计算代码。
- `raw_trials.json`：随机顺序和 24 个逐次真实测量。
- `classification.json`：逐对有效性、Δ、中位数、方向计数及分类计算。
