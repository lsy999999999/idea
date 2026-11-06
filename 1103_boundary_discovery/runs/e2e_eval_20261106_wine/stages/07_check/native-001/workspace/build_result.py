import glob, json, os

root = os.path.dirname(__file__)
project = "/Applications/ideas/1103_boundary_discovery"
ideas_path = project + "/runs/e2e_eval_20261106_wine/ideas.json"
ideas = json.load(open(ideas_path, encoding="utf-8"))["ideas"]

def abstract_for(work_id):
    for path in glob.glob(root + "/search_*.json"):
        payload = json.load(open(path, encoding="utf-8"))
        for work in payload.get("results", []):
            if work.get("id", "").endswith(work_id):
                inv = work.get("abstract_inverted_index") or {}
                tokens = []
                for token, positions in inv.items():
                    tokens.extend((pos, token) for pos in positions)
                return work, " ".join(t for _, t in sorted(tokens))
    raise RuntimeError(work_id)

specs = {
 "W1": [("W1515711631", "Sensory properties of premium Spanish red wines and their implication in wine quality perception", "https://doi.org/10.1111/j.1755-0238.2010.00115.x", "The major aims of the present study were to define the sensory space of these wines and determine the implication of their sensory properties (aroma and in-mouth attributes) in the quality perception of wine professionals.", "related_only")],
 "W2": [("W3044029723", "Inter-rater reliability of ‘clean cup’ scores by coffee experts", "https://doi.org/10.1111/joss.12596", "In both studies, IRR reliability was found to be low, denoting a lack of concept alignment among experts.", "related_only")],
 "W3": [("W4376140597", "Wine rankings and the Borda method", "https://doi.org/10.1017/jwe.2023.7", "We propose to establish wine rankings using scores that depend on the differences between favorable and unfavorable opinions about each wine, according to the Borda rule.", "very_similar"), ("W2622589455", "Sensory quality of wine: quality assessment by merging ranks of an expert-consumer panel", "https://doi.org/10.1111/ajgw.12287", "The method presented aims to bridge this gap by providing a ‘quality assessment by merging ranks of an expert consumer panel (QAMREC)’ procedure, which ranks wines on a quantitative scale according to their sensory quality.", "very_similar")],
 "W4": [("W3043737575", "Representational and sensory cues as drivers of individual differences in expert quality assessment of red wines", "https://doi.org/10.1016/j.foodqual.2020.104032", "The aim of this study was to model decisional consensus in expert red wine tastings, using an integrated competency framework.", "related_only")]
}
searches = []
ledger_rows = []
for i, path in enumerate(sorted(glob.glob(root + "/search_*.json")), 1):
    name = os.path.basename(path)
    bits = name[:-5].split("_")
    query_obj = json.load(open(path, encoding="utf-8"))
    query = query_obj.get("meta", {}).get("x_query", {}).get("oql", "")
    searches.append({"query": query or name, "url": "https://api.openalex.org/works", "status": "completed", "idea_ids": [bits[2]], "facet": bits[3], "round": 1, "snapshot_path": path})
    for rank, work in enumerate(query_obj.get("results", []), 1):
        selected_ids=("W1515711631","W3044029723","W4376140597","W2622589455","W3043737575")
        ledger_rows.append({"idea_id":bits[2],"facet":bits[3],"query":query or name,"rank":rank,"openalex_id":work.get("id"),"title":work.get("title"),"doi":work.get("doi"),"publication_date":work.get("publication_date"),"dedup_key":work.get("doi") or work.get("id"),"selection":"selected for claim comparison" if work.get("id","").endswith(selected_ids) else "not selected; limited abstract relevance or duplicate"})
with open(root+"/retrieval_ledger.json","w",encoding="utf-8") as f: json.dump(ledger_rows,f,ensure_ascii=False,indent=2)

checks=[]
for idea in ideas:
    iid=idea["id"]
    cards={
     "W1": ["以既定葡萄酒评审流程产生的 quality 中位数为目标，研究理化测量与聚合分的关系。", "理化测量和聚合分；机制未指定。", "询问聚合分关系及其与个体评委分关系是否相同。", "既定评审流程；其他条件未指定。", "未指定。", "葡萄酒质量评审。"],
     "W2": ["评委对同一酒样的绝对评分是否相近。", "评委评分；指标未指定。", "判断绝对评分是否可互换。", "实际用途要求绝对可互换时；其他条件未指定。", "未指定具体指标。", "葡萄酒感官评审。"],
     "W3": ["评委对酒样的相对顺序是否一致，以及评分差异来源。", "区分评委严厉度、酒样差异、评委与酒样交互。", "分别研究排序一致与评分方差来源。", "评审流程及样品设计未指定。", "未指定；统计量未选择。", "葡萄酒感官评审。"],
     "W4": ["评审流程评分是否测量独立定义的潜在感官属性。", "测量构念效度；具体机制未指定。", "评估评分与独立定义潜在属性的对应关系。", "须独立定义潜在感官属性；其余未指定。", "未指定效标或设计。", "葡萄酒感官评审。"]}[iid]
    sources=[]; evidence=[]; comparisons=[]
    claims=[{"claim_id":iid+"-C1","text":idea["idea"],"idea_quote":idea["idea"],"kind":"question","coverage":"UNKNOWN"}]
    for j,(wid,title,url,quote,sim) in enumerate(specs[iid],1):
        work,text=abstract_for(wid)
        snap=root+"/source_"+wid+".txt"
        if not os.path.exists(snap):
            with open(snap,"w",encoding="utf-8") as f: f.write("Title: "+title+"\nURL: "+url+"\nPublication date: "+str(work.get("publication_date"))+"\nEvidence: OpenAlex abstract\n\n"+text+"\n")
        sid=iid+"-S"+str(j); eid=iid+"-E"+str(j)
        sources.append({"source_id":sid,"title":title,"url":url,"accessed_on":"2026-11-06","content_note":"已读 OpenAlex 返回的摘要；保留全文摘要文本于本地快照。","similarity":sim,"evidence_level":"abstract","snapshot_path":snap,"publication_date":{"earliest":work["publication_date"],"latest":work["publication_date"],"url":"https://api.openalex.org/works/"+wid,"snapshot_path":snap,"quote":"Publication date: "+str(work["publication_date"])}})
        evidence.append({"evidence_id":eid,"source_id":sid,"quote":quote,"locator":"Abstract"})
        relations={"problem":"RELATED_ONLY","mechanism":"UNKNOWN","contribution":"RELATED_ONLY" if sim=="very_similar" else "UNKNOWN","assumptions":"UNKNOWN","validation":"UNKNOWN","application":"RELATED_ONLY"}
        facets={k:{"relation":v,"reason":"摘要提供方向层面的依据；未覆盖的细节保留未知。" if v!="UNKNOWN" else "摘要未说明该维度。","evidence_ids":[eid] if v!="UNKNOWN" else []} for k,v in relations.items()}
        claimrel="PARTIAL_OVERLAP" if sim=="very_similar" else "UNKNOWN"
        comparisons.append({"source_id":sid,"facets":facets,"claim_relations":[{"claim_id":iid+"-C1","relation":claimrel,"reason":"来源涉及相近的葡萄酒评审排序问题，但摘要不能证明覆盖本候选的完整问题。" if claimrel!="UNKNOWN" else "相邻研究不足以判定此问题已被研究。","evidence_ids":[eid] if claimrel!="UNKNOWN" else [],"conditions":{"relation":"not_applicable","reason":"这是研究问题比较，不是定理蕴含比较。"}}]})
    close=any(s["similarity"]=="very_similar" for s in sources)
    claim_state="PARTIAL_OVERLAP" if iid=="W3" else "UNKNOWN"
    claims[0]["coverage"]=claim_state
    overall=claim_state if iid=="W3" else "UNCLEAR"
    ctx=idea.get("evaluation_context",{"mode":"current","reference_date":None,"reference_reason":"No historical cutoff supplied.","source_papers":[]})
    roles=[]
    for s in sources: roles.append({"source_id":s["source_id"],"paper_id":None,"timing":"current","role":"eligible_prior","eligible":True})
    assessment={"context":ctx,"source_roles":roles,"all_sources_status":overall,"rediscovered_claim_ids":[],"task_verdict":"RETAIN_CANDIDATE" if overall!="UNCLEAR" else "UNRESOLVED","candidate_retained":True,"world_novelty":"NOT_ESTABLISHED"}
    prior_reason="检索发现非常相近的研究方向；该方向重合本身不说明原问题已被完整覆盖。" if close else "有限检索发现相邻工作，但现有证据不足以认定方向非常相近；因证据不完整而记为 unclear。"
    checks.append({"idea_id":iid,"prior_work":{"verdict":"close_direction_found" if close else "unclear","reason":prior_reason,"sources":sources},"math":{"verdict":"no_obvious_error","reason":"候选以研究问题表述，未见明显数学或逻辑矛盾；未要求证明或验证。","errors":[]},"novelty":{"idea_card":dict(zip(["problem","mechanism","contribution","assumptions","validation","application"],cards)),"claims":claims,"evidence":evidence,"comparisons":comparisons,"overall_status":overall,"assessment":assessment,"combination_assessment":{"status":"not_claimed","claim_ids":[],"reason":"候选没有声称一个整合机制或组合贡献。"},"remaining_difference":[{"claim_id":iid+"-C1","description":"当前摘要证据未确认该完整问题已被覆盖。"}],"recommended_action":"TARGETED_SEARCH","next_step":"针对本问题中尚未解析的具体 estimand 与评分模型检索全文研究，再判断覆盖关系。","search_exhaustive":False,"search_summary":{"stop_reason":"budget_reached","limitations":"完成每个候选三个检索角度的 OpenAlex 搜索并比较所选摘要；候选池与全文检索不足，快照保存在本工作区。"}}})

result={"schema_version":"claim-centric-v2","summary":"对四个葡萄酒评审研究问题完成有限的三角度公开文献检索与明显数学/逻辑粗筛。", "artifacts":[root+"/CHECK.md",root+"/retrieval_ledger.json"],"evidence":[{"kind":"retrieval","path":root}],"claims":[{"text":"四个问题均未发现明显数学或逻辑错误。"}],"limitations":["检索与摘要阅读受本次预算限制，不构成完整文献综述。","若摘要未呈现候选所问的精确 estimand 或构念定义，覆盖判断保持未知。"],"next_actions":["对 W1 的聚合中位数目标、W2 的绝对一致、W4 的构念效度做定向全文检索。"],"searches":searches,"checks":checks}
with open(root+"/result.json","w",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2)
