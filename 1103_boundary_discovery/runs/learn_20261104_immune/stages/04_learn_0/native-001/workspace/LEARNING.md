# 学习记录：腹腔巨噬细胞的组成

## 缺口

讨论提出：原研究取样的腹腔巨噬细胞是否可当作同一种群体？群体平均NO/TNF-α变化能否区分细胞内在训练和组成变化？

## 新学到的关系

我读取了Cassado、D'Império Lima与Bortoluci关于小鼠腹腔巨噬细胞的综述全文（本地 XML 和 DOI 见下）。综述总结：稳态腹腔内常驻LPM通常较多，表型偏F4/80高/MHC-II低；SPM较少，表型偏F4/80低/MHC-II高，且与骨髓来源的单核细胞谱系关系更近。炎症或感染后，腹腔髓系构成可以改变：LPM在腹腔中减少，SPM及炎性单核细胞增加。综述将LPM的“消失”与迁移等动态联系起来，因此不能简单等同于细胞死亡。

这是文献对小鼠腹腔的一般描述。它让“取样群体组成可能影响群体均值”从抽象担忧变成了有免疫学背景的具体问题，但**没有证明**金黄色葡萄球菌原研究的先感染、后硫乙醇酸诱导流程中真的发生了哪种组成变化。实验顺序、时间和被测细胞必须单独核对。

## 教学计算

假设两类细胞的单位细胞读数分别固定为LPM 10、SPM 2。若LPM占80%，总体均值为 `0.8×10 + 0.2×2 = 8.4`；若LPM占20%，则为 `0.2×10 + 0.8×2 = 3.6`。均值下降约57%，即使两个亚群本身都没有改变响应。这里的读数和比例完全是假设，用来检查加权平均逻辑，不是论文数据；真实测量的权重还取决于细胞数、分泌量及归一化方式。

## 对问题的影响

我现在会把“预测群体平均响应”和“识别响应改变的微观来源”分开提问。前者可以把细胞来源、取样流程、训练时序和挑战终点固定后评估；后者还需知道被测细胞的亚群/身份，或观察细胞分辨的响应。当前材料没有给出原研究亚群比例或单细胞响应，故不能归因于组成改变，也不能把均值变化直接解释为每个细胞内在重编程。

## 未解问题

- 训练性免疫原始研究所用的先感染后硫乙醇酸方案中，具体亚群比例和细胞迁移/存活情况是什么？未知。
- 该原研究的细胞因子读数归一化如何影响不同亚群对总体读数的贡献？未知。
- 我未阅读全文中引用的LPM/SPM原始实验，无法进一步评估其门控策略和诱导后的具体时间动力学。

## 来源与获取情况

- **全文已取得并阅读**：Cassado Ados A, D'Império Lima MR, Bortoluci KR. “Revisiting mouse peritoneal macrophages: heterogeneity, development, and function.” *Frontiers in Immunology* 6:225 (2015). DOI: [10.3389/fimmu.2015.00225](https://doi.org/10.3389/fimmu.2015.00225). Europe PMC全文：[https://europepmc.org/articles/PMC4437037](https://europepmc.org/articles/PMC4437037)。本地原文：`sources/PMC4437037_fullText.xml`（Europe PMC fullTextXML 接口实际取得）。
- **失败访问，不作证据**：Ghosn et al. “Two physically, functionally, and developmentally distinct peritoneal macrophage subsets.” DOI: [10.1073/pnas.0915000107](https://doi.org/10.1073/pnas.0915000107)。Europe PMC fullTextXML 请求返回HTTP 500，未取得或阅读全文；本记录不引用其具体结论。
