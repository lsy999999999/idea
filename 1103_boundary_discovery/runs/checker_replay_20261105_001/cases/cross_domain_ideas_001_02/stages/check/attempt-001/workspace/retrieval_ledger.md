# 检索台账

日期：2026-11-05。引擎：OpenAlex Works API、Europe PMC REST、Crossref Works API；无语义检索。候选以 DOI/题名去重。

| Facet | Query | 状态与选择 |
|---|---|---|
| problem | OpenAlex: “immune memory” “resource allocation” | 完成；返回10条，含 How a well-adapting immune system remembers (DOI 10.1073/pnas.1812810116)，因讨论免疫记忆与历史信息更新而保留；其余多为通信资源分配或人工免疫，排除。 |
| problem | Europe PMC: “immune memory” AND (tissue OR allocation OR organization) | 完成；10条元数据结果，当前摘要大多是2026年条目且主题不匹配，未据此作实质判断。 |
| mechanism | OpenAlex: “immune memory” “mechanism design” | 失败：匿名请求限流。 |
| mechanism | Europe PMC: “local signals” AND “tissue-resident memory” | 失败：503。 |
| mechanism | Crossref: “immune memory” mechanism design | 完成；结果中 Contextual Mechanism Design 与生物免疫主题不相关，未作为比较来源；未找到直接跨域先例。 |
| contribution | OpenAlex: “tissue resident memory T cells” organization pathology | 失败：匿名请求限流。 |
| contribution | Europe PMC: “trained immunity” AND “tissue resident” memory pathology | 失败：503。 |
| contribution | Crossref: “immune memory” local rules tissue organization | 完成；保留 Tissue-resident memory T cells: local specialists in immune defence (DOI 10.1038/nri.2015.3) 作为局部组织免疫背景元数据；保留 A local macrophage chemokine network sustains protective tissue-resident memory CD4 T cells (DOI 10.21417/b71591) 并取得 OpenAlex 摘要，因局部信号网络和保护作用与部分主张相关。 |

实际深入阅读两篇摘要；另一个综述只有元数据，没有纳入实质比较。远低于建议的30–50候选/8–10摘要/3–5全文。因服务访问与时限，停止在部分检索；未进行第二轮。不得据此宣称无相近工作。
