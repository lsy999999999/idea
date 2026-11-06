# 五项审查问题的修复与验证

2026-11-05。对应 [open-inquiry-v2 审查记录](reviews/open_inquiry_v2_20261105_review/REVIEW_CN.md)。五项问题均已修复，当前入口仍为 `fish_inquiry.py`。新增验证保存在 `fix_checks_20261105/`，原审查复现和修复前实现快照保留。

| 问题 | 修复后的行为 |
| --- | --- |
| 核查笔记漏掉间接来源 | `note_dependencies.py` 展开被查主张的全部上游 `depends_on`、核查报告实际引用证据，以及已审核旧笔记的终端来源。取回时重新应用当前任务日期。2007/2008 年来源不会再以“仅测量数据”身份进入 2000 年前任务。 |
| 旧纠正笔记续写失败 | 从取回包继承旧报告的审核闭包，并保留其引用。依赖在持久化前检查；同键修订不能丢弃旧纠正报告。`admission.json` 记录已接纳内容，中断恢复不会重复调用模型或增加重复笔记版本。 |
| 默认计算轴错误 | `diff` 包装函数默认 `axis=0`；`norm` 默认 `axis=-1`，均支持显式覆盖。接口执行与研究者协议一致。 |
| 最终评价绕过统一 checker | `final_evaluation.py` 在生成冻结后调用公共 `CHECKER_PROMPT` 和 `validate_checks(require_claims=True)`，独立检索，返回完整六维、逐主张、时间／可见性及任务结论。无来源／无核心主张不能获得完整覆盖结论。 |
| 无摘要时跳过可读全文 | 来源身份及日期筛选与内容可读性筛选分开。摘要为空仍尝试符合条件的 PMC 正文；日期越界、正文 DOI 不匹配或含被排除来源时仍拒绝。 |

## 时间与来源可见性

鱼类任务继续使用批准的 **2010-01-01 之前**知识边界。最终 checker 的参考日期明确带 `evidence_kind: task_configuration`，引用本地任务配置，并说明这不是来源论文发表日期。该类型只能用于参考时间，不能用作某篇文献的发表日期。

控制器在冻结后生成 `evaluation/generation_exposure.json`，记录生成提示词、工具审计和来源策略检查。满足检查时记录来源 idea 在供应材料中隐藏；检查不完整时记未知。匹配隐藏来源的 idea 可以记为 `INDEPENDENT_REDISCOVERY`；后续论文单独比较。评价端可以检索来源论文及后续文献，评价材料不会进入生成记忆。

生成阶段继续通过受控 broker 补学；最终评价使用独立的 `evaluation/` 工作目录和公共运行器，支持真实检索。`ACCEPTED_CHECK.json` 保存输入／结果哈希，通过校验的最终报告可直接复用。

## 验证结果

**96 项离线测试通过：**历史入口 63 项（原 47 项加本次 16 项回归）、既有学习／记忆交接 11 项、公共 checker 时间与可见性 22 项。

新回归涵盖真实旧纠正笔记的取回、续写和再次取回；上游及核查引用来源在更早截止日期下被排除；未核实依赖在提交前失败；中断恢复；旧版不完整审核证明隔离；默认时间／向量轴；无摘要全文获取与身份／日期筛选；冻结后调用公共 checker；空覆盖证据拒绝；隐藏来源完全匹配；未知暴露；实验参考日期不得冒用为文献发表日期。

另在真实 **R01 第 1000–1159 帧**运行 `norm(diff(positions))`，得到 `159 × 2` 的逐鱼位移数组，与 `np.linalg.norm(np.diff(positions, axis=0), axis=-1)` 逐项一致，缺失值一致。原始轨迹未修改。结果见 `fix_checks_20261105/ACTUAL_COMPUTE.json` 及 `actual_compute/`。

保护核对：**718 个既有文件哈希一致**，包括旧鱼类试跑 **205 个冻结文件**、旧入口及依赖代码、原持久记忆实现与已有记忆。结果见 `fix_checks_20261105/PRESERVATION_AUDIT.json`。

本次没有真实研究模型或网络调用；联网与最终评价交接使用可复现 fixture，真实轨迹计算使用原数据。新的完整科学探索尚未启动。

## 启动与兼容

修复改变了入口及依赖代码，使用新的运行 ID；旧运行不会被新版代码续写。源码冻结现在包含新依赖解析器、最终评价适配器和公共 checker／记忆／运行器依赖。

```bash
.venv/bin/python -u historical_inquiry/fish_inquiry.py \
  --config historical_inquiry/configs/fish_v2.json \
  --run-id inquiry_v2_fixed_001
```

复现回归测试：

```bash
.venv/bin/python -m unittest discover -s historical_inquiry -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s bootstrap -p 'test_novelty_scope.py' -v
```
