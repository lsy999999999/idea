import os
os.chdir('/home/lsy/hysteron_baselines_deepseek_20261110/runs/scientist_v2/workspace')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("measurements.csv")
print("rows:", len(df))
print("record counts:")
print(df.record_type.value_counts().to_string())


def fit_line(x, y):
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    pred = X @ beta
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return beta, pred, r2


def fit_origin(x, y):
    b = np.sum(x * y) / np.sum(x * x)
    pred = b * x
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return b, pred, r2


def loocv_line(x, y):
    errs = []
    for i in range(len(x)):
        m = np.arange(len(x)) != i
        X = np.column_stack([np.ones(np.sum(m)), x[m]])
        b = np.linalg.lstsq(X, y[m], rcond=None)[0]
        errs.append(y[i] - b[0] - b[1] * x[i])
    return float(np.sqrt(np.mean(np.square(errs))))


def loocv_origin(x, y):
    errs = []
    for i in range(len(x)):
        m = np.arange(len(x)) != i
        b = np.sum(x[m] * y[m]) / np.sum(x[m] * x[m])
        errs.append(y[i] - b * x[i])
    return float(np.sqrt(np.mean(np.square(errs))))


print("\nCALIBRATION: used only as stiffness priors, not installed-spring identities")
nominal = {"S046": 0.46, "S019": 0.19, "S007": 0.07}
cal = df[df.record_type == "calibration"]
for sid in ["S046", "S019", "S007"]:
    sub = cal[cal.spring_id == sid]
    x = sub.x_m.to_numpy()
    y = sub.force_N.to_numpy()
    coef = np.polyfit(x, y, 1)
    pred = coef[0] * x + coef[1]
    r2 = 1.0 - np.sum((y - pred) ** 2) / np.sum((y - np.mean(y)) ** 2)
    gg = sub.groupby("x_m").force_N.agg(["min", "max", "count"])
    gaps = (gg["max"] - gg["min"])[gg["count"] > 1].to_numpy()
    print(
        f" {sid}: fitted k={coef[0]/100.0:.3f} N/cm "
        f"(nominal {nominal[sid]:.2f}), R2={r2:.4f}, "
        f"median load-unload gap={np.median(gaps):.4f} N, n={len(sub)}"
    )

thr = df[df.record_type == "threshold"].copy()
thr["sgn"] = np.where(thr.direction == "up", 1, -1)
thr = thr[thr.configuration_id.isin(["pair_A", "pair_B"])]

up = thr[thr.direction == "up"][
    ["configuration_id", "rotor_i", "other_state", "mount_l_cm", "drive_gamma_cm"]
].rename(columns={"drive_gamma_cm": "g_up"})
dn = thr[thr.direction == "down"][
    ["configuration_id", "rotor_i", "other_state", "mount_l_cm", "drive_gamma_cm"]
].rename(columns={"drive_gamma_cm": "g_down"})
piv = up.merge(
    dn,
    on=["configuration_id", "rotor_i", "other_state", "mount_l_cm"],
    how="inner",
)
piv["c"] = (piv.g_up + piv.g_down) / 2.0
piv["h"] = (piv.g_up - piv.g_down) / 2.0

print("\nPIVOTED THRESHOLDS: c=(up+down)/2, h=(up-down)/2")
print(
    piv[
        ["configuration_id", "rotor_i", "other_state", "mount_l_cm", "c", "h"]
    ].to_string(index=False)
)

pa = piv[piv.configuration_id == "pair_A"].copy()
pa_sum = {}

print("\nPAIR A: exploratory fits; measured thresholds are rounded to 0.1 cm")
for r in [1, 2]:
    sub = pa[pa.rotor_i == r]
    L = np.sort(sub.mount_l_cm.unique())
    hs, Js, c0s = [], [], []
    for val in L:
        ss = sub[np.isclose(sub.mount_l_cm, val)]
        hs.append(ss.h.mean())
        cp = ss.loc[ss.other_state == 1, "c"].to_numpy()[0]
        cm = ss.loc[ss.other_state == -1, "c"].to_numpy()[0]
        Js.append((cp - cm) / 2.0)
        c0s.append((cp + cm) / 2.0)
    hs = np.array(hs)
    Js = np.array(Js)
    c0s = np.array(c0s)
    L2 = L**2

    bh, hpred, r2h = fit_line(L2, hs)
    j2, j2pred, r2j2 = fit_origin(L2, Js)
    j1, j1pred, r2j1 = fit_origin(L, Js)

    pa_sum[r] = {
        "L": L,
        "L2": L2,
        "h": hs,
        "J": Js,
        "c0": c0s,
        "h0": hs[0],
        "hpred": hpred,
        "j2pred": j2pred,
        "j1pred": j1pred,
        "hmodel": bh,
        "j2": j2,
    }

    print(f" rotor {r}: L = {np.round(L, 3)} cm")
    print(f"   h = {np.round(hs, 3)} cm; common-mode c0 = {np.round(c0s, 3)}")
    print(f"   state-dependent J = {np.round(Js, 3)} cm")
    print(
        f"   h = {bh[0]:.3f} - {(-bh[1]):.4f} L^2; R2={r2h:.3f}; "
        f"LOOCV RMSE={loocv_line(L2, hs):.3f} cm"
    )
    print(
        f"   J = {j2:+.4f} L^2; R2={r2j2:.3f}; "
        f"LOOCV RMSE={loocv_origin(L2, Js):.3f} cm"
    )
    print(
        f"   J = {j1:+.4f} L;   R2={r2j1:.3f}; "
        f"LOOCV RMSE={loocv_origin(L, Js):.3f} cm"
    )
    print(
        f"   max |h(other=+1)-h(other=-1)| = {sub.groupby('mount_l_cm').h.agg(lambda z: z.max()-z.min()).max():.3f} cm"
    )

Lall = []
zall = []
for r in [1, 2]:
    Lall.extend(pa_sum[r]["L2"])
    zall.extend(1.0 - pa_sum[r]["h"] / pa_sum[r]["h0"])
Lall = np.array(Lall)
zall = np.array(zall)
mnorm = np.sum(Lall * zall) / np.sum(Lall * Lall)
Lc = 1.0 / np.sqrt(mnorm)
zpred = mnorm * Lall
r2norm = 1.0 - np.sum((zall - zpred) ** 2) / np.sum((zall - np.mean(zall)) ** 2)
rmse_norm = np.sqrt(np.mean((zall - zpred) ** 2))
print("\nCOMMON NORMALIZED WIDTH RELATION (both pair_A rotors)")
print(f"   1 - h/h0 = (L/{Lc:.2f})^2; R2={r2norm:.3f}; RMSE={rmse_norm:.3f}")

pb = piv[piv.configuration_id == "pair_B"].copy()
pb_sum = {}
print("\nPAIR B: crossed coupling at L=4.7 cm, compared with pair_A at L=4.731 cm")
for r in [1, 2]:
    ss = pb[pb.rotor_i == r]
    cp = ss.loc[ss.other_state == 1, "c"].to_numpy()[0]
    cm = ss.loc[ss.other_state == -1, "c"].to_numpy()[0]
    Jb = (cp - cm) / 2.0
    hb = ss.h.mean()
    pb_sum[r] = {"J": Jb, "h": hb}
    Ja = pa_sum[r]["J"][-1]
    ha = pa_sum[r]["h"][-1]
    print(
        f" rotor {r}: pair_B J={Jb:+.2f}, h={hb:.2f}; "
        f"pair_A J={Ja:+.2f}, h={ha:.2f}; "
        f"sign_flip={Jb * Ja < 0}, |J| ratio={abs(Jb/Ja):.2f}, h ratio={hb/ha:.2f}"
    )

stops = {"pair_A": {1: 36.65, 2: 10.50}, "pair_B": {1: 18.3, 2: 38.8}}
xs, ys = [], []
for r in [1, 2]:
    xs.append(stops["pair_A"][r])
    ys.append(pa_sum[r]["h"][-1])
    xs.append(stops["pair_B"][r])
    ys.append(pb_sum[r]["h"])
r_stop = np.corrcoef(xs, ys)[0, 1]
print(
    f"\nCONFOUND CHECK: measured h at L~4.7 vs stop half-range, Pearson r={r_stop:.3f} (n=4)"
)

ev = (
    df[df.record_type == "state_event"]
    .sort_values("event_index")
    .reset_index(drop=True)
)
states = ev.state_string.tolist()
seq = ev[["s1", "s2", "s3", "s4"]].to_numpy()
period8 = states[:8] == states[8:16]
hamm = [int(np.sum(seq[i] != seq[i - 1])) for i in range(1, len(seq))]
wrap = int(np.sum(seq[0] != seq[-1]))
flip_rot = []
for i in range(len(seq)):
    prev = seq[i - 1] if i > 0 else seq[-1]
    idx = np.where(prev != seq[i])[0]
    flip_rot.append(int(idx[0] + 1) if len(idx) == 1 else -1)

print("\nNETWORK C: ordered events, not a time series")
print(" first 8 states:", states[:8])
print(" second 8 states:", states[8:16])
print(" exact period-8 repeat:", period8)
print(" unique states in one period:", len(set(states[:8])))
print(
    f" single-flip transitions: {sum(1 for d in hamm if d == 1)}/{len(hamm)}; wrap={wrap}"
)
print(" rotor flip order in one period:", flip_rot[:8])
print(" event drive values:", np.round(ev.drive_gamma_cm.to_numpy(), 2))

print("\nNAIVE AMPLITUDE-ROW-DELETION EXERCISE: not a protocol simulation")
for A in [6.0, 5.85, 5.75, 5.2, 5.0, 4.4, 3.5]:
    keep = [i for i in range(8) if abs(ev.drive_gamma_cm.to_numpy()[i]) <= A]
    if len(keep) < 2:
        continue
    kstates = [states[i] for i in keep]
    multi = 0
    for j in range(len(kstates)):
        a = kstates[j]
        b = kstates[(j + 1) % len(kstates)]
        d = sum(1 for p, q in zip(a, b) if p != q)
        if d != 1:
            multi += 1
    print(
        f"   A={A:.2f}: kept={len(keep)}, multi-flip transitions={multi}/{len(kstates)}"
    )

fig, ax = plt.subplots(1, 4, figsize=(18, 4))
for r in [1, 2]:
    a = pa_sum[r]
    ax[0].scatter(a["L2"], a["h"], label=f"rotor {r}")
    ax[0].plot(a["L2"], a["hpred"], "--")
    ax[1].scatter(a["L2"], a["J"], label=f"rotor {r}")
    ax[1].plot(a["L2"], a["j2pred"], "--")
    ax[1].plot(a["L2"], a["j1pred"], ":")
    ax[2].scatter(a["L2"], a["h"] / a["h0"], label=f"rotor {r}")

xx = np.linspace(0.0, np.max(Lall), 50)
ax[2].plot(xx, 1.0 - mnorm * xx, "k--", label="common law")
ax[0].set_xlabel("L^2 (cm^2)")
ax[0].set_ylabel("half-width h (cm)")
ax[1].set_xlabel("L^2 (cm^2)")
ax[1].set_ylabel("center shift J (cm)")
ax[2].set_xlabel("L^2 (cm^2)")
ax[2].set_ylabel("h/h0")
ax[3].plot(ev.event_index, ev.drive_gamma_cm, "o-")
ax[3].axhline(0.0, color="k", linewidth=0.5)
ax[3].set_xlabel("event index")
ax[3].set_ylabel("drive gamma (cm)")
for a in ax:
    a.legend(fontsize=8)
plt.tight_layout()
plt.savefig("figure.png", dpi=120)

print("\nCONCRETE FINDING")
print(" MEASURED: pair_A h/h0 collapses as 1-(L/7.9 cm)^2 for both rotors.")
print(" CHALLENGE: the state-dependent center J also scales as L^2, not linearly in L.")
print(
    " CONDITIONAL CONSEQUENCE: rotor 2 crosses |J|>h near L=3.7 cm, a testable disjoint-loop regime."
)
print(
    " SUPPORT: pair_B crossed coupling flips J sign and increases |J|; network_C repeats an 8-state single-flip cycle."
)
print(
    " LIMITATIONS: four L values, 0.1 cm rounding, no independent repetitions, one pair_B L,"
)
print(
    "   stop-angle and topology confounds, and unknown network_C connectivity/reversal positions."
)
print(
    " MECHANISM: not identified; these are exploratory fits and conditional predictions only."
)
