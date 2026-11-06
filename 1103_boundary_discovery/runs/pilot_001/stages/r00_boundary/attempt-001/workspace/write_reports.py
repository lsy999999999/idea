#!/usr/bin/env python3
"""Render compact tables and the Chinese boundary report from the saved audit."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
d = json.loads((ROOT / "coverage_audit.json").read_text(encoding="utf-8"))

with (ROOT / "coverage_by_site_year.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["site_no", "year", "calendar_days", "water_mean_days", "water_max_days", "flow_mean_days", "water_flow_days", "water_flow_air_matched_days", "water_coverage_fraction", "flow_coverage_fraction", "paired_coverage_fraction", "water_qualifiers"])
    for s in d["daily_values"]:
        air = d["paired_daily_air_water_flow"][s["site_no"]]["matched_days_by_year"]
        for year, y in s["by_year"].items():
            w.writerow([s["site_no"], year, y["expected_calendar_days"], y["water_mean_days"], y["water_max_days"], y["flow_mean_days"], y["water_flow_paired_days"], air.get(year, 0), y["water_mean_coverage_fraction"], y["flow_coverage_fraction"], y["paired_coverage_fraction"], ";".join(y["water_qualification_codes"])])

with (ROOT / "coverage_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["site_no", "station", "water_daily_first", "water_daily_last", "water_daily_valid_days", "flow_daily_first", "flow_daily_last", "flow_daily_valid_days", "water_flow_paired_days", "air_station_id", "air_station_distance_km", "water_flow_air_matched_days", "matched_first", "matched_last", "years_2014_2024_with_at_least_350_matched_days", "IV_2020_water_points", "IV_2020_wallclock_duplicate_timestamps", "IV_2020_max_wallclock_gap_seconds"])
    for s in d["daily_values"]:
        site = s["site_no"]
        meta = next(x for x in d["site_metadata"] if x["site_no"] == site)
        pair = d["paired_daily_air_water_flow"][site]
        iv = next(x for x in d["instantaneous_2020"] if x["site_no"] == site)["nonempty_series"][0]
        n_years = sum(pair["matched_days_by_year"].get(str(y), 0) >= 350 for y in range(2014, 2025))
        w.writerow([site, meta["station_nm"], s["water_mean_first"], s["water_mean_last"], s["water_mean_days"], s["flow_mean_first"], s["flow_mean_last"], s["flow_mean_days"], s["paired_daily_days"], pair["air_station_id"], pair["air_station_distance_km"], pair["matched_days"], pair["first_day"], pair["last_day"], n_years, iv["n"], iv["duplicate_wallclock_timestamps"], iv["max_interval_seconds"]])

report = f"""# 河温候选边界审计

检索时间：2026-11-03，UTC；每个逐站请求的实际 UTC 时间、URL、HTTP 状态、字节数与 SHA-256 见 `coverage_audit.json`。本阶段只检查数据可用性和测量条件，没有拟合或执行候选预测实验。

## 选择规则

从先前样本审计的 3 个 USGS 站点出发，取实时 Oregon 活跃 stream 水温站查询（`stateCd=OR, parameterCd=00010, siteType=ST, siteStatus=active`）中的交集，不按观察结果增删站点。该清单返回 349 条、349 个不同站号，3 个种子站全部在列。选择出的站点是 10396000、11501000、11502500。

## 实际观测

| USGS 站 | 水温日均值可见范围与有效天 | 流量日均值范围与有效天 | 水温+流量同期天 | NOAA 气温配对代理 | 2014–2024 每年至少 350 个三源配对日 | 2020 瞬时水温点 |
|---|---|---|---:|---|---:|---:|
| 10396000 | {d['daily_values'][0]['water_mean_first']} 至 {d['daily_values'][0]['water_mean_last']}；{d['daily_values'][0]['water_mean_days']} 天 | {d['daily_values'][0]['flow_mean_first']} 至 {d['daily_values'][0]['flow_mean_last']}；{d['daily_values'][0]['flow_mean_days']} 天 | {d['daily_values'][0]['paired_daily_days']} | USR0000OPHI，6.85 km | {sum(d['paired_daily_air_water_flow']['10396000']['matched_days_by_year'].get(str(y),0)>=350 for y in range(2014,2025))}/11 | {d['instantaneous_2020'][0]['nonempty_series'][0]['n']} |
| 11501000 | {d['daily_values'][1]['water_mean_first']} 至 {d['daily_values'][1]['water_mean_last']}；{d['daily_values'][1]['water_mean_days']} 天 | {d['daily_values'][1]['flow_mean_first']} 至 {d['daily_values'][1]['flow_mean_last']}；{d['daily_values'][1]['flow_mean_days']} 天 | {d['daily_values'][1]['paired_daily_days']} | USR0000OCHI，3.80 km | {sum(d['paired_daily_air_water_flow']['11501000']['matched_days_by_year'].get(str(y),0)>=350 for y in range(2014,2025))}/11 | {d['instantaneous_2020'][1]['nonempty_series'][0]['n']} |
| 11502500 | {d['daily_values'][2]['water_mean_first']} 至 {d['daily_values'][2]['water_mean_last']}；{d['daily_values'][2]['water_mean_days']} 天 | {d['daily_values'][2]['flow_mean_first']} 至 {d['daily_values'][2]['flow_mean_last']}；{d['daily_values'][2]['flow_mean_days']} 天 | {d['daily_values'][2]['paired_daily_days']} | USR0000OCHI，1.80 km | {sum(d['paired_daily_air_water_flow']['11502500']['matched_days_by_year'].get(str(y),0)>=350 for y in range(2014,2025))}/11 | {d['instantaneous_2020'][2]['nonempty_series'][0]['n']} |

逐年三源交集、水温和流量覆盖比例见 `coverage_by_site_year.csv`。在候选的连续现代时期中，2014–2024 的流量日均值覆盖完整；但水温有小缺口，例如 10396000 在 2016 年缺 41 天，11501000 在 2017/2022 年有缺测，11502500 在 2014–2024 大多完整。水温起始年之前仅有流量，没有可用于水温事件恢复的记录。USGS 在 2026 年返回的当前年数据是部分年份；不能把 2026 年与完整年比较。

2020 瞬时记录的间隔主体为 900 秒（15 分钟）。2020 年点数分别为 35136、35117、35111；`10396000` 达到闰年 15 分钟完整格点数，另两站各少 19 与 25 个点。三条序列都出现 4 个重复本地墙钟时间，来自夏令时回拨时本地时间戳未携带 UTC offset；相邻差分最大为 4500 秒，故需按 America/Los_Angeles 夏令时正确解析后再界定真实断档。请求 `parameterCd=00010,00020` 只返回水温系列，没有站点级气温瞬时序列。流量日值可与水温日值直接按日期配对；近邻 NOAA GHCN 日 TMAX/TMIN 也已按日期交集核对，但只是空间代理，不等于河岸同点气温。

## 元数据与测量边界

当前 USGS expanded site metadata 给出站名、坐标、河流汇水面积与 PST/本地夏令时标志；本次快照的 `inventory_dt` 为空。长时间日值响应里每站对应一个水温 IV_TS_ID（116483、116505、116513）及一个日值序列 ID，但单一 ID 不能证明整个时期探头、安装位置、校准或汇总算法没有变化。当前站点元数据不是历史变更日志，因此历史传感器/站点变化尚未核实。

USGS 日值含已批准(A)、临时(P)及估算(e)限定符；流量中存在 `A:e`/`P:e`。最新 2026 值为临时值，历史数据可被修订。NOAA GHCN 清单把近站 USR0000OPHI 与 USR0000OCHI 的 TMAX/TMIN 年限列为止于 2023 年，但抓取到的 `.dly` 原文件含 2024–2025 日期。这是可复现的目录元数据与文件内容冲突；2023 年后气温配对应冻结为待核验，不能直接当作无疑义测试数据。气象站距离、海拔、暴露和观测规范差异也可能引入代表性误差。

## 进入后续检验的判断

- **可进入的准备范围**：三个站的日尺度描述性联合覆盖可用于列出事件候选期；2014–2024 是相对重叠较好的开发窗口。跨站/时间外测试的数据底座在日尺度上可行，但本站只有 3 个选择性种子样本，不能代表 Oregon 的总体。
- **尚不应进入的检验**：原候选是热事件后的恢复轨迹与下一事件之间的预测信息，需要事件级高频序列。此处只做了 2020 一年瞬时水温全年的初审，并未证明 2014–2024 各年都有连续高频水温与稳定观测方法；因此现有证据不足以批准留整站或时间外的恢复曲线预测检验。
- **不支持的主张**：任何水温预测增益或新的热惯性/地下水机制。本阶段没有估计这些量，且气温代理和历史探头元数据有上述限制。

## 建议的下一步

先做非建模的多年份 IV 补充审计：对 3 个站逐年（优先 2014–2025 暖季）取水温瞬时序列元数据/小窗口样本，统计实际 15 分钟格点、连续可用天数、最大断档、夏令时处理及 IV_TS_ID/methodID 变更；同时向 USGS station record 和仪器/站点历史元数据核对探头更换。气温侧确认 GHCN `.dly` 与库存冲突，并冻结 NOAA 站选择规则和空间距离；流量侧记录估算限定符和是否以日均值对齐。随后预先规定训练/测试时间和事件阈值。

若至少两个以上站点在同一多年份时段有稳定的高频水温、逐日流量和可审计气温代理，再缩小为这些站点进入候选事件级检验；如果高频时序只在个别年份/单站可用，放弃“留站+时间外可迁移”主张，改成明确标注单站/单时期的描述性恢复分析，或停止该候选。

## 数据来源

- USGS Oregon 活跃站列表：`{d['requests'][0]['request_url']}`
- USGS 当前站点元数据：`{d['requests'][1]['request_url']}`
- USGS 水温日统计与流量日均值，2000-01-01 至 2026-11-02：`{d['requests'][2]['request_url']}`
- USGS 水温与气温参数瞬时值检查，2020-01-01 至 2020-12-31：`{d['requests'][3]['request_url']}`
- NOAA GHCN-Daily 完整站点清单：`{d['requests'][4]['request_url']}`；近邻站原始 `.dly` 文件 URL/检索时刻记录在 `coverage_audit.json`。
- 起点样本审计：`/Applications/ideas/1103_boundary_discovery/bootstrap/scout/evidence/usgs_sample_audit.json`。
"""
(ROOT / "coverage_report_zh.md").write_text(report, encoding="utf-8")

base = "runs/pilot_001/stages/r00_boundary/attempt-001/workspace/"
result = {
    "summary": "依据预先限定为三个种子站与实时 Oregon 活跃 stream 水温站交集的规则，完成 USGS 2000-2026 日值覆盖、2020 年瞬时采样检查、近邻 NOAA GHCN 气温文件检查及逐日三源日期交集。日尺度联合资料可进入事件候选期整理，但尚不足以批准原定的多年份高频恢复轨迹、留站与时间外预测检验；本阶段未拟合或预测。",
    "artifacts": [
        {"path": base + "coverage_report_zh.md", "description": "中文逐站适用性与测量风险报告。"},
        {"path": base + "coverage_summary.csv", "description": "逐站汇总覆盖表。"},
        {"path": base + "coverage_by_site_year.csv", "description": "逐年水温、流量及三源配对覆盖表。"},
        {"path": base + "coverage_audit.json", "description": "完整请求日志、URL、检索时间、响应哈希、站点/年度统计及气温逐日交集。"},
        {"path": base + "audit_coverage.py", "description": "抓取及统计脚本。"},
        {"path": base + "write_reports.py", "description": "从审计 JSON 生成报告及 CSV 的脚本。"},
        {"path": base + "data/", "description": "本次保存的 USGS RDB 与 NOAA 清单、近邻站原始 GHCN-Daily 文件。"}
    ],
    "evidence": [
        {"type": "observation", "source": "coverage_audit.json:selection", "detail": "活跃 Oregon 水温 stream 清单返回 349 个唯一站号；三个样本站均入选。", "interpretation": "站点子集是种子样本与指定实时清单的交集，不是随机或总体代表样本。"},
        {"type": "observation", "source": "coverage_summary.csv; coverage_by_site_year.csv", "detail": "水温日均值起始日分别为 2010-10-14、2005-04-28、2007-10-17；流量日均值从 2000-01-01 到 2026-11-02 每日均有记录。", "interpretation": "日尺度下存在可用多年重叠，但较早时段不能用于水温分析，个别年份仍有日缺测。"},
        {"type": "observation", "source": "coverage_audit.json:paired_daily_air_water_flow", "detail": "将 USGS 水温日均值、流量日均值与最近 NOAA 站 TMAX/TMIN 按日期逐日交集；配对总日数及逐年数量已保存。最近代理站距离为 1.8-6.85 km。", "interpretation": "满足日期同步的初步条件，但 NOAA 站的空间代表性和目录/文件年份冲突限制协变量可靠性。"},
        {"type": "observation", "source": "data/usgs_iv_water_and_air_2020.rdb", "detail": "2020 瞬时水温返回 35136、35117、35111 点，间隔主体为 900 秒；三站各有 4 个重复本地墙钟时间，最多相邻间隔 4500 秒。请求 parameterCd=00010,00020 仅返回 00010 水温系列。", "interpretation": "确认单年高频水温可访问，未确认更长时期高频记录或站点级瞬时气温；回拨时间需用带时区解析。"},
        {"type": "observation", "source": "coverage_audit.json:ghcn_daily_air_temperature_coverage and data/noaa_ghcnd_inventory.txt", "detail": "NOAA 清单将 USR0000OPHI 和 USR0000OCHI 的 TMAX/TMIN 列到 2023 年，实际下载的 .dly 文件记录含 2024-2025 年。", "interpretation": "文件数据与目录元数据冲突，2023 年后的气温记录暂不作为无争议验证数据。"},
        {"type": "observation", "source": "data/usgs_daily_values_2000_to_2026.rdb", "detail": "日值表含 A/P/e 资格码，三个站均存在估算流量限定符；单个水温 IV_TS_ID 分别为 116483、116505、116513。", "interpretation": "限定符须纳入过滤/敏感性方案；一个当前序列 ID 不能证实历史传感器或汇总方法未变化。"}
    ],
    "claims": [
        {"claim": "2014-2024 在这三个站的日尺度上大体具备水温、流量及 NOAA 近邻气温代理的可配对观察，可作为列举事件候选窗口的开发数据。", "status": "bounded_observation", "not_claimed": "没有证明事件级高频水温多年份完整，也没有验证预测增益。"},
        {"claim": "目前证据不足以支撑原计划的留整站和时间外恢复轨迹预测实验。", "status": "interpretation", "basis": "除 2020 年外尚未审计瞬时水温多年覆盖；三站样本小；历史传感器变化未核实；气温代理有元数据冲突。"}
    ],
    "limitations": [
        "USGS 高频温度仅对 2020 全年做了直接覆盖核查；其它年份的日统计不代表 15 分钟连续性。",
        "USGS 当前 expanded site metadata 没有提供本审计所需的历史探头更换/位置变化日志；IV_TS_ID 稳定不等于传感器稳定。",
        "气温来自邻近 NOAA 站，非河岸原位测量；最近站 `.dly` 与 NOAA 清单的年份范围存在差异。",
        "USGS 记录有 provisional、estimated 数据标记；日汇总掩盖日内峰值与恢复曲线。",
        "三站源于样本审计，不是代表 Oregon 活跃站的概率样本；站点留出只有极少数折。"
    ],
    "next_actions": [
        "不拟合预测模型。先对 2014-2025 暖季做逐年 USGS IV 高频温度数据可用性、缺测/最长断档、DST 对齐和 IV_TS_ID/methodID 变化审计。",
        "获取并核实 USGS 探头/站点历史记录；冻结 NOAA 配对站与年份规则，解释 GHCN inventory 与 .dly 文件的 2024-2025 差异。",
        "若两个以上站在共同多年窗口满足高频温度、可配对流量、可靠气温和可追踪仪器记录，再预先注册时间外/留站事件测试；否则缩为单站单期描述性分析或放弃候选。"
    ]
}
(ROOT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
