"""Encode the organizer's explicit, nonblind post-run judgments, not a model judge."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import harness as h

# Each entry is an authored semantic judgment: Chinese gloss, family, rationale.
LABELS = {
 'education_1': [
  ('缺勤负担是否调节补习邀请的收益', 'E_ATTENDANCE_SUPPORT', '明确补习邀请×事前缺勤交互；目前只能检查未定时代理关联。'),
  ('低早期成绩预警与后续恶化预警是否覆盖不同学生', 'E_GRADE_ALERT', '有具体预警规则比较和后续需求检查，但集合不重合这一预测很弱。'),
  ('长通勤学生是否更受益于交通／出勤支持', 'E_COMMUTE_SUPPORT', '增加通勤—出勤路径及随机服务邀请；现有表只可检查首段关联。')],
 'education_2': [
  ('高缺勤学生应接受出勤补救还是等时补习', 'E_ATTENDANCE_SUPPORT', '比较两种支持包及缺勤调节，和上一重复属于同一配置思路，有不同处理对比。'),
  ('学生需求访谈能否改善支持匹配与成绩', 'E_BARRIER_ROUTING', '新增障碍测量、路由干预、接受率与成绩终点。'),
  ('等时检索练习能否优于增加自主学习', 'E_RETRIEVAL_PRACTICE', '具体学习策略随机对比；世界文献已有检索练习方向，本轮未作专门检索。')],
 'energy_1': [
  ('持续高用电之后的房间温升是否可作监测信号', 'N_THERMAL_LOAD', '初始假说和滞后／先行安慰剂可区分；后续代码错误另记，不倒改L1评分。'),
  ('室内外热响应时滞能否触发通风检查', 'N_VENTILATION', '明确新增通风状态标签验证，现有温度序列只支持探索。'),
  ('反复夜间底载能否触发可控待机负载审计', 'N_STANDBY_AUDIT', '明确筛查—插座测量闭环；未把熄灯直接当成无人。')],
 'energy_2': [
  ('用高负载触发分回路计量提高等预算观测收益', 'N_EVENT_METERING', '增加主动测量安排和等预算随机比较，R1随后纠正为下一时段触发。'),
  ('房间热恢复能否指示需检查的通风状态', 'N_VENTILATION', '与energy_1 I2同族；给出直接换气测量和控制条件。'),
  ('负载事件后的反馈能否减少后续用电而维持舒适', 'N_TIMED_FEEDBACK', '随机消息时机、后续Wh、舒适与反弹均有定义；题名occupancy与正文不完全一致。')],
 'environment_1': [
  ('风向状态转变是否缩短高污染持续时间', 'V_WIND_CLEARANCE', '新增事件终点和六小时持续概率；Iws为累计量，不能直接解释为瞬时风速。'),
  ('污染缺测是否集中于过程边界', 'V_BOUNDARY_MISSINGNESS', '有边界窗口缺测比较和事件计数敏感性，不仅是一般缺失警告。'),
  ('记录的雨雪过程是否增加污染消散信息', 'V_WET_CLEARANCE', '新增湿天气与次时段浓度变化比较；需保留累计字段解释。')],
 'environment_2': [
  ('风向转变是否增添污染清除的预测信息', 'V_WIND_CLEARANCE', '与environment_1 I1同族，条件和终点更严格。'),
  ('记录的降雨开始是否伴随污染衰减', 'V_WET_CLEARANCE', '与environment_1 I3同族；累计雨时增量需核对测量含义。'),
  ('潮湿与低累计风量是否共同增强污染持续性', 'V_HUMID_STAGNATION', '明确露点差×Iws交互及独立时间块预测检查。')],
 'health_1': [
  ('个人持续语音偏移能否触发有价值的临床复评', 'H_PERSISTENT_ALERT', '固定警报预算与实际临床访视锚点；承认插值分数无法验证临床效用。'),
  ('标准化录音能否分离录音条件与疾病语音变化', 'H_RECORDING_CONTEXT', '同日配对录音与条件标注、重复性和独立临床方向比较均具体。'),
  ('降低录音频率能否保持变化检测延迟', 'H_SAMPLING_CADENCE', '明确负担—延迟比较；语音偏移与临床变化分别验收。')],
 'health_2': [
  ('三次同任务录音均值能否改进固定误报率下的变化警报', 'H_REPLICATE_ALERT', '新增重复采样设计，要求真实会话和独立临床标签。'),
  ('语音能否区分用药ON／OFF与长期进展', 'H_MEDICATION_STATE', '明确配对用药状态及参与者留出检验，所需用药数据另采。'),
  ('日内语音变异能否提高等负担症状回访命中率', 'H_VARIABILITY_CHECKIN', '新增症状日记和变异触发与固定回访对比。')],
 'materials_1': [
  ('掺合料比例是否改变可用强度的达到年龄', 'M_BINDER_AGE', '龄期×组成及工程阈值年龄比较，配方复现与独立批次明确区分。'),
  ('固定胶凝组成下减水与增塑剂能否维持强度及工作性', 'M_WATER_ADMIXTURE', '有水胶比／外加剂操作和强度非劣比较，工作性需新增。'),
  ('强度合格决策需要多少独立批次', 'M_BATCH_RELIABILITY', '具体阈值误分与批次方差设计；属于常规试验规划，尚无新颖性证据。')],
 'materials_2': [
  ('不同胶凝体系是否需要分别校准7天对28天强度的判断', 'M_BINDER_AGE', '明确早强比例和可比强度范围，与materials_1 I1同族。'),
  ('胶凝体系是否改变最早采样合格年龄', 'M_BINDER_AGE', '同一强度发展族的阈值表述，和materials_1 I1高度接近。'),
  ('相同早期强度下组成能否区分后续增长', 'M_BINDER_AGE', '同一强度发展族的预测表述；三条并非三个独立核心方向。')],
 'transport_1': [
  ('恶劣天气是否对临时用户的租车量影响更大', 'T_WEATHER_SEGMENT', '明确用户类别×天气及日时段的描述比较，计数与潜在需求区分。'),
  ('天气响应是否存在超出当前信息的小时滞后', 'T_WEATHER_LAG', '问题要检验滞后增量，预测却预期几乎没有增量，并把无增量列为失败，未统一研究假说方向。'),
  ('工作日通勤时段是否更受天气影响', 'T_WEATHER_DAYPART', '明确工作日×小时的天气关联异质性，和用户类别比较有不同主对比。')],
 'transport_2': [
  ('不同用户与运营时段是否需要不同天气响应策略', 'T_WEATHER_SEGMENT', '与transport_1 I1同族；增加三重对比，尚未证明运营政策收益。'),
  ('两年租车增长集中于通勤会员还是休闲临时用户', 'T_YEAR_GROWTH', '有标准化年份×用户×时段增长分解和明确反例。'),
  ('温湿组合是否比单独温度更能区分用户需求响应', 'T_HEAT_HUMIDITY', '明确温湿交互、用户构成、日期留出与温度单项基线。')],
}

FINAL_NOTES = {
 'education_1': ('保留并细化试验', '关联不确定', '0.678等级分，区间[-0.275,1.631]；不能估计补习邀请效应。'),
 'education_2': ('改变估计目标与支持包协议', '招募可行性', '157个G1<10记录；只检查人数和代理分层，不检验处理效应。'),
 'energy_1': ('根据错误零事件结果改暴露', '计算语义错误', '微秒时间戳与纳秒整数比较；零事件理由错误，最终孤立尖峰版未计算。'),
 'energy_2': ('纠正为t+1触发并明确分母', '局部描述支持', '697个触发时段中高负载占72.88%，等预算随机安排22.91%；无回路归因证据。'),
 'environment_1': ('负面／不确定结果，最终字段为空', '关联不确定', '71匹配对，差-0.0141，区间[-0.1408,0.1250]；final_idea=null。'),
 'environment_2': ('放弃入段时特征，改为过程中变化', '原方向不获支持；修订未计算', '加入入段风向转变使留年Brier从0.08953变0.08999；新风险集方案未计算。'),
 'health_1': ('明确个人基线与警报预算', '纯方案', '没有真实临床访视锚点；主动未请求不相关临床验证计算。'),
 'health_2': ('明确重复录音与参与者留出', '采样密度可行性', '日内相邻行对数不是同会话重复或临床有效性。'),
 'materials_1': ('收窄为工程阈值和独立批次', '部分局部描述支持', '7→28及28→56天增长方向符合预期；1→7天只有两组且全为零掺合料，阈值年龄未检验。'),
 'materials_2': ('加入批次和合格误分决策', '局部描述支持', '早强比例差-0.1131，区间[-0.1589,-0.0582]；配方级且范围限制并非充分匹配。'),
 'transport_1': ('收窄时段并重定义天气对比', '局部描述支持', '用户天气对比-0.1555，区间[-0.2628,-0.0790]；观测计数，非政策效果。'),
 'transport_2': ('固定通勤／休闲代理和三重对比', '关联不确定', '三重对比-0.1296，区间[-0.3686,0.1240]；第4类天气只有2行。'),
}


def main():
    initial, final, source_sets = [], [], []
    for name, entries in LABELS.items():
        run = ROOT / 'runs' / name
        s = h.state(run)
        first = s['replies'][0]['reply']
        for c, (gloss, family, reason) in zip(first['candidates'], entries):
            assert c['id'] == 'I' + str(entries.index((gloss, family, reason))+1)
            checks = dict(specific=1, input_increment=1, distinguishing_test=1,
                          coherent_feasible=int((name, c['id']) != ('transport_1', 'I2')))
            initial.append(dict(run=name, id=c['id'], title=c['title'], gloss=gloss,
                                family=family, checks=checks,
                                usable=all(checks.values()), rationale=reason,
                                frozen_source=str(run/'sealed_replies/L1.json'),
                                frozen_source_sha256=h.sha(run/'sealed_replies/L1.json')))
        f = s['final']
        populated = isinstance(f.get('final_idea'), dict)
        checks = dict(specific=int(populated), input_increment=int(populated),
                      distinguishing_test=int(populated),
                      coherent_feasible=int(populated and name != 'energy_1'))
        change, evidence, explanation = FINAL_NOTES[name]
        final.append(dict(run=name, initial_selected_id=first['selected_id'],
                          selected_family=entries[0][1],
                          model_status=f['status'], model_evidence=f['evidence_level'],
                          structured_candidate_present=populated,
                          checks=checks, usable=all(checks.values()),
                          change=change, reviewed_evidence=evidence, explanation=explanation,
                          original_final=f,
                          scoring_note=('缺少最终候选字段，叙述保留但不补写为完成候选。' if not populated
                              else '候选问题本身仍可研究；本轮计算解释及据此返工未通过连贯性验收。' if name=='energy_1'
                              else '达到候选标准，证据支持程度另列；新测量方案允许通过。')))
        for t in s['tools']:
            if t['type']=='search':
                source_sets.append(dict(run=name, query=t['request']['query'],
                                        sources=t['result'].get('sources',[])))
    pairs=[]
    for domain in sorted({x['run'].rsplit('_',1)[0] for x in final}):
        a,b=[x for x in final if x['run'].rsplit('_',1)[0]==domain]
        candidates=[x for x in initial if x['run'].rsplit('_',1)[0]==domain]
        pairs.append(dict(domain=domain, initial_candidates=6,
                          initial_usable=sum(x['usable'] for x in candidates),
                          initial_coarse_families=len({x['family'] for x in candidates}),
                          final_usable=int(a['usable'])+int(b['usable']),
                          selected_core_repeats=a['selected_family']==b['selected_family']))
    nearby={'materials_1','materials_2','transport_1','transport_2'}
    for s in source_sets:
        s['preliminary_novelty_label']='相近已知方向' if s['run'] in nearby else '资料不足'
        s['exact_world_novelty']='未判定'
    totals=dict(runs=12, initial_candidates=36, initial_usable=sum(x['usable'] for x in initial),
                initial_coarse_families=len({x['family'] for x in initial}),
                usable_initial_coarse_families=len({x['family'] for x in initial if x['usable']}),
                structured_final_candidates=sum(x['structured_candidate_present'] for x in final),
                final_usable=sum(x['usable'] for x in final),
                selected_coarse_families=len({x['selected_family'] for x in final}),
                usable_final_coarse_families=len({x['selected_family'] for x in final if x['usable']}),
                pairs_repeating_selected_core=sum(x['selected_core_repeats'] for x in pairs),
                selected_first_candidate=sum(x['initial_selected_id']=='I1' for x in final),
                generic_only_initial=sum(not x['checks']['specific'] or not x['checks']['input_increment'] for x in initial),
                role_searches=len(source_sets),
                returned_source_records=sum(len(x['sources']) for x in source_sets),
                with_abstract=sum(bool(v['original_abstract']) for x in source_sets for v in x['sources']))
    report=dict(time=h.now(), reviewer='Organizer, nonblind; no new model role calls',
                judgment_scope='Input-relative candidate quality and coarse semantic grouping; not world originality or causal discovery.',
                thresholds='PROTOCOL.md four binary criteria. Null final is not reconstructed; wrong computation-driven revision fails final coherence pending repair.',
                dedup_rule='Same domain relation/decision core belongs to one family despite thresholds, matching, age windows or wording. Families remain distinct across domains; shared abstract templates discussed in report.',
                totals=totals,domains=pairs,initial=initial,final=final,
                preliminary_literature=source_sets,
                limitations=['Manual nonblind judgments; borderline items could change under independent review.',
                             'Two repeats, familiar historical datasets, no single-model baseline.',
                             'Initial scores judge L1 proposals; downstream errors are not back-propagated.',
                             'Final scores combine candidate coherence and presence, not correctness of a new mechanism.',
                             'All source sets were requested for selected I1; unselected ideas have no dedicated novelty search.',
                             'No exhaustive or full-text originality search was performed.'])
    h.dump(ROOT/'review/SEMANTIC_REVIEW.json',report)
    lines=['# 36条初始idea目录与人工复核', '',
           '所有原文及修改分支仍保存在IDEA_LINES.md与冻结运行中。下表是组织者非盲的粗粒度分组；同族不等于完全相同，也不构成文献原创性裁决。', '',
           '|轮次|候选|中文概括|思路族|事前四项|复核理由|',
           '|---|---|---|---|---|---|']
    for x in initial:
        lines.append('|'+ '|'.join([x['run'],x['id'],x['gloss'],x['family'],
                                   ''.join(str(v) for v in x['checks'].values()),x['rationale']])+'|')
    lines += ['', '四位依次为具体性、输入增量、可区分性、连贯可行性。35/36达到候选标准；这不是35条原创发现。28个粗粒度初始思路族中27个至少有一条通过的候选。', '',
              '各轮最终字段11/12非空；纳入能源时间单位错误后，本轮完整可验收最终候选10/12。四个领域的两次主选同族，12次均选择I1。', '']
    h.dump(ROOT/'review/CANDIDATE_CATALOG.md','\n'.join(lines))
    print(json.dumps(dict(totals=totals,domains=pairs),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
