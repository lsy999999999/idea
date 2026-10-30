import json, re, html
from pathlib import Path

ROOT = Path(__file__).parent
S = ROOT / 'sources'
records = []
def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', s or ''))).strip()
def cross(stem, index=0):
    m = json.loads((S / (stem+'.json')).read_text())['message']
    a = m['items'][index] if 'items' in m else m
    date = a.get('published-print', a.get('published',{})).get('date-parts',[[]])[0]
    online = a.get('published-online',{}).get('date-parts',[[]])[0]
    display_date = '-'.join(map(str,date))
    if online and online != date:
        display_date = '-'.join(map(str,online)) + '（在线）；' + display_date + '（卷期）'
    return dict(title=clean(a.get('title',[''])[0]), doi=a.get('DOI'),
                journal='; '.join(a.get('container-title',[])),
                date=display_date, abstract=clean(a.get('abstract')),
                source_file=stem+'.json')
def epmc(stem, doi):
    a = next(a for a in json.loads((S/(stem+'.json')).read_text())['resultList']['result'] if a.get('doi')==doi)
    return dict(title=a['title'],doi=doi,journal=a.get('journalInfo',{}).get('journal',{}).get('title',''),
                date=a.get('firstPublicationDate',a.get('pubYear','')),abstract=clean(a.get('abstractText')),
                source_file=stem+'.json')
def add(a, level, kind, fact, use):
    a.update(id=f'P{len(records)+1:02}',reading_level=level,kind=kind,fact=fact,use=use)
    records.append(a)

add(cross('q_groundwater'),'摘要、正文关键段落、限制、数据说明','研究论文',
    '分析约17万口监测井和1,693个含水层系统；发现快速下降、加速下降及局部恢复，讨论监测不连续、空间不均和深度差异。',
    '支撑主动监测与管理问题；观测趋势本身不足以识别某项管理措施的因果效果。')
add(cross('q_flood'),'摘要、正文引言与数据/代码说明','研究论文',
    'AI在无测站流域的极端河流事件上，可将与既有全球系统即时预报相近或更好的可靠性提前到最多五天；提供回报数据。',
    '成熟预报能力为研究行动衔接提供基础；本文未直接证明本报告提出的救援agent有效。')
add(cross('q_conservation'),'Crossref与Europe PMC公开摘要交叉核对','元分析',
    '186项研究、665个试验；约三分之二案例中的保护行动改善生物多样性或减缓下降。',
    '保护干预可以用实际结果评价；总体效果不能直接保证任意本地措施有效。')
add(cross('q_policy'),'公开摘要','实证研究',
    '对41国1998—2022年的1,500项气候政策开展事后评估，识别63个有大幅减排效果的政策干预。',
    '启发政策组合及因果评价；63不是全部政策有效率的简单分子，识别阈值与方法影响结论。')
add(cross('q_carbon'),'公开摘要','实证研究',
    '采用合成控制研究六国26个避免毁林项目；多数未显著减少毁林，有效项目中的减少也低于申报。',
    '支撑额外性审计与反事实敏感性研究，不能泛化为所有碳项目均无效。')
add(cross('q_alab'),'当前更正版摘要、正文关键段落、数据说明，并读更正','研究论文',
    'A-Lab结合计算、文献、机器学习、主动学习与机器人；当前版本报告17天内实现57个目标中的36个化合物。',
    '展示实验闭环，且须与P25一起引用，不能继续沿用未更正的40个成功或笼统新材料说法。')
add(cross('q_coscientist'),'摘要和数据/代码说明','研究论文',
    'Coscientist结合LLM、检索、代码与实验自动化执行化学研究任务；论文的数据代码说明指出完整发布有限制，提供简化实现。',
    '实验编排已有先例；不能假定可以下载完全相同的端到端实现。')
add(cross('q_trial'),'摘要、讨论全文、评估范围','研究论文',
    'TrialGPT在183个合成患者和超过7.5万条试验标注上评价；小型用户研究报告筛选时间减少42.6%。',
    '匹配、排序和筛选效率已有先例；未据此证明实际入组率或临床结局提升。')
add(cross('q_virtual_lab'),'出版商公开摘要、图题和数据说明；正文付费','研究论文',
    'Virtual Lab组合多学科LLM角色，设计92个纳米抗体并做实验验证；两个设计显示针对特定变体改善的结合特征。',
    '展示跨领域协作与实验确认；不是人人可直接复用的一般科学发现保证。')
add(cross('q_farm'),'出版商公开摘要与图题；正文付费','研究论文',
    '2005—2015年中国约2,090万农户采纳改进管理，报告作物增产与氮肥减少；实践依赖本地试验和庞大推广网络。',
    '农业研究应同时考虑科学建议、本地适配、推广与实际采纳；该研究不是AI agent试验。')
add(cross('q_benefit',1),'公开研究摘要','随机田野试验',
    '约3万名可能符合SNAP资格的老年人随机分组，9个月参与率分别为6%、11%、18%；干预引入者较健康且收入较高。',
    '支持申请协助的重要性及分布效应；人工协助的效应不能直接归为AI效应。')
add(cross('q_supply_climate',2),'期刊最终版公开摘要、发表信息','实证金融研究',
    '供应商热暴露影响上下游经营收益；经历高于预期暴露时，客户更可能终止供应商关系。',
    '支持企业适应与供应链金融切口；期刊卷期2024，在线发表于2023-12-09，采用最终版而非早期工作论文数值。')
add(cross('q_supply_shocks',1),'期刊公开摘要','实证经济学研究',
    '自然灾害冲击沿供应链传导，特定投入品对应更强的客户产出及价值损失，并外溢至其他供应商。',
    '说明替代性约束应进入采购与现金流决策。')
add(cross('q_finance_credit',1),'期刊公开摘要、发表信息','实证与模型研究',
    '利用美国抵押贷款数据比较传统与机器学习预测，并在信用市场模型中分析分布效应；部分群体获益较少。',
    '金融应用的评价应包含分布效应；不可把预测改善直接等同于所有借款人福利改善。卷期2022、在线2021。')
add(epmc('epmc_amr','10.1016/s0140-6736(24)01867-1'),'Europe PMC详细结构化摘要；开放全文另已保存','全球负担估计与情景预测',
    '估计2021年细菌AMR直接归因死亡约114万、相关死亡约471万；不同年龄和地区趋势不同。',
    '支持监测与资源配置重要性；归因与相关不能混用，未来数字属于情景预测。')
add(epmc('epmc_rare','10.1056/nejmoa2314761'),'Europe PMC详细结构化摘要','多队列诊断研究',
    '对此前未诊断家庭进行全基因组分析；在既往外显子阴性但后来获诊断的家庭中，63.5%的变异可由外显子重分析或附加方法检出。',
    '支持旧数据重分析价值；63.5%的分母是特定已获诊断家庭，不能说63.5%的全部未诊断患者可被重分析诊断。')
add(cross('q_food'),'Crossref提供的编辑摘要与元数据','研究论文',
    '综合约3.8万农场、40种农产品的环境影响信息，指出相同食品的生产环境影响存在明显差异。',
    '支持采购中的生产者差异；粗粒度食品平均值不能替代具体供应商测量。')
add(cross('q_methane'),'公开摘要','观测与排放估计研究',
    '分析四个美国东南部大型填埋场2019—2023年卫星观测，估计排放平均高于其报告值，并讨论核算模型选择。',
    '提示监测与申报的交叉验证机会；四个场地估计不可泛化为所有填埋场。')
add(cross('q_water_quality',1),'公开Key Takeaways摘要','行业调查研究',
    '公用事业调查发现服务管线材料识别需组合核实手段，不同方法成本差异明显，替换的附带成本不可忽略。',
    '为水务主动调查与成本建模提供相邻实践证据。')
add(cross('q_water_recovery'),'摘要、引言关键段落、数据/代码说明','研究论文',
    '华北平原两千余口井的分析报告2020年以来平均约0.7米/年恢复，涉及调水、开采规定和湿年等共同条件。',
    '中国本地案例与数据入口；后续2026-10-30访问核验发现Zenodo记录受限，不能视为可匿名下载。不能把全部恢复单独归因某一项政策。')
add(epmc('epmc_flood','10.1126/sciadv.adu2865'),'公开摘要','灾害重建与模拟研究',
    '研究2023年Derna灾难，结合再分析、卫星和水文模型，指出水坝失败显著放大损害。',
    '预警—行动研究须包含基础设施；事后重建不等于灾前可知。')
add(epmc('epmc_nutrition','10.1016/j.cdnut.2026.107669'),'公开结构化摘要','膳食篮替代建模研究',
    '在英国基础食品篮中比较植物/真菌替代品的营养、环境和成本，发现选择不同产品会改变权衡。',
    '支撑多目标餐饮采购；属于模型替代实验，不能当作实际人群健康干预效果。')
add(epmc('epmc_wastewater','10.1080/22221751.2026.2731499'),'公开摘要','叙述性综述',
    '讨论污水信号的采样、环境、实验室和人群影响；纳入分析工作中多数针对SARS-CoV-2，跨任务预警证据有限。',
    '支撑主动采样与复检选题；不能假定对所有病原体都具有相同预警能力。')
add(dict(title='Biodiversity conservation has an evidence problem — it’s time to fix it',doi='10.1038/d41586-026-00309-1',journal='Nature',date='2026-02-04',source_file='bio_evidence.txt'),
    '评论正文','社论',
    '讨论生态保护证据质量、实践者可获取性、地区偏差及正在建设的AI证据工具。',
    '重要问题线索与相近工作入口；不是证明某个agent有效的实证研究。')
add(dict(title='Author Correction: An autonomous laboratory for the accelerated synthesis of inorganic materials',doi='10.1038/s41586-025-09992-y',journal='Nature',date='2026-01-19',source_file='alab_correction.txt'),
    '更正正文','正式更正',
    '复核原40项成功后确认36项，4项仅凭XRD不能定论；澄清材料新颖性，移除一项误入训练数据的化合物讨论。',
    '启发独立验证与补测研究；更正并未推翻自主实验的全部价值。')
add(cross('bio_existing'),'公开摘要与元数据','工作论文/预印本',
    '描述面向保护科学的持续证据数据库管线，包括筛选、提取、检索和人机协作；报告与既有人工综述的比较。',
    '证明持续文献整理不是空白；其性能属于预印本报告，不能当独立复现结论。')
add(cross('meta_biomni'),'期刊元数据与Europe PMC公开摘要','研究论文',
    'Biomni构建跨生物医学领域的工具环境，结合检索规划与代码执行，评估多种任务并给出研究案例。',
    '通用生物医学工具agent已有正式发表先例；摘要不能证明其覆盖本报告所有纵向任务。')
add(cross('meta_swmm_agent'),'期刊元数据与Europe PMC公开摘要','研究论文',
    'SWMM-Agentic操作已有雨洪模型；在Astlingen上测试60个任务和三种模型，展示静态、动态和情景任务。',
    '水务模型自然语言调用已有先例；候选题须进一步聚焦观测决策和领域结果。')
add(epmc('prior_rare_specific','10.1038/s41586-025-10097-9'),'Europe PMC公开摘要；出版商正文请求超时','研究论文',
    'DeepRare整合40余种工具及更新知识源，处理文本、表型和遗传检测等输入，评估多数据集罕见病鉴别诊断。',
    '罕见病诊断agent已有强先例，不能把工具编排或证据可追溯单独作为新颖性。')
add(cross('meta_marine_agent'),'公开摘要与元数据','概念框架预印本',
    '讨论将LLM嵌入海洋保护区设计和管理决策支持系统，强调整合碎片化专业知识以及共创。',
    '生态决策agent的总体构想已被提出；实证本地适配和干预收益仍需验证。')
add(epmc('prior_rare_specific','10.64898/2026.06.24.26356357'),'公开摘要','预印本',
    'RESCUE描述面向EHR的主动筛查和诊断升级支持流程，报告单机构回顾性筛查与人工病历复核。',
    '持续筛查也有相近工作；回顾性筛查性能不能等同前瞻诊断延迟改善。')

assert len(records)==31
assert len(set(a['doi'] for a in records))==31
(ROOT/'literature_catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
lines=['# 文献与证据索引', '', '检索日期：2026-10-30。共31份核心来源，包含研究论文、综述、社论、更正和预印本。逐项注明实际阅读范围。', '',
       '引用的研究事实来自本轮取得的公开原文或摘要；“用途”是本报告的研究判断。已保存网页不意味着逐段精读或复核原始数据。', '',
       '部分出版商全文返回403或网络超时，已用可访问的期刊元数据、Europe PMC或Crossref摘要；未将其标记为全文阅读。检索中出现出版日期晚于本轮截止日或日期不清的记录，没有纳入以下索引。', '']
for a in records:
    lines += [f"## {a['id']} · {a['title']}", '',
              f"{a['journal'] or '预印本平台'} · {a['date']} · {a['kind']}。 [DOI与原始来源](https://doi.org/{a['doi']})", '',
              f"**实际阅读：** {a['reading_level']}。", '',
              f"**论文事实：** {a['fact']}", '',
              f"**研究用途：** {a['use']}", '']
(ROOT/'文献与证据索引.md').write_text('\n'.join(lines))
print('Created bibliography with',len(records),'sources.')
