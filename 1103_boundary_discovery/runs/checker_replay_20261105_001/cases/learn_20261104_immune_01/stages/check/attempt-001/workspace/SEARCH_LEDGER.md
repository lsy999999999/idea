# 检索台账

候选：`immune_population_prediction_and_microstate_identifiability`。日期：2026-11-05。引擎为 Crossref REST API、Europe PMC REST API、NCBI PubMed E-utilities 与 eLife 出版方网页；没有语义检索。

| 角度 | 查询 | 状态/响应 | 去重与筛选 |
|---|---|---|---|
| problem | `trained immunity peritoneal macrophage heterogeneity` | Crossref 完成，原始 JSON 为 `crossref_problem.json` | 命中腹腔巨噬细胞异质性与腹膜透析结局；保留为应用/问题近邻候选。 |
| problem | `peritoneal macrophage heterogeneity` | PubMed E-utilities 失败，返回 SOLR 500；原始响应为 `pubmed_peritoneal.json` | 不据此推断缺少文献。 |
| problem | `peritoneal macrophage heterogeneity OR trained immunity macrophage` | Europe PMC 失败，返回服务 503；`europepmc_problem.json` | 服务不可用，不重复扩大查询。 |
| mechanism | `macrophage composition identifiability prediction` | Europe PMC 失败，返回服务 503；`europepmc_mechanism.json` | 机制方向候选检索受限。 |
| mechanism | Crossref 单篇查询 DOI `10.7554/elife.105206.1` | 完成，`source_trainedstudy.json`；另存引用文本 `SOURCE_ELIFE.txt` | 保留：摘要明确研究 trained immunity 后巨噬细胞对特定功能挑战的响应。 |
| contribution | `population measurements cell composition identifiability macrophage` | Crossref 完成，原始 JSON 为 `crossref_contribution.json` | 返回广泛跨领域候选；标题/元数据不作为覆盖证据。 |
| contribution | Crossref 单篇查询 DOI `10.1016/j.kint.2016.10.030` | 完成，`source_peritoneal.json`，无摘要 | 仅书目与题名，不用于实质覆盖判断。 |
| contribution | Crossref 单篇查询 DOI `10.1038/s41423-023-01005-0` | 完成，`source_trainedreview.json`，无摘要 | 仅书目与题名，不用于实质覆盖判断。 |
| follow-up | eLife 出版方文章页 `https://elifesciences.org/articles/105206` | 完成，`elife_page.html` | 摘要与 Crossref 摘要一致；未形成独立的新比较证据。 |

去重：以 DOI 合并同文记录；保留 3 篇不同 DOI 的定向候选，其中只有 eLife 研究具可读摘要。没有达到 30–50 候选或 8–10 摘要；数据库服务故障与 900 秒上限内的访问限制导致提前停止。最接近来源只支持“指定二次挑战下 trained macrophage 响应已被研究”，不覆盖所提混合群体中预测来源的区分问题。未完成针对组成/存活/细胞间作用的有效摘要检索，因此相应覆盖状态为 UNKNOWN。
