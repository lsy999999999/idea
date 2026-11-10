"""Validate frozen packets and, if present, summarize actual evaluator outputs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIMS = ['value','concept','generativity']

def load(name):
    return json.loads((ROOT / name).read_text())

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, data):
    (ROOT / name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

frozen = load('FROZEN_INPUTS.json')
checks = {'frozen_inputs_unchanged': all(digest(ROOT/p)==h for p,h in frozen.items())}
source = load('controller_only/source_manifest.json')
checks['source_unchanged'] = digest(Path(source['path'])) == source['sha256']
cases = load('controller_only/cases.json')
by_key = {c['key']:c for c in cases}
checks['unique_11_cases'] = len(by_key)==len(cases)==11
ratings = {}
errors = []
for repeat in ['r1','r2']:
    packet = load(repeat+'/packet.json')
    mapping = load('controller_only/'+repeat+'_mapping.json')
    checks[repeat+'_complete_mapping'] = len(mapping)==11 and set(mapping.values())==set(by_key) and set(mapping)=={p['id'] for p in packet}
    checks[repeat+'_text_preserved'] = all(p['text']==by_key[mapping[p['id']]]['text'] for p in packet)
    result_path = ROOT/repeat/'result.json'
    if not result_path.exists():
        continue
    result = load(repeat+'/result.json')
    evaluations = result['evaluations']
    if len(evaluations)!=11 or {e['id'] for e in evaluations}!=set(mapping):
        errors.append(repeat+': missing or duplicate candidate coverage')
    ratings[repeat]={}
    text_by_id={p['id']:p['text'] for p in packet}
    for e in evaluations:
        if e['id'] not in mapping:
            errors.append(repeat+': unknown ID')
            continue
        for dim in DIMS:
            v=e[dim]
            if v['score'] is not None and (type(v['score']) is not int or v['score'] not in range(4)):
                errors.append(repeat+': score outside rubric')
            if not v['quote'] or v['quote'] not in text_by_id[e['id']]:
                errors.append(repeat+': ungrounded quote '+e['id']+' '+dim)
            if not v['reason'].strip():
                errors.append(repeat+': empty reason')
        ratings[repeat][mapping[e['id']]]=e
    events_path=ROOT/repeat/'events.jsonl'
    tool_events=[]
    if events_path.exists():
        for line in events_path.read_text().splitlines():
            try:event=json.loads(line)
            except json.JSONDecodeError:continue
            item=event.get('item',{})
            if item.get('type') in ['command_execution','mcp_tool_call','web_search','file_change']:
                tool_events.append(item.get('type'))
    checks[repeat+'_no_observed_tool_calls']=not tool_events

comparisons=[]
design=load('controller_only/preregistered_checks.json')
for repeat,r in ratings.items():
    for kind,pairs in [('invariance',design['strict_invariance_pairs']),
                       ('content',design['content_sensitive_pairs']),
                       ('maturity',[design['maturity_non_penalty']])]:
        for a,b in pairs:
            if a not in r or b not in r:continue
            delta={dim:None if r[a][dim]['score'] is None or r[b][dim]['score'] is None else r[b][dim]['score']-r[a][dim]['score'] for dim in DIMS}
            used=['concept','generativity'] if kind=='content' else DIMS
            known=all(delta[d] is not None for d in used)
            passed=None if not known else (all(delta[d]==0 for d in used) if kind=='invariance' else all(delta[d]<0 for d in used) if kind=='content' else all(delta[d]>=0 for d in used))
            comparisons.append({'repeat':repeat,'kind':kind,'reference':a,'comparison':b,'comparison_minus_reference':delta,'passes_predeclared_rule':passed})
    if 'grand_wish' in r:
        value=r['grand_wish']['value']['score']
        comparisons.append({'repeat':repeat,'kind':'wish','score':value,
                            'passes_predeclared_rule':None if value is None else value<3})

agreement=[]
if len(ratings)==2:
    for key in by_key:
        for dim in DIMS:
            a=ratings['r1'][key][dim]['score']
            b=ratings['r2'][key][dim]['score']
            agreement.append({'key':key,'dimension':dim,'r1':a,'r2':b,'exact_match':a==b,
                              'absolute_difference':None if a is None or b is None else abs(a-b)})

if errors or not all(checks.values()):
    state='validation_failed'
elif len(ratings)==2:
    state='two_outputs_validated'
else:
    state='prepared_not_run' if not ratings else 'partial'
save('VALIDATION.json',{'state':state,'checks':checks,'errors':errors,'actual_evaluation_outputs':len(ratings),'comparisons':comparisons,'agreement':agreement})

labels={
 'idea_distance_transition':'原候选：距离转移','idea_history_prediction':'原候选：历史预测','idea_direction_similarity':'原候选：方向相似度',
 'analysis_request':'分析请求','directional_guess':'方向性猜测','structural_hypothesis':'阶段解释假说',
 'polished_equivalent':'同一假说：润色扩写','explicitly_unfinished':'同一假说：明确未完成',
 'question_equivalent':'同一假说：问句表达','mechanism_removed':'移除阶段解释','grand_wish':'宏大愿景'}
review=['# 三维 idea 评分小试评材料','',
 '日期：2026-11-06。状态：'+state+'。','',
 '本轮仅诊断评分量表：研究价值、概念内容、研究生成力各0—3分或未知，不计算总分、不删除候选、不修改冻结研究或研究者记忆。',
 '', '## 试评方法','',
 '- 3条冻结候选使用原文 idea 与 motivation 字段，隐去已知检查结果和运行过程。',
 '- 8条控制样例由当前控制器根据本聊天构造；不是原研究者的新发现。',
 '- 计划请求 GPT-6 Luna / low，两次独立新会话；同一模型的重复，不是两个独立模型或人类专家。',
 '- 每次会话含全部11条，打乱顺序并重新编号；不给样例标签、预期分数或配对关系。近似重复内容本身仍可被模型识别。',
 '- 预先固定：润色与问句改写三维分数应完全相同；明确未完成不应造成分数下降；增加阶段解释应提升概念内容及生成力；全部差值原样报告。',
 '- “未完成”样例还明说操作定义未选定，属于可能的措辞混杂，不能把差异全部归因为成熟度偏差。',
 '- 每项评分要求逐字引用自身候选、说明理由、列出未知项和下一步发展建议。建议不计入原文分数。',
 '', '## 当前执行状态','',
 '用户已于2026-11-06明确授权发送这11条材料并执行两次试评。早前自动审批拒绝记录保留；授权后实际CLI请求返回401 Unauthorized / INVALID_API_KEY。原生Luna评审作为同模型续接尝试单独记录。有效模型输出数量以VALIDATION.json为准。',
 '', '## 候选材料（本清单仅供用户和控制器查看）','']
for c in cases:
    review.extend(['### '+labels[c['key']], '', c['text'],''])
review += ['## 已完成本地校验','',
          f'- 实际模型输出：{len(ratings)} 份。',
          '- 原候选文件、量表、候选、盲化映射、预注册检查的冻结哈希均作校验。',
          '- 两次会话的候选覆盖和原文字段一致性均作校验。',
          '', '## 解释范围','',
          '即使本轮通过，也只支持此领域少量受控样例上的量表表现；不建立长期潜力真值、世界新颖性、排序策略有效性或跨领域通用性。']
(ROOT/'TRIAL_MATERIALS_CN.md').write_text('\n'.join(review)+'\n')
if ratings:
    save('RESULTS.json',{'ratings':ratings,'comparisons':comparisons,'agreement':agreement})
    report=['# 三维评分试评结果','', '状态：'+state+'。','',
            '分数顺序为：研究价值 / 概念内容 / 研究生成力。没有加权总分。','',
            '| 材料 | 会话1 | 会话2 |','|---|---|---|']
    for key in by_key:
        cells=[]
        for repeat in ['r1','r2']:
            cells.append(' / '.join(str(ratings[repeat][key][d]['score']) for d in DIMS) if repeat in ratings and key in ratings[repeat] else '未取得')
        report.append('| '+labels[key]+' | '+' | '.join(cells)+' |')
    report+=['','## 预先固定的检查','']
    for c in comparisons:
        report.append('- '+json.dumps(c,ensure_ascii=False))
    report+=['','## 重复一致性','',f'完全相同的逐维评分：{sum(a["exact_match"] for a in agreement)} / {len(agreement)}。',
             '', '## 范围','', '同一模型、单一领域、小量受控样例。不是世界新颖性检查，不建立长期潜力真值或研究调度有效性。原始评语见RESULTS.json。']
    review_path=ROOT/'CONTROLLER_REVIEW_CN.md'
    if review_path.exists():
        report+=['',review_path.read_text()]
    (ROOT/'RESULTS_CN.md').write_text('\n'.join(report)+'\n')
print(json.dumps({'state':state,'checks':checks,'errors':errors,'actual_outputs':len(ratings)},ensure_ascii=False))
