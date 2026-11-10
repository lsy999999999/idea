# 四架构机械迟滞假说短程对照

同一 123 行实测输入，DeepSeek 官方 deepseek-flash / high，文献严格早于 2024-09-12。四套使用此前测试的固定版本源码；AI-Scientist-v2 在原优先服务器运行。具体适配与回合见 PROTOCOL_CN.md。

## 交付与实际用量

| 架构 | 状态 | 假说数 | 生成调用 | 生成输入 token | 生成输出 token | 终评调用 |
|---|---|---:|---:|---:|---:|---:|
| researchagent | complete | 3 | 55 | 896,213 | 211,119 | 5 |
| virtual_lab | complete | 3 | 21 | 279,383 | 113,423 | 2 |
| scientist_v2 | complete | 3 | 10 | 164,337 | 113,993 | 2 |
| evoscientist | complete | 3 | 9 | 222,785 | 34,726 | 2 |

调用按实际成功或截断响应结算记录统计，含定义服务和恢复尝试；缓存复用不重复计入。失败及未返回请求的实际计费未知。各架构发言、评审和工具选择不同，实际资源不是等额。

## researchagent

实际轨迹发展出三类条件性假设：H1 把邻态耦合操作化为窗口中心平移 B 与半宽变化 G，pair_A 支持“同 l 下 h 不变、c 移动”，但 G 在现有数据中近零且低功效；H2 提出 b+q*theta 的杠杆臂刚度机制，平行耦合预期 q≠0、交叉耦合近 bias-only，然 pair_A 的 l 效应是 sigma 对称共同模，pair_B 单点不能检验扫描，故保留为待新实验的机制假设；H3 主张 16 个无时间戳事件只能给出图/反转协议等价类，精确 twofold 重复是周期性而非吸引子稳定性，需释放阈值或单边干预破缺。三者均区分实测关系、模型假设与机制，未新增更强机制。

### H1 可加偏置—微分增益的窗口算子假设

**假说机制。** 每个转子在驱动坐标 gamma 中的切换窗口可用中心 c_i 与半宽 h_i 表示；邻转子状态 sigma 对耦合扭矩的效应被分解为平移窗口的可加偏置 B_i 和改变窗宽的微分增益 G_i。该分解是局部有效描述，不主张 bias/gain 是唯一物理成分。

**关系或推导。** c_i(sigma,l)=(gamma_i^up+gamma_i^down)/2; h_i(sigma,l)=(gamma_i^up-gamma_i^down)/2; B_i=c_i(sigma,l)-c_i(-sigma,l); G_i=h_i(sigma,l)-h_i(-sigma,l)。用带 sigma、l、sigma*l 项的嵌套回归估计，并对 ±0.1 cm 做区间传播。

**实测支持。** pair_A 在固定 l 下，两个 other_state 的 h 基本相同：rotor 1 的 h 约 7.2, 6.8/6.9, 6.0, 4.6 cm；rotor 2 约 1.7, 1.6, 1.4–1.5, 1.1 cm；而中心随 l 的邻态差从约 0 增至 1.2 cm（rotor 1）和 4.4 cm（rotor 2）。pair_B 在单一 l=4.7 下 B 很大（约 11.1 和 5.5 cm），G 近零但仅 0.1–0.3 cm，低于/接近分辨率。宽度随 l 的收缩是 sigma 对称的共同模效应，不应误写成邻态微分增益。

**适用假设。** gamma_down 按带符号阈值处理；当两阈值同号时 h 是代数半宽而非物理窗口。；bias/gain 是局部线性化分解，依赖驱动坐标与几何。；±0.1 cm 阈值不确定度需传播；pair_B 单点不能检验 l 扫描。；实测弹簧近似线性只约束机制，不证明几何机制。

**区别后果。** 在固定几何的新器件中，改变 other_state 应主要移动 c 而 h 在预注册等价边界内不变；若能可变 l 的交叉耦合床上观察到 G 随 l 系统增大并超过传播误差，则单纯 bias-only 描述失败，需要增益/刚度项。

**竞争解释。** 非可分离的耦合力矩、止挡限制分支、安装/夹持边界改变、驱动零点偏移，均可产生表观中心移动；pair_B 的 G≈0 低功效，不能单独确认 bias-only。

**原始出处。** 问题陈述·模型假设与 P1–P2；方法·第 2 阶段；Clarity/Validity/Originality 反馈对 c,h,B,G 的定义与 pair_B 低功效的批评。

**独立终评。** already_done；obvious_error。已覆盖：相互作用使上/下切换场随邻态线性移动，V_i^±(S)=v_i^±+Σc_ij s_j 正是可加偏置与状态依赖阈值；B/G 只是把上/下阈值改写成中心/半宽坐标，属重参数化而非新机制。未解：半宽微分增益 G 及其随 l 的系统变化、pair_B 的低功效，来源未给出。 窗口中心/半宽分解本身成立，但假设列表写“两阈值同号时 h 是代数半宽而非物理窗口”有明确坐标逻辑错误。只要 gamma_up>gamma_down，区间 [gamma_down,gamma_up] 仍是物理迟滞窗口，与阈值是否跨过坐标零点无关。pair_B 转子2、other=-1 的阈值为 2.1 与24.9 cm，物理窗口宽22.8 cm，半宽11.4 cm。可保留 B/G 分解，应删除该同号例外。独立终评原给no_obvious_error，原判保留。

- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖邻态改变翻转阈值的实验问题

### H2 杠杆臂刚度项 q 与平行/交叉耦合的机制假设

**假说机制。** 准静态力矩平衡中，邻转子通过 b_ij(l)+q_ij(l)*theta_i 作用：b 提供可加力矩，q 改变有效刚度 K_eff，从而改变阈值窗宽。平行耦合因杠杆臂随 l 增长而预期 q≠0、窗宽随 l 收缩；固定 l 的交叉耦合被假设为近纯加性偏置（q≈0）。

**关系或推导。** 0=k_d,i L_i(gamma-rho_i)-K_i theta_i+sum_j sigma_j[b_ij(l)+q_ij(l)theta_i]+tau_stop,i；K_eff=K_i-sum_j sigma_j q_ij；h_i≈tau_s,i/K_eff；c_i≈rho_i+sum_j sigma_j b_ij/K_eff。平行耦合拟合 b,q；交叉耦合检验 q=0，但跨器件只作为先验/传递假设，不作固定同一参数。

**实测支持。** pair_A 中 h 随 l 单调减小（rotor 1: 7.2→6.8/6.9→6.0→4.6 cm；rotor 2: 1.7→约1.6→1.4/1.5→1.1 cm），与杠杆臂改变有效刚度方向一致；但同一 l 下 G≈0，说明该 l 效应是 sigma 对称的共同模项，现有平行表并未支持“邻态微分增益 q”版本。pair_B 只有一个 l，不能检验交叉耦合的 l 依赖；其大 B、近不变 h 仅与 bias-only 相容，不构成强证据。

**适用假设。** 小角度、硬止挡、无惯性、无摩擦的准静态主动集模型。；q_ij 是局部线性化刚度项，非线性剩余需作为残差检验。；pair_A/pair_B/network_C 是不同器件，参数不可直接共享；钢线 1–3 边应单列。；止挡角度、安装坐标和夹持反力未知或需实测。

**区别后果。** 若 q 机制成立，新平行耦合床在固定 other_state 下扫 l 应显示 h(l) 的系统变化；交叉耦合床扫 l 时若 h 不变而仅 c 变，则支持 crossed bias-only，若 h 随 l 变则否定该纯加性版本。该预测需新扫描，pair_B 现有单点不能检验。

**竞争解释。** 纯 bias-only 交叉耦合；几何非线性/大角度力矩；止挡接触与夹持边界差异；弹簧样本与安装弹簧不一致。若新数据无图通过，应报告需放松的传递、边类型或几何假设，而非直接宣称机制被证伪。

**原始出处。** 方法·第 3 阶段；实验·第 2 阶段；Validity/Innovativeness 反馈对 q 定义、pair_B 欠定和跨器件传递的批评；Robustness 反馈对 l^2 容差与符号异常的提醒。

**独立终评。** unclear；obvious_error。已覆盖：耦合几何可控制相互作用强弱/符号，串行与平行构型已有铁磁/反铁磁差异。未解：b_ij(l)+q_ij(l)θ_i 的杠杆臂有效刚度 q、窗宽收缩与 l 扫描；pair_A 的 l 效应是 σ 对称共同模，pair_B 单点不能检验，来源无法评估该具体 q 机制。 由 0=k_d L(gamma-rho)-K_eff theta+sum sigma b+tau_stop，c/h 的约化式必须保留驱动杠杆 k_d L。现写 c≈rho+sum sigma b/K_eff 与 h≈tau_s/K_eff 量纲不一致：K_eff 是力矩/角度，b、tau_s 是力矩，比值是角度，而 gamma、c、h 的单位是 cm。固定 theta 时偏置项应给 Δc≈-b/(k_d L) 量级；固定止挡角差时窗宽应随 K_eff Δθ/(k_d L) 变，而不是 tau_s/K_eff 的倒数关系。故约化公式有明确的量纲和函数形式错误；b+q theta 的机制本身可在修正后保留，但现式不能按原样用于拟合或预测。

- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖耦合符号可正可负，但未涉及 q 刚度通道

### H3 仅有序约束下的网络等价类与弱可辨识性假设

**假说机制。** 16 个 network_C 事件没有时间戳、反转行和唯一并列顺序，只能作为区间/序约束：每次事件要求翻转转子的阈值区间包含观测 gamma，非翻转转子尚未越过其阈值；并列仅限同一单调段内相邻事件。网络拓扑、止挡角、附着坐标和反转幅度属于未知参数，输出应是等价类而非唯一图。

**关系或推导。** 对事件 t：gamma_t in I_{i_t}(sigma_t)，且 gamma_t notin I_j(sigma_t)（j≠i_t）；并列事件仅当同一单调段内相邻且 drive 坐标相同；反转幅度 R_k 作为满足单调段不等式的松弛变量，不由事件极值推断。图枚举为六条可能边 × {absent, parallel, crossed, wire}，用区间分支定界保留可行图与反转路径。

**实测支持。** network_C 的 8 状态循环在第 9–16 事件精确重复，实际只有约 7 个独立转变；若干转变共享 gamma=5.8 与 -5.1，顺序仅为名义；事件极值不能当作反转位置。故 16 行不足以唯一确定 6 边图。精确重复只证明单一协议下的周期性，不证明吸引子稳定性。

**适用假设。** 相邻并列才可无序；非相邻重复不得全局并列。；反转幅度为未知松弛变量；时间间隔不可推断。；pair 参数跨器件只作带不确定度的传递先验。；±0.1 cm 与无重复使等价类可能很大；需报告类体积/熵及容差敏感性。

**区别后果。** 若补测 network_C 各转子在 8 种邻态、两个方向下的释放阈值，并做单边刚度替换/附着偏移，则等价类应可测量地收缩；若收缩后仍无任何图通过新约束，则最小 pairwise kernel 类被拒绝（非证明）。若仅记录反转幅度，只能消除路径歧义，不能识别拓扑。

**竞争解释。** 更大的图/协议等价类；高阶或多体耦合；协议依赖的周期响应而非稳定吸引子；夹持边界改变阈值图。需把“无图通过”报告为嵌套放松结果，而非单一机制证伪。

**原始出处。** 问题陈述·未知量与可辨识性目标；方法·第 4–5 阶段；实验·第 1/4/5 阶段；Clarity/Validity/Robustness 反馈对并列规则、等价类度量、重复计数和最小破缺测量的批评。

**独立终评。** no_close_work_found；unclear。相关但不同：已有工作枚举相互作用 hysteron 的 transition graph，并研究 Preisach 图拓扑与 RPM；未覆盖“16 个无时间戳、含重复/并列事件只能给图与反转协议等价类”的弱可辨识问题。事件 1–8 与 9–16 精确重复只支持协议周期性，不能证明吸引子稳定性；此分辨属该候选自身贡献。 独立终评把“约7个独立转变”直接判为计数错误，判据偏强：八行状态内确有7个相邻转变，跨第8→9行后才出现第8种有向转变；但8种转变不等于8个独立约束，候选未定义“独立”。应明确使用全部8种观测转变，并说明约束的依赖性，当前不能仅凭边数给出数学错误结论。其弱可辨识性方向可保留。另需把非翻转者的有向阈值裕量不等式写清，gamma不在阈值区间内本身不保证其尚未越阈。

- [Profusion of transition pathways for interacting hysterons](https://doi.org/10.1103/physreve.104.054608)：覆盖 transition graph 枚举，但非无序事件的可辨识性
- [State transition graph of the Preisach model and the role of return-point memory](https://doi.org/10.1103/physreve.102.012122)：覆盖图拓扑层级，但未处理缺时间戳事件等价类

## virtual_lab

本轨迹最终收敛为两个采用假设加一个条件假设：H1a 是受 ell=0 阈值、J(0)=0 与 tan 基线约束的固定止挡力矩平衡基线；H1b 是解释 pair A 的 ell^2 杠杆臂工作机理，拟合良好但未被独立证明，Lc 仅作经验外推且几何上不可实现；H2 保留“交叉反转”为条件性两通道符号机制，因 pair B 与 pair A 的刚度、止挡、偏移和静止长度混杂而不能识别。Network C 未单列为第三机理，而作为 H1b 的可检验后果；势垒坍缩被拒绝为主要解释。

### H1a 固定止挡力矩平衡基线（受测量约束）

**假说机制。** 转子的阈值由硬止挡处力矩平衡决定：零驱动力矩时 gamma_sigma = y tan(theta_sigma)，因此 h0 = (y/2)(tan theta_+ - tan theta_-)，m0 = (y/2)(tan theta_+ + tan theta_-)。该基线不含耦合弹簧参数，只把止挡角、驱动作用线高度 y 和转子几何联系起来。它解释了为何 ell=0 时两转子在另一转子两种状态下阈值相同：耦合弹簧虽已张紧，但 J(0)=0；转子2约1.8 cm的中点偏移被归为驱动零点/预载常数，而非相互作用。

**关系或推导。** h0 = (y/2)(tan theta_+ - tan theta_-); m0 = (y/2)(tan theta_+ + tan theta_-); J(0) = 0（在耦合弹簧已张紧时）。取 y=9.4 cm、L=6.3 cm，得 h0≈7.00 cm（转子1）与1.74 cm（转子2）。

**实测支持。** Mechanics Scientist 终稿报告：修正基线预测 h0=7.00、1.74 cm，与 ell=0 实测半宽约7.2、1.7 cm 相差不超过0.2 cm；并指出 pair A 的四行 ell=0 数据在两种另一转子状态下上下阈值相同，故 J(0)=0 而弹簧已张紧。PI 初始输入还给出标定斜率与名义刚度相符、加载-卸载仅有小偏移。

**适用假设。** 刚性杆与固定硬止挡；线性弹簧；准静态驱动；摩擦与惯性可忽略；止挡角和驱动作用线高度 y 已知

**区别后果。** 若改变 y 或止挡角，h0 与 m0 应按上述 tan 公式协同变化；在任何 ell=0 且弹簧已张紧的构型中，另一转子状态不应改变上下阈值（J(0)=0）。若观察到 ell=0 时 J 非零超过约 ±0.1 cm，则该基线或其几何参数设定失败。

**竞争解释。** 被排除或压低的解释：仅靠耦合弹簧力大小产生中点偏移；把转子2的1.8 cm偏移当作转子间相互作用。该基线不解释 ell>0 的阈值收缩与 J，那些留给 H1b。

**原始出处。** Mechanics Scientist 终稿第2段（修正 sin 基线为 tan 基线）；Theory Scientist 终稿对 H1a 的拆分；Recommendation 终稿 H1a 段。

**独立终评。** no_close_work_found；obvious_error。已覆盖的仅是机械 hysteron 的双线性力—位移与切换场表述；未覆盖固定硬止挡下 γ=y tanθ、h0/m0 的 tan 基线及“耦合弹簧已张紧但 J(0)=0”这一特定几何关系。该候选本质是常规力矩平衡/参数基线，不是新机制解释；来源无法核对固定止挡几何。 h0算术正确：tan36.7≈0.745、tan(-36.6)≈-0.742，4.7×(0.745+0.742)≈6.99 cm；转子2 tan11.2≈0.198、tan(-9.8)≈-0.173，4.7×(0.371)≈1.74 cm。问题在m0：同一公式给转子2 m0≈4.7×(0.198-0.173)≈0.12 cm，而实测(3.5+0.1)/2=1.8 cm。若把1.8 cm归为驱动零点c_i，正确式子应为gamma_i^σ=c_i+y tan theta_i^σ，m0=c_i+(y/2)(tanθ+ + tanθ-)；原文m0公式漏了c_i，且由此推出的“m0随y/止挡角按tan公式协同变化”不成立。这是方程/逻辑遗漏，不是单纯未知安装细节；h0和J(0)=0部分不受影响。


### H1b 几何杠杆臂的 ell^2 耦合（工作机理，未证明）

**假说机制。** 在固定硬止挡上，耦合弹簧力矩 tau_i^(c) 经归一化因子 A_i 改写阈值：gamma_i^sigma = gamma_i0^sigma - tau_i^(c)(theta_i^sigma, s_j, ell)/A_i。对反射对称几何作偶次展开，耦合转矩含 ell^2(a_i^sigma + b_i^sigma s_j) 项，于是半宽受 ell^2 压低、状态偏置 J_i 随 ell^2 增长；J(0)=0。该机理把阈值变化主要归因于杠杆臂与弹簧伸长变化，而非负曲率势垒坍缩。

**关系或推导。** tau_i^(c) = tau_i0^sigma + ell^2(a_i^sigma + b_i^sigma s_j) + O(ell^4); h_i = h_i0 - (ell^2/(2A_i))[(a_i^+ - a_i^-) + (b_i^+ - b_i^-)s_j]; J_i = -(ell^2/(2A_i))(b_i^+ + b_i^-); m_i0 = gamma_i0,avg - (ell^2/(2A_i))(a_i^+ + a_i^-). 数据拟合形式：h_i = h_i0 - c_i ell^2，J_i = beta_i ell^2。宽度收缩要求 a_i^+ > a_i^-；h 对 s_j 近独立要求 |b_i^+ - b_i^-| ell^2/(2A_i) <~0.1 cm。

**实测支持。** Individual 报告 pair A 每转子四个 ell 的拟合：c1=0.115、c2=0.0261 cm^-1；beta1=-0.0273、beta2=-0.0977 cm^-1；最大残差不超过0.04 cm；线性-in-ell 拟合更差（h 残差约0.26/0.06 cm，J 约0.09/0.26 cm）。h 对另一转子状态近独立；最大 ell 时 mu=|J|/h 对 A2 约2.0、对 A1 约0.13。Lc=sqrt(h0/c) 约7.9/8.05 cm 只是二次外推，且 Mechanics Scientist 终稿指出该长度在真实几何中不可实现，故不构成势垒坍缩证据。

**适用假设。** 刚性杆、线性弹簧、准静态、摩擦/惯性可忽略；固定硬止挡；关于枢轴线的反射对称展开可截断到 ell^2；A_i、a_i^+/-、b_i^+/-、tau_i0 不由数据单独识别；J 的 cm 量纲以 A_i=kL cos(theta_sigma) 归一化，跨器件比较受安装弹簧不确定性影响

**区别后果。** 在固定 ell、弹簧和止挡下，把单个耦合附件点关于其转子枢轴线镜像，应使 J_i -> -J_i，而 h_i 与 m_i0 在约 ±0.1 cm 内不变；若失败，或更宽 ell 范围出现强线性项，则该转子的几何杠杆臂解释失败。对 pair A 做自由双转子驱动：ell=4.731 cm 时预期同驱动成对切换（mu 足够大），ell=0 时预期顺序切换（约3.5 cm 后7.3 cm）。Network C 中若同驱动对是强制切换/雪崩，阻断 s1 应改变后续同驱动阈值；若只是近退化独立阈值，则不应改变。

**竞争解释。** 竞争解释包括：线性-in-ell 杠杆、负曲率势垒坍缩（Lc 外推）、仅力大小的耦合、预载/安装不对称。轨迹最终保留 H1b 为工作机理但明确“未证明”，并拒绝把势垒坍缩作为主因。

**原始出处。** Individual 的 Fixed-stop lever-arm torque balance 推导与拟合表；Mechanics Scientist 终稿对 Lc 不可实现及 mu 的判别；Theory Scientist 终稿将 H1b 定义为带 J(0)=0 的 ell^2 工作机理；Recommendation 终稿 H1b 段。

**独立终评。** unclear；no_obvious_error。已覆盖：设计几何可控制 hysteron 相互作用，串行/平行构型改变耦合符号与强度。未解：ell^2 杠杆臂展开、J(0)=0、镜像使 J→−J、共同宽度收缩及 Lc 外推；来源不能评估该具体能量/力矩项是否成立，pair_A 拟合只是有效模型支持。 检查h=h0-c ell^2与J=beta ell^2：pair A ell=0时h1=7.2、h2=1.7；ell=4.731时h1=4.6、h2=1.1，给出c1≈(7.2-4.6)/4.731^2=0.116、c2≈(1.7-1.1)/22.38=0.027，与0.115/0.0261一致。J1=(m_+-m_-)/2在ell=4.731为(-0.3-0.9)/2=-0.60，J2=(-0.6-3.8)/2=-2.20，与beta1 ell^2≈-0.611、beta2 ell^2≈-2.19一致。若A_i=kL cosθ，tau/A_i= N cm / N = cm，量纲成立。m_avg近常数只要求a+ + a-≈0，不矛盾。未发现算术/量纲错误；机理仍是未证明的条件模型。

- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖弹性中介的相互作用，但无线杆 ell^2 机制

### H2 两通道符号机制与“交叉反转”条件假设

**假说机制。** 耦合对阈值偏置的符号并非只由两杠杆投影乘积决定。交叉项含两个通道：预载/弹簧刚度项与几何投影项。pair B 的正 J 可能来自任一通道、预载或安装不对称，不能仅凭“平行改为交叉”识别为交叉因果效应。

**关系或推导。** d tau_i/d theta_j = [f'(r)/r](d . u_i)(d . u_j) + f(r)(u_i . u_j)，其中 d=R_i-R_j，u_i=ell_i e'(theta_i)。第一项是预载/刚度通道，第二项是几何投影通道；近零预载时第二项可占主导，故 J 的符号不由交叉几何单独决定。

**实测支持。** PI 初始输入：pair B 在交叉耦合下出现正的状态依赖中点移动，而 pair A 在大 ell 为负移动。Theory Scientist 初始估计最大 ell 时 J 约为 +5.55、+2.75 cm（B1、B2），B1 的 mu 约1.37；但 Mechanics Scientist 与 Theory Scientist 终稿均指出 pair B 与 pair A 的刚度、止挡、偏移和静止长度不同，跨器件 J 量纲又受 A_i 不确定性影响，因此“交叉使符号反转”只是条件性解释。

**适用假设。** H1a/H1b 的刚性、线性、准静态假设仍适用；pair B 的安装几何、止挡与预载可独立标定后才可做跨对比较；J 的比较须在 gamma 空间并尽量固定 A_i；交叉本身不是唯一变量

**区别后果。** 在同一器件上做平行/交叉互换，并保持 ell、弹簧、止挡和安装偏移固定：若交叉是因果的，J 应翻转符号而 h 与 m0 基本不变；若 J 不翻转，或 h/m0 同时显著改变，则更支持预载/安装不对称或第二弹性通道，而非“交叉反转”。

**竞争解释。** 竞争解释：交叉几何导致符号反转；预载/安装不对称导致表观正 J；两通道弹性项的相对权重改变导致符号变化。轨迹未把 pair B 的正 J 识别为交叉效应。

**原始出处。** PI 初始 Team Member Input 对 pair B 正移动的描述；Theory Scientist 初始对 pair B J 与 mu 的估计；Theory Scientist 终稿将 H2 重构为两通道导数并称 pair B 受混杂；Recommendation 终稿 H2 段。

**独立终评。** unclear；unclear。已覆盖：邻态相互作用可为铁磁或反铁磁，且几何/串并联可改符号；故“交叉可反转符号”的上位方向不新。未解：把交叉效应拆成预载/刚度通道与几何投影通道的导数式，以及 pair_B 与 pair_A 刚度、止挡、偏移和静止长度混杂下的因果识别；来源未评估该二通道机制。 按给定d=R_i-R_j和u_i=ell_i e'(theta_i)，若取tau_i=f(r)(d·u_i)，则∂tau_i/∂theta_j=-(f'/r)(d·u_i)(d·u_j)-f(u_i·u_j)；若取tau_i=-f(r)(d·u_i)，则得到文中的正号形式。文中未给出tau_i定义，故导数式可条件成立，但符号不能独立核验；这不是已证明的算术错误。J数值核验：pair B rotor1 m(-1)=2.6、m(+1)=13.7，J=5.55；rotor2 m(-1)=13.5、m(+1)=19.0，J=2.75，与给定估计一致；但pair B与A的刚度、止挡和偏移混杂，跨器件符号比较不可识别。

- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖符号可变与邻态依赖
- [Controlled pathways and sequential information processing in serially coupled mechanical hysterons.](https://doi.org/10.1073/pnas.2308414121)：覆盖构型控制符号，但未给交叉/平行二通道分解

## scientist_v2

轨迹实际发展了三个条件性假设。H1 是修正后的偏置—刚度双通道有效模型：pair_A 两转子宽度按共同 1-(L/7.91)^2 收缩，但原设想的 J∝L 被数据挑战，J 反而近似 L^2；这是最强测量支持，也是关键修正。H2 是由 H1 外推的转子2分离环/从动带预测：|J|>h 约在 L≈3.7 cm 出现，L=5.5 cm 时预期约 4.1 cm 从动带，属未验证条件预测。H3 是交叉拓扑导致 J 符号反转的序数假设；pair_B 两转子符号确反转，但只有一个 L 且 stop 范围混杂（r=0.80），宽度放大不能归因。network_C 仅显示精确重复的八态单翻转序列；naive 振幅删行产生多翻转，未验证周期截断。nodes[1] 的嵌套拟合/反转计数在执行前被阻断，故振幅相图未完成。所有结论均为探索性有效模型，未识别机制。

### H1_bias_stiffness_dual_channel_L2 修正后的偏置—刚度双通道有效模型：共同 L^2 宽度塌缩与转子特异二次偏置

**假说机制。** 耦合弹簧对双稳转子同时贡献状态偏置与曲率/势垒降低。原设想是偏置随杠杆臂 L 线性、宽度收缩随 L^2；轨迹中的 pair_A 数据分析支持共同几何宽度通道，但把偏置通道修正为近似 J∝L^2。因而保留为条件性有效模型：宽度通道共享塌缩尺度 L*≈7.91 cm，偏置通道转子特异且二次。该机制是模型假设，不是已识别物理机制。

**关系或推导。** c_i(s_j,L)=c_i0+J_i(L)s_j; h_i(L)=h_i0-K_i L^2. pair_A: h_1=7.164-0.1151 L^2, h_2=1.689-0.0261 L^2; J_1=-0.0273 L^2, J_2=-0.0977 L^2; 1-h/h0=(L/7.91)^2. 展开假设: U=const+B_i(s_j,L)theta_i+0.5[K_i-C_i(L)]theta_i^2+...; 若两端杠杆为 L_i,L_j，则可令 K_i∝k_c L_i^2, J_i∝k_c L_i L_j；此比例关系是待检验假设。

**实测支持。** nodes[0].term_out 的 CALIBRATION 给出 S046/S019/S007 近线性弹簧（R^2≈1）；PAIR A 给出两转子 h 的 L^2 拟合（R^2=0.999/0.994）和 J 的 L^2 拟合（R^2=0.994/0.999）；COMMON NORMALIZED WIDTH 给出统一关系 1-h/h0=(L/7.91)^2（R^2=0.995, RMSE=0.009），尽管两转子 h0 相差约 4.2 倍。final §2–§3 明确报告原 J∝L 预测失败、J≈L^2 更强。

**适用假设。** 小角度、成对、准静态弹簧模型；弹簧近似理想线性；calibration 行仅作刚度先验，不是已安装弹簧的同一身份；pair_A 只有 4 个 L 值，阈值四舍五入到 0.1 cm，无独立重复；统一宽度塌缩不等于唯一机制；stop 接近、杠杆变化或弹簧松弛可混杂；状态依赖 Preisach 场也可吸收中心移动，因此双通道分解非唯一

**区别后果。** 在第五个独立安装距离 L 上，两转子应继续满足 h/h0≈1-(L/7.91)^2，且同一转子的 J 应对 L^2 的交叉验证优于对 L 的线性拟合；若宽度不按共同比例收缩而仅阈值整体平移，则双通道曲率机制被削弱。

**竞争解释。** 宽度塌缩可部分来自 stop 接近、驱动杠杆变化或弹簧松弛；中心移动可由任意状态依赖 Preisach 偏置吸收；因此数据支持受约束的有效模型，而非唯一机制。

**原始出处。** idea 的 Short Hypothesis；nodes[0].operation=draft 的 term_out（PAIR A、COMMON NORMALIZED WIDTH、CONCRETE FINDING）；final 报告 §2–§3 与 Mechanism 段。

**独立终评。** unclear；no_obvious_error。已覆盖：相互作用可用状态依赖切换场描述，且可同时改变上/下阈值；Preisach/相互作用 hysteron 模型也允许偏置与势垒参数。未解：共同宽度塌缩 1−h/h0=(L/7.91)^2、转子特异 J∝L^2 及“偏置通道 vs 曲率通道”的物理解释；来源只覆盖状态依赖阈值，无法判断 L^2 标度是否超出已知有效参数化。 未见明显算术或量纲错误：J 的 L^2 系数乘 cm^2 得 cm，与 h、c 的 cm 阈值一致。取 L=4.731 cm，h1=7.164−0.1151×22.382=4.587 cm，h2=1.689−0.0261×22.382=1.105 cm；1−h/h0 分别为约 0.360 与 0.346，接近 (4.731/7.91)^2=0.358。由 h0/K 分别得零点约 7.89 与 8.04 cm，与共同 7.91 cm 有约 1–2% 差异，但归一化拟合仍可成立。U 展开中 B_iθ 到阈值 h_i 的杠杆换算未写出，J∝L_iL_j 也只是待检验假设；这些是建模缺口/假设，不是已证明的矛盾。

- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖阈值随邻态变化，但未测宽度塌缩标度

### H2_rotor2_disjoint_loop_slaving_band 转子2的 |J|>h 分离环与从动带条件预测

**假说机制。** 若状态依赖偏置幅度超过半宽，两个 other_state 的阈值区间分离，出现一个宽度为 2(|J|-h) 的驱动带；在该带内自由转子被保持转子“奴役”，不随驱动翻转。pair_A 转子2因安装偏移/杠杆几何具有更大的 |J|/h，因此应比转子1更早进入该 regime。

**关系或推导。** 两个 other_state 的阈值区间约为 [c_i0+J_i-h_i, c_i0+J_i+h_i] 与 [c_i0-J_i-h_i, c_i0-J_i+h_i]；当 |J_i|>h_i 时两区间不交叠，从动带宽 W=2(|J_i|-h_i)。按 pair_A 二次拟合外推 L=5.5 cm：J_2≈-2.96 cm, h_2≈0.90 cm，区间约 [-2.25,-0.46] 与 [3.66,5.45] cm，W≈4.1 cm。

**实测支持。** nodes[0].term_out 的 PAIR A 显示 L=4.731 cm 时转子2 J=-2.2 cm、h=1.1 cm，已满足 |J|>h；CONCRETE FINDING 给出交叉点约 L≈3.7 cm。final 的 Conditional prediction 明确给出 L=5.5 cm 的区间与约 4.1 cm 从动带。

**适用假设。** 二次拟合可外推到 L=5.5 cm，且未越过 stop/slack 失效区；c_i0≈1.6 cm 在该外推中近似常数；pair_A 的几何与驱动协议可复现；阈值读数误差不改变区间拓扑；该预测是条件性的，不是已观测结果

**区别后果。** 在 pair_A 转子2、L=5.5 cm 的独立实验中，应观察到约 4.1 cm 宽的驱动带：保持转子符号固定时，转子2不翻转而随保持转子状态定向；若两个阈值区间仍交叠或从动带不存在，则外推的 L^2 律/双通道模型受挫。

**竞争解释。** stop 附近非线性、弹簧松弛、驱动杠杆变化或转子2的几何偏移都可在不引入“从动带”机制的情况下改变表观阈值；需独立力矩—角度测量排除。

**原始出处。** nodes[0].term_out 的 PAIR A 与 CONCRETE FINDING；final 的 Conditional prediction 段；nodes[1].plan 也提出该从动带，但其执行在 nodes[1] 被阻断。

**独立终评。** unclear；no_obvious_error。已覆盖：相互作用 hysteron 可出现雪崩，一个元件翻转会触发另一个翻转；这与“奴役/从动”相邻。未解：|J|>h 造成两个邻态阈值区间不交叠、宽度 W=2(|J|−h) 的驱动带，以及 L=5.5 cm 外推；来源未给该分离环判据，且越界外推需独立数据。 按给定二次式复算：L=5.5 cm 时 L^2=30.25，J2=−0.0977×30.25=−2.955 cm，h2=1.689−0.0261×30.25=0.900 cm。取 c0≈1.6 cm，两个区间约为 [−2.255,−0.456] 与 [3.657,5.456] cm，间隙 4.113 cm，近似等于 2(2.955−0.900)=4.110 cm；交叉点由 0.0977L^2=1.689−0.0261L^2 得 L≈3.69 cm，与文中约 3.7 cm 相符。外推未观测且可能进入 stop/slack 区；“从动带”是条件机制语言，不是由区间拓扑直接证明的结论，但不构成算术错误。

- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖雪崩式从动，未覆盖阈值区间分离

### H3_crossed_topology_sign_inversion 交叉弹簧拓扑导致偏置符号反转的条件性假设

**假说机制。** 把平行耦合改为交叉耦合会改变弹簧力臂方向，从而反转状态依赖偏置 J 的符号，并可能改变其幅度；该拓扑假设只作序数/符号检验，不主张固定放大倍数。宽度是否随拓扑改变仍受 stop 范围强烈混杂。

**关系或推导。** 在可比 L 下检验 sign(J_B)≈-sign(J_A)；不预设 |J_B|/|J_A| 的定量值。pair_B 观测：转子1 J_A=-0.60, J_B=+5.55（比值 9.25）；转子2 J_A=-2.20, J_B=+2.75（比值 1.25）。宽度比较须报告 h 与 stop half-range 的相关（r=0.80, n=4），不能直接归因于拓扑。

**实测支持。** nodes[0].term_out 的 PAIR B 行显示两转子 J 符号均翻转；final §4 报告转子2 pair_B h=11.55 cm 对 pair_A h=1.10 cm，但 stop 范围也宽得多，故宽度证据被混杂。

**适用假设。** pair_B 只有一个 L=4.7 cm，无法分离拓扑与杠杆臂长度；stop 角度/半程未归一化，宽度比较不可靠；交叉弹簧的安装身份与 calibration 样品不完全对应；符号反转是可重复的拓扑效应，而非单次装配误差——此点未验证

**区别后果。** 在 stop 几何匹配、同一 L 的平行/交叉对照中，J 的符号反转应保留；若把 h 按 stop half-range 归一化后 pair_B 转子2的宽度优势消失，则“交叉拓扑特异宽度放大”被拒绝，只保留符号反转。

**竞争解释。** stop 范围、附件坐标和有效杠杆变化可单独产生表观 J 与 h 差异；状态依赖 Preisach 场也可拟合符号变化，故不能据此识别唯一弹簧机制。

**原始出处。** nodes[0].term_out 的 PAIR B 与 CONFOUND CHECK；final 报告 §4。

**独立终评。** already_done；no_obvious_error。已覆盖：串行构型给出反铁磁样相互作用，平行构型预期铁磁，说明连接几何可反转相互作用符号；交叉弹簧使 J 反号是同一方向上的一种实现。未解：pair_B 仅一个 L、止挡半程未归一化（r=0.80）导致幅度与宽度放大不能归因；来源已覆盖“符号受拓扑控制”的核心方向。 由 pair_B 行可复算：转子1 两个 other_state 的中心均值约 2.6 与 13.7 cm，给 J≈+5.55 cm、h≈4.05 cm；转子2 中心均值约 13.5 与 19.0 cm，给 J≈+2.75 cm、h≈11.55 cm。pair_A 在 L≈4.73 cm 的 J 约为 −0.61 与 −2.20 cm，故两转子符号反转及幅度比约 9.1（按 −0.60 则 9.25）和 1.25 均可复算。四个转子点粗算 h 与 stop half-range 的 r≈0.80，保留宽度混杂警告是合理的；单一 L 与安装偏移使拓扑归因不足，但这是识别问题，不是算术或量纲错误。

- [Controlled pathways and sequential information processing in serially coupled mechanical hysterons.](https://doi.org/10.1073/pnas.2308414121)：直接覆盖构型改变相互作用符号
- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖符号反转现象本身

## evoscientist

在 123 行测量上保留 3 个条件性解释：H1 用硬止挡处的双线性力臂耦合解释 pair_A 阈值随 mount_l_cm 的漂移及 ell=0 的零依赖；H2 用交叉耦合翻转固定转子力臂符号解释 pair_B 的正 down 阈值与大幅位移，但定量低估 21.4 cm 的观测差；H3 用矩形 hysteron 网络解释 network_C 事件 1-8 与 9-16 的 period-1 重复。三者均非验证结论：校准无独立重复，阈值仅 ±0.1 cm 单次测定，network_C 几何与反转位置未知，H2 还受 pair_A/pair_B 止挡角差异混淆。

### H1 H1：硬止挡处的双线性力臂耦合设定阈值（条件性）

**假说机制。** 每个转子在硬止挡上，切换由净力矩过零控制；驱动弹簧与耦合弹簧的力矩均随各自力臂线性变化。耦合项正比于被切换转子的耦合力臂 ell_i，因此 ell_i=0 时另一转子的固定状态不应进入阈值。该机制把 pair_A 中随 mount_l_cm 的阈值漂移解释为杠杆臂变化，而不是弹簧预张力变化。

**关系或推导。** 力矩平衡假设：L*k_d*(gamma*cos(theta_i)-L*sin(theta_i)-delta_d)+k_c*ell_i*(ell_i*sin(theta_i)-ell_j*sin(theta_j)-delta_c)=0。解得 gamma*_i=[k_d*L^2*sin(theta_i)+k_c*ell_i*(ell_i*sin(theta_i)-ell_j*sin(theta_j))+C]/(k_d*L*cos(theta_i))。对力臂求导：d(gamma*_i)/d(ell_i)=(k_c/k_d)*(2*ell_i*sin(theta_i)-ell_j*sin(theta_j))/(L*cos(theta_i))。因此阈值对 ell_i 的斜率可正可负，取决于 2*ell_i*sin(theta_i) 与 ell_j*sin(theta_j) 的相对大小；ell_i=0 时耦合项整体消失。

**实测支持。** 校准为线性且无明显回滞：S046、S019、S007 的最小二乘斜率分别为 45.85、18.97、6.96 N/m，对 0.46、0.19、0.07 N/cm（即 46、19、7 N/m），截距给出自由长度约 3.89、4.21、2.67 cm（record_id 1-67；校准工具记录 Dbeb2af9、Df870c81、D334e917）。pair_A 阈值（record_id 68-99，±0.1 cm）显示：rotor1 up 在 other=-1 时从 7.3 降至 5.5 cm（斜率约 -0.38），other=+1 时从 7.3 降至 4.3（约 -0.65）；rotor2 up 在 other=-1 时从 3.5 升至 4.9（约 +0.30），other=+1 时从 3.5 降至 0.5（约 -0.65）。最关键是 mount_l_cm=0 时，四组配对阈值完全相同（7.3/7.3、-7.1/-7.1、3.5/3.5、0.1/0.1），与“ell_i=0 时另一转子状态不进入耦合项”的模型关系一致。按 k_c/k_d=0.07/0.19 与 L=6.3 cm 估算，斜率量级约 0.2-0.6，覆盖实测的 0.30-0.65（仅数量级支持）。

**适用假设。** 切换由硬止挡处净力矩过零决定，而非热激活或临界势垒条件。；弹簧力线性、几何小角度近似成立；驱动与耦合的静止长度仅给阈值加常数偏置。；mount_l_cm 代表被切换转子 i 的耦合力臂 ell_i；该语义未能由定义服务确认，故零依赖检验以此为前提。；pair_A 的拟合参数不与 pair_B 或 network_C 共享。；阈值单次测定、无独立重复；斜率是对 4 个力臂点的探索性线性拟合。

**区别后果。** 若能把 rotor2 的耦合 attachment 移到负 ell_i（枢轴另一侧），其 up 阈值斜率 +0.30 应连续经过零，并在 ell_i*=ell_j*sin(theta_j)/(2*sin(theta_i)) 处反号；纯预张力/自由长度偏置解释只预测共同平移，不预测符号反转。另一个可检验点：在固定其他几何时，阈值对 ell_i 应近似二次型，而不是对预张力参数的线性平移。

**竞争解释。** 预张力或静止长度偏置、纯止挡几何差异、摩擦/粘滞、mount_l_cm 语义不同（例如测的是另一转子的力臂）均可产生部分阈值漂移；H1 的优势只在 ell_i=0 的零依赖与斜率符号模式，而非已排除这些替代。

**原始出处。** 最终交付响应（FINAL_DELIVERY 后）H1 段；数据 record_id 68-99；校准与阈值工具记录 Dbeb2af9、Df870c81、D334e917。此段为轨迹中实际提出的条件性模型。

**独立终评。** unclear；obvious_error。已覆盖：机械 hysteron 可用双线性力—位移、力平衡和状态依赖切换场建模，阈值可由几何参数移动。未解：固定硬止挡的杠杆臂 ell_i、ell_i=0 时另一转子状态不进入耦合项、阈值对 ell_i 的二次型/符号反转点；来源未给该杠杆臂力矩式，故不能判定是已知力学变体还是新机制。 量纲本身一致：k_d L(gamma cosθ-L sinθ-delta_d) 与 k_c ell_i(ell_i sinθ_i-ell_j sinθ_j-delta_c) 均为 N·cm 量级。但代数求解有符号错误。由 H1 自己写的力矩平衡解出应为 gamma*_i=[k_d L^2 sinθ_i + k_d L delta_d - k_c ell_i^2 sinθ_i + k_c ell_i ell_j sinθ_j + k_c ell_i delta_c]/(k_d L cosθ_i)，即耦合项为 -k_c ell_i(ell_i sinθ_i-ell_j sinθ_j)+C；H1 写成 +k_c ell_i(ell_i sinθ_i-ell_j sinθ_j)+C，符号相反。于是正确导数应为 d gamma*/d ell_i=(k_c/k_d)(ell_j sinθ_j-2 ell_i sinθ_i)/(L cosθ_i)，而 H1 给出相反号。因此“斜率正负由 2 ell_i sinθ_i 与 ell_j sinθ_j 相对大小决定”的方向被反转；ell_i=0 时耦合项消失的结论不受影响。C 未定义但可并入常数，非致命；实测斜率量级不能抵消该符号错误。

- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖邻态依赖阈值

### H2 H2：交叉耦合翻转固定转子的力臂符号，解释 pair_B 的位移窗口（条件性）

**假说机制。** pair_B 的耦合弹簧为交叉连接，等效于在耦合力矩中把固定转子的力臂 ell_j 变号；在 H1 同一双线性力臂律下，这会同时移动 up 与 down 阈值，并可在 pair_A 中不存在的正 down 阈值处产生切换。该机制是 H1 的几何变体，不是新的独立微观机制。

**关系或推导。** 在 H1 的 gamma* 表达式中作 ell_j -> -ell_j，得到交叉-平行阈值差：Delta gamma*(crossed-parallel) ≈ 2*k_c*ell_i*ell_j*sin(theta_j)/(k_d*L*cos(theta_i))。取 pair_B 的 k_c=k_d=0.19 N/cm、ell_i=ell_j=4.7 cm、L=6.3 cm，并按 theta_j 约 18-39 度估算，该式给约 4.6 cm 的位移量级；而实测 rotor2 up 的 other=-1 阈值 24.9 cm 相对 pair_A 的 3.5 cm 高 21.4 cm，模型明显低估。

**实测支持。** pair_B（record_id 100-107，±0.1 cm）中 rotor2：up/other=-1 为 24.9，up/other=+1 为 30.7；down/other=-1 为 +2.1，down/other=+1 为 +7.3。pair_A 的 rotor2 在 mount_l_cm=0 时 up=3.5、down=+0.1；pair_B 出现“正 down 阈值”且 up 阈值大幅抬高，符号模式与交叉耦合翻转 ell_j 的定性预测一致。定量上，公式只给约 4.6 cm 的位移，远小于 21.4 cm，故 H2 当前是符号层面的条件性解释，而非定量成功。

**适用假设。** pair_B 的“crossed”连接确实使耦合力矩中固定转子的力臂变号。；mount_l_cm=4.7 是两侧共同的耦合力臂 ell_i=ell_j；该语义未确认。；pair_B 的 k_c、k_d、L 与表列值一致，且钢线延伸尚未改变有效弹簧刚度。；pair_A 与 pair_B 的止挡角和 x_mount_offsets 不同；H2 假定这些几何差异可分离或至少不主导符号模式。；阈值单次测定、无重复；21.4 cm 差值不能全部归因于交叉耦合。

**区别后果。** 若把交叉对的耦合 mount 从 4.7 cm 逐步缩短到 0，H2 预测 pair_B 的阈值应近似二次地坍缩向 pair_A 的 ell=0 值（rotor2 up 约 3.5、down 约 0.1），且正 down 阈值先消失；纯止挡几何解释则预测阈值主要随止挡角 18.3/38.8 度移动，而不随耦合 mount 二次坍缩。

**竞争解释。** pair_A 与 pair_B 的止挡角、安装偏移和弹簧有效刚度不同；钢线延伸、接触/摩擦、未记录的预紧、以及 mount_l_cm 语义差异都可解释大幅位移。H2 的定量低估正是这些替代机制仍未被排除的证据。

**原始出处。** 最终交付响应 H2 段；pair_B 数据 record_id 100-107，并与 pair_A record_id 84-99 的 ell=0 阈值对照。该假设由轨迹中 H1 的同一力矩律直接变形而来。

**独立终评。** already_done；obvious_error。已覆盖：构型几何可控制相互作用符号，串行反铁磁与平行铁磁的对照已表明“改连接可翻转符号”；把交叉连接等效为 ell_j→−ell_j 是同一方向的力学实现。未解：模型仅给约 4.6 cm 位移而实测差 21.4 cm，且 pair_A/pair_B 止挡角与安装偏移混杂，定量机制未被来源支持。 在 H1 写出的 gamma 表达式下，代入 ell_j→-ell_j 得 Delta gamma*(crossed-parallel)≈2 k_c ell_i ell_j sinθ_j/(k_d L cosθ_i)，代 k_c=k_d=0.19、ell_i=ell_j=4.7、L=6.3、θ_j≈18-39° 可复算约 2-5 cm，文中“约 4.6 cm”本身不算离谱。但有三处显然错误：(1) H1 的 gamma 耦合项符号已反，正确力矩平衡下该 Delta 应带负号；(2) 该 Delta 定义在相同 ell_i,ell_j 的 crossed-parallel 对比，H2 却把 pair_B（ell=4.7）与 pair_A 的 ell=0 值 3.5/0.1 相比，21.4 cm 并不是该公式估计的量；同 ell=4.731 时，pair_A rotor2 up/other=-1=4.9，差为 20.0；down/other=-1=2.7，差为 2.1-2.7=-0.6；(3) 表中 pair_A 在 ell=0 已有 down=+0.1、在 ell=4.731 有 +2.7，故“pair_A 中不存在正 down 阈值”与数据不符。

- [Controlled pathways and sequential information processing in serially coupled mechanical hysterons.](https://doi.org/10.1073/pnas.2308414121)：覆盖构型改变符号的核心方向
- [Memory from coupled instabilities in unfolded crumpled sheets.](https://doi.org/10.1073/pnas.2200028119)：覆盖正负耦合并存

### H3 H3：network_C 为矩形 hysteron 网络并处于稳定 period-1 轨道（条件性）

**假说机制。** 把每个转子对看作一个矩形 hysteron：给定其他转子状态时，转子 i 在 gamma 超过 up 角点时翻到 +1，在低于 down 角点时翻到 -1，否则保持原态。network_C 的整体状态是四个符号的矢量；恒定振幅循环驱动会选择一个闭合轨道。该机制解释事件序列的重复性，并把同 drive 值的连续事件解释为未分辨的级联次序。

**关系或推导。** 对每个转子 i：若 gamma>gamma_up,i（在其余符号固定下）则 s_i=+1；若 gamma<gamma_down,i 则 s_i=-1；否则 s_i 保持不变。状态 S=(s1,s2,s3,s4)。矩形 hysteron 的轨道由角点 (gamma_down,i, gamma_up,i) 与耦合引起的角点移动决定；在周期驱动下，若返回同一 S 且驱动值在 ±0.1 cm 内重合，则记为 period-1 闭合。

**实测支持。** network_C 的 16 个有序事件（record_id 108-123）中，事件 1-8 与 9-16 的状态字符串逐一相同，drive_gamma_cm 也相同或在 0.1 cm 内（4.5、5.8、5.8、-4.3、-5.1、-5.1、5.9、-3.3）。事件 2/3 同为 +5.8，事件 5/6 同为 -5.1，符合“次序未分辨的近同时级联”，而不是两个已分辨的独立势垒。事件 7 在 +5.9、事件 8 在 -3.3，说明两者之间至少存在一次驱动反转；但导出表没有反转行，故反转位置本身未知。

**适用假设。** 每个转子对可用矩形 hysteron 描述，记忆仅由当前四个符号和角点决定。；驱动为恒定振幅、准静态循环；事件顺序保留，但事件间时间与反转位置未记录。；相同 drive 值的连续事件可视为同一驱动位置附近的未分辨次序，而非时间重合。；network_C 的止挡角、完整连接和耦合强度未知；本假设不声称已识别具体连接图。；四转子装置经过迭代调整，不是未选择的随机样本；事件表无独立重复。

**区别后果。** 若把驱动振幅从当前约 5.9 cm 略降到 5.9 cm 以下，矩形 hysteron 网络预测 period-1 闭合会被破坏，出现更长周期轨道或固定点；若由单个转子主导，则只应丢失 rotor4 在 +5.9 附近的事件，而其余事件仍按原顺序闭合。另一个检验：在事件 7 与 8 之间人为插入驱动反转并记录反转位置，应能区分“反转导致的顺序事件”与“网络内级联”。

**竞争解释。** 单转子主导、未分辨的事件时序、驱动漂移/蠕变、装置非平稳性、以及 network_C 未知连接均可产生类似重复序列；H3 只主张矩形 hysteron 网络是一个与现有事件顺序一致的条件性解释，未验证具体连接或角点。

**原始出处。** 最终交付响应 H3 段；network_C 数据 record_id 108-123。该段把事件 1-8 与 9-16 的重复性作为轨迹中实际提出的周期-1 证据。

**独立终评。** already_done；obvious_error。已覆盖：矩形 Preisach hysteron / 相互作用 hysteron 网络的 transition graph、循环驱动下的极限环与 RPM 已是标准问题；事件 1–8 与 9–16 的重复可由该框架解释。未解：network_C 的具体四转子拓扑、反转位置与“稳定 period-1 吸引子”而非协议截断；来源不提供该装置事件表，故具体识别仍未定。 H3把切换事件的最大gamma=5.9 cm写成当前驱动振幅，并由八个状态/驱动值重复定义period-1。这两步均不可由导出表推出。数据协议明确没有反转行，禁止以事件极值代替反转幅值；事件1-8的非零驱动增量符号为 +、-、-、+、-，至少包含三次反转，不能把这个状态块直接等同于通常一次上扫/下扫的驱动周期。矩形hysteron网络本身仍是条件模型，但period-1证据与5.9 cm振幅预测的论证有明确逻辑错误。

- [State transition graph of the Preisach model and the role of return-point memory](https://doi.org/10.1103/physreve.102.012122)：直接覆盖矩形 hysteron/Preisach 网络与周期驱动记忆
- [Profusion of transition pathways for interacting hysterons](https://doi.org/10.1103/physreve.104.054608)：覆盖相互作用 hysteron 网络的周期轨道/图多样性

## 补充执行与检查校正

AI-Scientist-v2 第二节点最初被 AST 检查误拦于 matplotlib.use("Agg")。修正这个检查后，在服务器原样执行已保存 node_1.py，退出码 0，无新模型调用；原始冻结结果保持不变。补充 stdout 和代码哈希见 controller_only/server_node_verification/EXECUTION.json。该补充进一步发现八状态块内至少三次驱动反转，因此八个事件的重复不能等同于一个驱动周期。

EvoScientist H3 的独立终评原给 no_obvious_error；控制端复算指出把最大切换位置 5.9 cm 当作当前驱动振幅，以及把状态块重复直接定义为 period-1，均超出给定记录。原终评原样保留，报告采用 controller_only/CONTROLLER_AUDIT.json 中的校正。

初始终评对相似研究的判断偏重装置细节，随后以同一历史时间边界共享检索并复核研究方向；报告采用 BROAD_SCOPE_AUDIT.json 的判断，并保留初判。

## 证据和边界

原始回复、工具记录、原版讨论/计算结果、假说出处和冻结清单均保存在 runs/。FINAL.json 是各架构实际轨迹的统一提取；独立终评单独保存且未返回生成系统。no_close_work_found 仅表示本次有界检索未找到高度相近工作；实验验证和世界新颖性仍须分别建立。

同一个小型场景、短程和不同 native 角色数支持比较具体内容与开销，架构整体优劣需要重复运行和更广场景。
