# 检索与实际阅读记录

检索日期：2026-11-05。查询围绕 bulk / single-cell、细胞组成、intrinsic response、macrophage heterogeneity 与 identifiability/deconvolution。完整 API 响应与正文页面保存在 `retrieved/`。

## 最接近来源

**SCDC: bulk gene expression deconvolution by multiple single-cell RNA sequencing references** (Bib 2020; DOI: 10.1093/bib/bbz166)

URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC7820884/

实际读取 PMC 阅读页正文摘要。原文摘录：“SCDC, a deconvolution method for bulk RNA-seq that leverages cell-type specific gene expression profiles from multiple scRNA-seq reference datasets.” 同一段称方法用伪 bulk 样本和实验混合细胞系评估，随后报告其可复现细胞比例与测量表型之间的关联。其方向明确覆盖混合群体信号、组成估计及表型关联，因此与候选微观来源识别问题非常相近。

## 免疫细胞背景来源

**Revisiting Mouse Peritoneal Macrophages: Heterogeneity, Development, and Function** (Front Immunol 2015; DOI: 10.3389/fimmu.2015.00225)

URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC4437037/

实际读取 PMC BioC 全文 JSON 的摘要。原文称：“recently it was demonstrated the co-existence of two subsets in mouse peritoneal cavity (PerC)”；并指出巨噬细胞异质性与不同组织环境适应和专门功能相符。此来源说明腹腔巨噬细胞组成异质性是已有背景，但不说明目标训练/挑战实验样本实际发生组成变化。

## 查询日志

- Europe PMC：`(single-cell OR cellular composition) macrophage population response identifiability`。访问 URL 返回 Cloudflare 检查页，未获得检索结果；按失败记录，不作为新颖性依据。
- OpenAlex：`single-cell population composition cell-intrinsic response identifiability macrophage`。返回细胞内巨噬细胞机制及单细胞异质性文献。
- OpenAlex：`bulk gene expression cell composition deconvolution intrinsic differential expression`。定位 SCDC、BayesPrism、细胞类型解卷积与 bulk 表达来源研究。
- OpenAlex：`single-cell macrophage heterogeneity population average response`。定位巨噬细胞单细胞异质性研究。

## 资料文件

- `retrieved/openalex_macrophage_heterogeneity.json`：第一组 OpenAlex 返回。
- `retrieved/openalex_bulk_deconvolution.json`：bulk / 解卷积查询返回。
- `retrieved/PMC7820884_reader.html`：直接阅读的 SCDC PMC 页面。
- `retrieved/PMC4437037_fullText.json`：实际阅读的综述全文 JSON。
