# 15分钟河温波形留年检验

## 状态

按冻结设计完成了可用站点的主要计算，但整体状态为**部分完成**：11502500 Williamson站指定的2023年IV输入实际为“ No sites found matching all criteria”，只有空的表头，无法计算留出目标。没有更换留出年；对该站2023以及Sprague-Williamson成对流量比预测均报告不可执行。其它两个站保留2023作为唯一测试年。

## 冻结设计和数据处理

预分析记录 [preanalysis.json](preanalysis.json) 在读取2023年原始IV数据前写入。拟合只使用2014-2022年5-9月，2024完全排除。逐站筛选A限定符、15分钟本地时间格、每天至少87个有效点；日温特征为一阶24小时谐波振幅A24、相位、实测极值时刻、跨午夜18:00-次日06:00的S_night和06:00-18:00的S_day。预测量由既存日面板按精确站号/日期连接，要求air_mean、air_range非缺失且日流量为正。两模型为月份+air_mean+log(flow)，以及再加air_range；分别逐站拟合、使用相同完整样本。测试差值为基线绝对误差减扩展模型绝对误差，正值代表扩展模型误差较低。区间采用测试年份内28日循环移动块bootstrap，2000次，固定种子20261103。

输入的15分钟温度文件来自 `runs/pilot_001/stages/r01_boundary/attempt-001/workspace/data/`，日协变量来自 `runs/pilot_001/parallel_exploration/paired_daily_panel.csv`。逐年筛选计数和逐日值见 [analysis_results.json](analysis_results.json) 与 [daily_diagnostics.csv](daily_diagnostics.csv)；逐日预测见 [heldout_predictions.csv](heldout_predictions.csv)。

## 观察结果

2023年有完整合格水温日及日面板配对的站点各153日：10396000与11501000。所有站2014-2022均有训练资料；训练可用日数因流量/气象缺失及斜率窗口不完整略有差异。

| 站点 | 目标 | 测试 MAE 基线 → 加 air_range | MAE改善 (°C) | 28日块95%区间 | 训练 air_range 斜率 |
|---|---|---:|---:|---:|---:|
| 10396000 | A24 | 0.633 → 0.580 | 0.0527 | [-0.0648, 0.1775] | +0.1675 |
| 10396000 | S_night | 0.1093 → 0.1076 | 0.0017 | [-0.0067, 0.0116] | -0.0105 |
| 10396000 | S_day | 0.1234 → 0.1127 | 0.0106 | [-0.0159, 0.0391] | +0.0370 |
| 11501000 | A24 | 0.4106 → 0.3618 | 0.0488 | [-0.0126, 0.1064] | +0.0994 |
| 11501000 | S_night | 0.0712 → 0.0700 | 0.0012 | [-0.0025, 0.0052] | -0.0066 |
| 11501000 | S_day | 0.0844 → 0.0732 | 0.0113 | [-0.0021, 0.0233] | +0.0228 |

两可用站的训练期条件斜率方向一致：air_range与A24正相关、与夜间斜率负相关、与白天斜率正相关。测试年点估计显示加入air_range对A24及S_day的MAE改善大于S_night；但所有28日块区间均跨0。该检验因此给出“预测有正向点估计但时间块不确定性较大”的结果，没有稳健证据支持夜间特异性强于白天的解释。这里的斜率是条件预测关联，不能解释为热交换机制或因果效应。

## 河网与竞争解释

2026-11-03查询USGS NLDI公开服务：`https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-11501000/navigation/DM/nwissite`（HTTP 200）。从Sprague站沿下游主河道导航返回11502500 Williamson below Sprague站；结果也返回“SPRAGUE RIVER ABOVE WILLIAMSON RIVER”以及“WILLIAMSON RIVER BLW SPRAGUE RIVER”相关河段/站点。保存的响应和抽取字段在 [network_check.json](network_check.json)。这支持地图河网中的上下游连通，但不能给出传播时延、流量闭合或纯支流份额。

尽管连通得到支持，11502500的2023 IV文件只有 `agency_cd, site_no, datetime` 空列，并含“ No sites found matching all criteria”。因此无法计算下游/上游A24比、圆周相位差，亦不能执行该竞争模型的留年检验。流量比可能受中间来水、取水、储存与测量时点影响，不能直接叫支流混合比例。文件证据保留在原始只读输入，未改写。

## 暴露、边界与下一步

2023不是项目层面未接触的新年份：已有项目逐日温度/气象/流量面板及先前日尺度预测/复核涵盖2023（见 `runs/pilot_001/parallel_exploration/paired_daily_panel.csv`、`runs/pilot_001/stages/r02_skeptic/attempt-001/workspace/recomputed_results.json`、`runs/pilot_001/stages/r04_skeptic/attempt-001/workspace/independent_results.json`）。本轮在查看2023高频IV测试目标之前保存了变量、筛选和模型设计，但没有在冻结文件中写出明确的系数符号预言，因此方向结果仅作描述，不能称为方向预注册检验。

日气温均值/幅度是站点日摘要，不含逐时辐射、遮阴、河岸微气候或能量通量；USGS IV可能是临时数据。块bootstrap仅反映这两站已观测测试季的时间序列不确定性，不代表站点总体不确定性。2024只用于既有探索线索，不进入本次训练、调参或确认。

最有信息量的下一步是查明11502500在2023年瞬时温度序列为何无站点返回，确认是否为请求参数/站点系列覆盖问题；若能从公开USGS服务取得原定2023记录，应先保留原冻结设计和此次失败版本，再在新版本执行完整三站测试以及同日流量比预测。之后应以未来未接触年份或独立连通河系检验，并补充亚日气象/辐射观测，才能区分一般预测关联与热交换解释。当前结果不支持新颖性主张。
