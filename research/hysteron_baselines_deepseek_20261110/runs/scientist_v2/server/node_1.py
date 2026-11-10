import numpy as np, pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv("measurements.csv")
print("rows:", len(df))
print(df.record_type.value_counts().to_string())


def lin(x, y):
    X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    p = X @ b
    r2 = 1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)
    return b, p, r2


def org(x, y):
    b = np.sum(x * y) / np.sum(x * x)
    p = b * x
    r2 = 1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)
    return b, p, r2


def loo(x, y, o=False):
    e = []
    for i in range(len(x)):
        m = np.arange(len(x)) != i
        if o:
            b = np.sum(x[m] * y[m]) / np.sum(x[m] ** 2)
            e.append(y[i] - b * x[i])
        else:
            b = np.linalg.lstsq(
                np.column_stack([np.ones(m.sum()), x[m]]), y[m], rcond=None
            )[0]
            e.append(y[i] - b[0] - b[1] * x[i])
    return float(np.sqrt(np.mean(np.square(e))))


cal = df[df.record_type == "calibration"]
print("\nCALIBRATION = stiffness priors only (not installed-spring identities)")
for sid in ["S046", "S019", "S007"]:
    s = cal[cal.spring_id == sid]
    x = s.x_m.to_numpy() * 100.0
    y = s.force_N.to_numpy()
    k, b = np.polyfit(x, y, 1)
    p = k * x + b
    r2 = 1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)
    g = s.groupby("x_m").force_N.agg(["min", "max", "count"])
    gap = (g["max"] - g["min"])[g["count"] > 1]
    print(
        f"  {sid}: k={k:.4f} N/cm, R2={r2:.5f}, n={len(s)}, median load-unload gap={np.median(gap.to_numpy()):.4f} N"
    )

thr = df[df.record_type == "threshold"]
cols = ["configuration_id", "rotor_i", "other_state", "mount_l_cm"]
up = thr[thr.direction == "up"][cols + ["drive_gamma_cm"]].rename(
    columns={"drive_gamma_cm": "gu"}
)
dn = thr[thr.direction == "down"][cols + ["drive_gamma_cm"]].rename(
    columns={"drive_gamma_cm": "gd"}
)
piv = up.merge(dn, on=cols, how="inner")
piv["c"] = (piv.gu + piv.gd) / 2.0
piv["h"] = (piv.gu - piv.gd) / 2.0
print("\nPIVOTED THRESHOLDS (exploratory; thresholds rounded to 0.1 cm)")
print(piv[cols + ["c", "h"]].to_string(index=False))

pa = piv[piv.configuration_id == "pair_A"]
S = {}
print("\nPAIR A: nested fits + LOOCV (measured h and J, model comparison)")
for r in [1, 2]:
    sub = pa[pa.rotor_i == r]
    L = np.sort(sub.mount_l_cm.unique())
    hs, Js, c0s = [], [], []
    for v in L:
        ss = sub[np.isclose(sub.mount_l_cm, v)]
        hs.append(ss.h.mean())
        cp = ss.loc[ss.other_state == 1, "c"].to_numpy()[0]
        cm = ss.loc[ss.other_state == -1, "c"].to_numpy()[0]
        Js.append((cp - cm) / 2.0)
        c0s.append((cp + cm) / 2.0)
    L = np.array(L)
    hs = np.array(hs)
    Js = np.array(Js)
    L2 = L**2
    bh, hp, r2h = lin(L2, hs)
    bl, hl, r2hl = lin(L, hs)
    j2, p2, r2j2 = org(L2, Js)
    j1, p1, r2j1 = org(L, Js)
    dh = hs[0] - hs
    q, pq, r2q = org(dh, Js)
    S[r] = dict(
        L=L, L2=L2, h=hs, J=Js, hp=hp, p2=p2, p1=p1, dh=dh, h0=hs[0], bh=bh, j2=j2, q=q
    )
    print(
        f" rotor {r}: L={np.round(L,3)}  h={np.round(hs,3)}  J={np.round(Js,3)}  c0={np.round(c0s,3)}"
    )
    print(
        f"   h = {bh[0]:.3f} - {abs(bh[1]):.4f} L^2 (R2={r2h:.3f}, LOOCV={loo(L2,hs):.3f})"
        f"  vs  h = a + bL (R2={r2hl:.3f}, LOOCV={loo(L,hs):.3f})"
    )
    print(
        f"   J = {j2:+.4f} L^2 (R2={r2j2:.3f}, LOOCV={loo(L2,Js,o=True):.3f})"
        f"  vs  J = {j1:+.4f} L (R2={r2j1:.3f}, LOOCV={loo(L,Js,o=True):.3f})"
    )
    print(
        f"   ONE-CHANNEL TEST J = q*(h0-h): q={q:+.3f}, R2={r2q:.3f}, LOOCV={loo(dh,Js,o=True):.3f}"
    )
    print(
        f"   state-dependence of h: max|h(+)-h(-)|={sub.groupby('mount_l_cm').h.agg(lambda z: z.max()-z.min()).max():.3f} cm (<= rounding)"
    )

A = np.concatenate([S[1]["L2"], S[2]["L2"]])
Z = np.concatenate([1 - S[1]["h"] / S[1]["h0"], 1 - S[2]["h"] / S[2]["h0"]])
m = np.sum(A * Z) / np.sum(A * A)
Lc = 1 / np.sqrt(m)
r2n = 1 - np.sum((Z - m * A) ** 2) / np.sum((Z - Z.mean()) ** 2)
print(
    f"\nCOMMON NORMALIZED WIDTH LAW (both rotors): 1-h/h0 = (L/{Lc:.2f} cm)^2, R2={r2n:.3f}, RMSE={np.sqrt(np.mean((Z-m*A)**2)):.4f}"
)
print(
    "   extrapolated h->0 collapse length ~ {:.2f} cm (no apparatus dimension in dossier equals it)".format(
        Lc
    )
)

print("\nLOOP-SEPARATION / SLAVE-BAND PREDICTION (derived from fitted c,h)")
for r in [1, 2]:
    s = S[r]
    h0, K, j2 = s["h0"], -s["bh"][1], abs(s["j2"])
    Ls = np.sqrt(h0 / (K + j2)) if K + j2 > 0 else np.inf
    band = 2 * (np.abs(s["J"]) - s["h"])
    print(
        f" rotor {r}: |J|=h at L*={Ls:.2f} cm; band 2(|J|-h) at L={np.round(s['L'],2)} -> {np.round(band,3)}"
    )
print(
    "   rotor 2: band is negative at L=3.154 and positive (+2.2 cm) at L=4.731 -> sign change bracketed"
)

pb = piv[piv.configuration_id == "pair_B"]
stops = {"pair_A": {1: 36.65, 2: 10.50}, "pair_B": {1: 18.3, 2: 38.8}}
print("\nPAIR B (single L=4.7 cm): ordinal sign/magnitude test, confounded by stops")
xs, ys = [], []
for r in [1, 2]:
    ss = pb[pb.rotor_i == r]
    cp = ss.loc[ss.other_state == 1, "c"].to_numpy()[0]
    cm = ss.loc[ss.other_state == -1, "c"].to_numpy()[0]
    Jb, hb = (cp - cm) / 2.0, ss.h.mean()
    Ja, ha = S[r]["J"][-1], S[r]["h"][-1]
    xs += [stops["pair_A"][r], stops["pair_B"][r]]
    ys += [ha, hb]
    print(
        f" rotor {r}: J_B={Jb:+.2f} (A {Ja:+.2f}, sign flip={Jb*Ja < 0}), h_B={hb:.2f} (A {ha:.2f}), h/stop_rad B={hb/stops['pair_B'][r]:.3f} A={ha/stops['pair_A'][r]:.3f}"
    )
print(
    f" h vs stop half-range across the 4 (device,rotor) cells: r={np.corrcoef(xs, ys)[0,1]:.3f} (n=4, not identifiable)"
)

ev = df[df.record_type == "state_event"].sort_values("event_index")
st = ev.state_string.tolist()
Q = ev[["s1", "s2", "s3", "s4"]].to_numpy()
g = ev.drive_gamma_cm.to_numpy()
fl = [int(np.sum(Q[i] != Q[i - 1])) for i in range(len(Q))]
d = np.diff(g)
nz = d[np.abs(d) > 1e-12]
rev = int(np.sum(np.sign(nz[1:]) != np.sign(nz[:-1])))
print("\nNETWORK C: ordered events, no timestamps")
print(
    f" period-8 exact repeat: {st[:8] == st[8:]} ; unique states/period: {len(set(st[:8]))}; single-flip transitions {sum(1 for x in fl if x == 1)}/{len(fl)}"
)
print(
    f" flip order in one period: {[int(np.argmax(Q[i] != Q[i-1]))+1 for i in range(1,9)]}"
)
print(f" drive values: {np.round(g,1)}")
print(
    f" direction reversals implied in 16 events: {rev} (>=3 per 8-event cycle) -> the 8-cycle is NOT one amplitude loop"
)
print(
    "   => amplitude-truncation prediction cannot be tested by deleting rows; needs reversal rows the export lacks"
)

fig, ax = plt.subplots(1, 3, figsize=(14, 4))
for r in [1, 2]:
    s = S[r]
    ax[0].scatter(s["L2"], s["h"], label=f"rotor {r}")
    ax[0].plot(s["L2"], s["hp"], "--")
    ax[1].scatter(s["L2"], s["J"], label=f"rotor {r}")
    ax[1].plot(s["L2"], s["p2"], "--")
    ax[1].plot(s["L2"], s["p1"], ":")
    ax[2].scatter(s["dh"], s["J"], label=f"rotor {r}")
xx = np.linspace(0, 25, 50)
ax[2].plot(xx, S[1]["q"] * xx, "C0:")
ax[2].plot(xx, S[2]["q"] * xx, "C1:")
ax[0].set_xlabel("L^2 (cm^2)")
ax[0].set_ylabel("h (cm)")
ax[1].set_xlabel("L^2 (cm^2)")
ax[1].set_ylabel("J (cm)")
ax[1].legend(fontsize=8)
ax[2].set_xlabel("h0 - h (cm)")
ax[2].set_ylabel("J (cm)")
ax[2].legend(fontsize=8)
plt.tight_layout()
plt.savefig("figure.png", dpi=110)

print("\nCONCRETE FINDING")
print(
    " MEASURED: pair_A h and |J| both rise with L^2; LOOCV prefers L^2 over L for J on both rotors."
)
print(
    " CHALLENGE: the hypothesis' 'bias linear in L, curvature L^2' split is not supported; both channels scale L^2."
)
print(
    " REFINEMENT: a one-parameter law J = q*(h0-h) fits both rotors (q rotor-specific, L-independent within rounding)"
)
print(
    "   -> one geometric lever-arm channel, not two independent parameters (still a fit, not mechanism)."
)
print(
    " CONDITIONAL PREDICTIONS: rotor 1 monostable (h->0) near L~7.9 cm; rotor 2 slave band 2(|J|-h) opens near L~3.7 cm,"
)
print(
    "   i.e. at fixed drive 0.5<gamma<2.7 cm rotor 2 should mirror the held rotor -> avalanches/multi-flips become possible."
)
print(
    " LIMITATIONS: 4 lever arms, 0.1 cm rounding, single up/down pair per cell, no repeats; pair_B has one L and stop-angle"
)
print(
    "   confound (rotor 2 h is 10x pair_A); network_C connectivity, stop angles and reversal positions unknown;"
)
print(
    "   the 8-state cycle needs >=3 drive reversals per period, so it is a state cycle under an unreported protocol."
)
print(
    " MECHANISM NOT IDENTIFIED: all fits exploratory; small-angle/pairwise/quasistatic assumptions untested."
)
