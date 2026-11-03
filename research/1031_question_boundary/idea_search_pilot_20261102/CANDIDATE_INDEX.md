# 54条初始候选与18条最终记录索引

全部内容保留；表中分组是隐藏组名模型评审的分组，最终验收包含组织者对错系数的修正。详细依据见REPORT.md。

## wine / A

|轮次|候选|原始标题|评审思路族|候选标准|
|---|---|---|---|---|
|1|I1|Does residual sugar modify the alcohol–quality association within wine color?|F1|通过|
|1|I2|Does free sulfur dioxide fraction add a within-color quality association?|F5|通过|
|1|I3|Test sugar–alcohol balance with randomized sensory samples|F2|通过|
|2|I1|Does alcohol–sugar interaction persist under flexible response curves?|F1|通过|
|2|I2|Does free sulfur dioxide add information beyond total concentration and pH?|F5|通过|
|2|I3|Does a randomized sugar–alcohol interaction generalize across wine lots?|F2|通过|
|3|I1|Does volatile acidity have threshold-specific associations with quality?|F9|通过|
|3|I2|Does visible wine color shift ratings of the same wine?|F8|通过|
|3|I3|Does free sulfur dioxide add a conditional association beyond total sulfur dioxide?|F5|通过|

|轮次|最终候选标题|状态|证据级别|最终验收|
|---|---|---|---|---|
|1|Does residual sugar modify the alcohol–quality association within wine color?|blocked|proposal_only|不计入：阻塞或区分预测不足|
|2|Do alcohol–sugar interaction terms improve ordinal quality fit within wine color?|revised|observational_support|不计入：阻塞或区分预测不足|
|3|Does the volatile_acidity association vary across quality thresholds?|blocked|computed_feasibility|不计入：阻塞或区分预测不足|

## wine / B

|轮次|候选|原始标题|评审思路族|候选标准|
|---|---|---|---|---|
|1|I1|Does residual sugar modify the alcohol-quality association?|F1|通过|
|1|I2|Does sulfur dioxide composition matter beyond total concentration?|F5|通过|
|1|I3|Does chemical overlap account for the red-white quality-score gap?|F12|通过|
|2|I1|How much quality disagreement remains among chemically similar wines?|F17|通过|
|2|I2|Does chemical rarity distinguish high-scoring wines from typical wines?|F16|不通过|
|2|I3|Does residual sugar buffer the sensory effect of volatile acidity?|F7|通过|
|3|I1|Do chemical associations shift every adjacent quality threshold in the same way?|F9|通过|
|3|I2|Does oxygen exposure change sulfur-dioxide loss differently across wine pH?|F3|通过|
|3|I3|Are quality scores reproducible across repeated blind ratings?|F10|通过|

|轮次|最终候选标题|状态|证据级别|最终验收|
|---|---|---|---|---|
|1|Does residual sugar modify the alcohol-quality association?|revised|proposal_only|通过|
|2|How much quality disagreement remains among chemically similar wines?|retained|observational_support|通过|
|3|Do chemistry-score associations vary across adjacent quality thresholds?|revised|proposal_only|通过|

## wine / C

|轮次|候选|原始标题|评审思路族|候选标准|
|---|---|---|---|---|
|1|I1|Does residual sugar modify the alcohol–quality association within wine color?|F1|通过|
|1|I2|Is the quality association with sulfur dioxide tied to its free fraction?|F13|通过|
|1|I3|Do red and white wines differ in score at comparable measured chemistry?|F11|通过|
|2|I1|柠檬酸是否改变挥发酸与质量评分的关系？|F4|通过|
|2|I2|酒精度与评分的关系是否在高酒精区间弯曲？|F14|通过|
|2|I3|挥发酸与评分的关联是否因酒色而异？|F15|通过|
|3|I1|Does volatile acidity relate differently to low and high quality-score thresholds?|F9|通过|
|3|I2|Does free sulfur dioxide add a distinct score association beyond total sulfur dioxide?|F5|通过|
|3|I3|Is the residual-sugar association with quality distinct from its association through alcohol?|F6|通过|

|轮次|最终候选标题|状态|证据级别|最终验收|
|---|---|---|---|---|
|1|Does residual sugar modify the alcohol–quality association within wine color?|retained|observational_support|通过|
|2|白葡萄酒中柠檬酸是否改变挥发酸与质量评分的关联？|revised|observational_support|不通过：错系数验收|
|3|挥发酸与低、高质量评分阈值的关联强度是否不同？|revised|proposal_only|通过|

## shopping / A

|轮次|候选|原始标题|评审思路族|候选标准|
|---|---|---|---|---|
|1|I1|Does product-page dwell relate differently to purchase across visitor types?|F01|通过|
|1|I2|Does a comparison aid increase conversion for high-dwell new visitors?|F17|通过|
|1|I3|Do product revisits after information pages mark a purchase-oriented path?|F15|通过|
|2|I1|Does the dwell proxy–purchase association flatten at higher dwell levels?|F01|通过|
|2|I2|Does an information-to-product return precede higher purchase frequency?|F15|通过|
|2|I3|Does a product comparison aid change conversion for first-time shoppers?|F17|通过|
|3|I1|Does special-day proximity change the purchase association of informational browsing?|F11|通过|
|3|I2|Does checkout transparency improve conversion after product exploration?|F19|通过|
|3|I3|Does informational-page visitation distinguish calendar effects from visitor composition?|F12|通过|

|轮次|最终候选标题|状态|证据级别|最终验收|
|---|---|---|---|---|
|1|Does an aggregate product-page dwell proxy have different purchase associations by visitor type?|revised|proposal_only|通过|
|2|Does the purchase association of an aggregate product-dwell proxy differ in shape by visitor type?|revised|observational_support|通过|
|3|Does SpecialDay proximity modify the purchase association of informational-page duration?|revised|negative_result|通过|

## shopping / B

|轮次|候选|原始标题|评审思路族|候选标准|
|---|---|---|---|---|
|1|I1|Does browsing-time allocation relate to purchases beyond browsing volume?|F09|通过|
|1|I2|How much apparent conversion signal depends on PageValues?|F06|通过|
|1|I3|Does the product-duration association vary by month?|F10|通过|
|2|I1|Does SpecialDay add a signal beyond Month?|F13|通过|
|2|I2|Does a delivery-information prompt change conversion near special days?|F18|通过|
|2|I3|Do BounceRates and ExitRates carry distinct session-level signals?|F07|通过|
|3|I1|Is the product-page-depth gradient mostly a session-mix effect?|F08|通过|
|3|I2|Do zero-duration page categories indicate behavior or telemetry gaps?|F05|通过|
|3|I3|Does a randomized product-navigation aid change completed purchases?|F16|通过|

|轮次|最终候选标题|状态|证据级别|最终验收|
|---|---|---|---|---|
|1|Does product-duration share add information beyond browsing volume?|revised|proposal_only|通过|
|2|Does SpecialDay add information beyond Month?|retained|computed_feasibility|通过|
|3|How much of the product-page-depth gradient reflects observed session mix?|retained|observational_support|通过|

## shopping / C

|轮次|候选|原始标题|评审思路族|候选标准|
|---|---|---|---|---|
|1|I1|Is PageValues a label-proximal measurement channel?|F06|通过|
|1|I2|Does visitor type mark different conversion correlates?|F02|通过|
|1|I3|Are month-level conversion differences compositional?|F04|通过|
|2|I1|Does PageValues' predictive contribution persist across months?|F06|通过|
|2|I2|Does product-page dwell per page carry signal beyond browsing depth?|F01|通过|
|2|I3|Is SpecialDay associated with conversion within the same month?|F14|通过|
|3|I1|Does the weekend conversion difference persist within months?|F03|通过|
|3|I2|Does product-page dwell per page retain an association across visitor types?|F01|通过|
|3|I3|Does the allocation of browsing time across page categories matter?|F09|通过|

|轮次|最终候选标题|状态|证据级别|最终验收|
|---|---|---|---|---|
|1|Is PageValues a label-proximal measurement channel?|retained|observational_support|通过|
|2|Does the supplied dataset support within-month SpecialDay comparisons?|revised|computed_feasibility|通过|
|3|Is product-page duration share nonlinearly associated with Revenue?|revised|computed_feasibility|通过|
