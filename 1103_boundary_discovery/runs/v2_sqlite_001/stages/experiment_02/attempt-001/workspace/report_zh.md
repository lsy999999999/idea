# E04 实验报告

## 执行与观察

按冻结计划 E04 执行了 12 个固定种子（20261128–20261139），每个种子包含 early、mid、late 三种条件，条件次序由对应 seed 初始化的 RNG 打乱。共完成 36 次真实 SQLite fresh-DB 运行，SQLite 版本为 3.51.3。数据库设置为 page_size=4096、WAL、synchronous=NORMAL、wal_autocheckpoint=0；每次均执行 24 个提交、每次插入 10 行，总计 240 行。reader 分别在第 0、12、23 批提交后建立 snapshot，并在单次 PASSIVE checkpoint 时保持活动。

12/12 个种子满足全部有效性条件：设置相同、snapshot 前缀和可见行数正确、reader 活动、最终 log_frames 相同且 checkpoint 前 WAL 字节数相同。三条件的 log_frames 均为 26，checkpoint 前 WAL 均为 107152 bytes，PASSIVE 的 busy 均为 0。每个种子的 checkpointed_frames 都是 early=2、mid=14、late=25；late−early 均为 23。checkpoint 调用时间中位数为 0.052333 ms，范围为 0.039667–0.328833 ms。

## 冻结分类

实际数字满足冻结 outcome rule `position_order`：12/12 个有效种子均有 late > early（规则要求至少 10/12），且 12/12 个 mid >= early（规则要求至少 10/12）。`position_flat` 未满足（0/12 三条件相等）。按冻结 effect mapping，这一观察映射为 D1 supports、D2 contradicts；这是该具体 SQLite build 与 240 行轨迹中的结果，不构成一般机制证明或新颖性证据。

## 方案差异与限制

没有偏离冻结计划的种子、条件、重复数、数据库参数、读者前缀、检查点调用次数或判定阈值。计划要求固定 SQL/schema/数据形状，但未在 E04 文件重述其字面细节；为保持与 E03 同一轨迹，沿用 E03 已记录的 `sample(id INTEGER PRIMARY KEY, value TEXT)` 和 `INSERT INTO sample(value) VALUES (?)`，每批数据值采用 `batch:row`。不补抽种子，也未依据结果改变规则。

结论限于 Python sqlite3 所链接的 SQLite 3.51.3、本地单 writer、单 reader、给定表与批次轨迹。checkpoint 耗时只作描述性报告。WAL 文件大小保持 107152 bytes 是文件长度观察，不代表各条件 checkpointed_frames 相同或不同。实验不评价并发服务延迟、其他数据库布局、读者数或工作负载，也不声称世界新颖性。
