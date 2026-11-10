import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from scipy.integrate import quad
from sklearn.metrics import precision_recall_curve
import figstyle  # noqa: F401
from figstyle import OI, QCOL, FIGDIR

R = json.load(open("results/results.json"))


def save(fig, name):
    fig.savefig(f"{FIGDIR}/{name}.pdf")
    fig.savefig(f"assets/{name}.png", dpi=170)
    plt.close(fig)


# ------------------------------------------------------------------ Fig 1: DE plane
z = np.load("results/parts/e3_0.npz")
FE, D, Q = z["FE"], z["D"], z["Q"]
rng = np.random.default_rng(3)
fig, ax = plt.subplots(figsize=(5.3, 3.35))
fig.subplots_adjust(left=0.27, right=0.95, bottom=0.14, top=0.90)
for q, (x0, y0) in {0: (0, -1.0), 1: (0, 1.5), 2: (0.5, -1.0), 3: (0.5, 1.5)}.items():
    h = 2.5 if y0 < 0 else 3.5
    ax.add_patch(Rectangle((x0, y0), 0.5, h, color=QCOL[q], alpha=0.07, lw=0, zorder=0))
ax.scatter(FE, D + rng.uniform(-0.27, 0.27, len(D)), s=3.2, c=[QCOL[int(q)] for q in Q],
           alpha=0.75, lw=0, zorder=2, rasterized=True)
ax.axvline(0.5, color="#555555", lw=0.7, ls=(0, (4, 2)), zorder=1)
ax.axhline(1.5, color="#555555", lw=0.7, ls=(0, (4, 2)), zorder=1)
n = len(Q)
labs = {0: ("Benign", 0.25, -0.68), 1: ("Cheap talk", 0.25, 4.62),
        2: ("Silent risk", 0.75, -0.68), 3: ("Aware", 0.75, 4.62)}
for q, (name, x, y) in labs.items():
    ax.text(x, y, f"{name} ({100 * np.mean(Q == q):.0f}%)", ha="center", va="center",
            color=QCOL[q] if q != 0 else "#555555", fontsize=8.5, fontweight="bold")
ax.set_xlim(0, 1); ax.set_ylim(-1.0, 5.0)
ax.set_yticks(range(5))
ax.set_yticklabels(["0  none", "1  generic", "2  hazard-specific", "3  quantified",
                    "4  quantified + scenarios"])
ax.set_xlabel(r"Modelled exposure percentile, $F_E(E_i)$")
ax.set_ylabel(r"Disclosure level $D_i$")
ax.text(0.5, 5.12, r"$\tau_E$", ha="center", va="bottom", fontsize=8.5, color="#555555")
ax.text(1.012, 1.5, r"$\tau_D$", ha="left", va="center", fontsize=8.5, color="#555555")
save(fig, "fig_de_plane")

# ------------------------------------------------------------------ Fig 5: master curve
E1 = R["E1"]
ells, sigs = E1["ells"], E1["sigmas"]
am, asd = np.array(E1["asset_mean"]), np.array(E1["asset_sd"])


def exact(ratio):
    a = ratio ** 2
    v, _ = quad(lambda t: np.arcsin(0.5 * np.exp(-a * t)) * np.exp(-t), 0, np.inf, limit=200)
    return 6 / np.pi * v


xs = np.logspace(-3.3, 1.6, 300)
fig, ax = plt.subplots(figsize=(5.6, 2.75))
fig.subplots_adjust(left=0.10, right=0.76, bottom=0.17, top=0.96)
ax.plot(xs, [exact(x) for x in xs], color="black", lw=1.0, zorder=2, label="Theory (Prop. 1)")
cols = plt.cm.viridis(np.linspace(0.0, 0.9, len(ells)))
for i, ell in enumerate(ells):
    r = np.array(sigs) / ell
    ax.errorbar(r, am[i, :len(sigs)], yerr=asd[i, :len(sigs)], fmt="o", ms=3.4, color=cols[i],
                mec="white", mew=0.35, elinewidth=0.6, capsize=0, zorder=3,
                label=fr"$\ell$ = {ell:,} km")
ax.axvline(1 / 3, color="#777777", lw=0.7, ls=(0, (1.5, 1.5)), zorder=1)
ax.text(0.40, 0.985, r"$\sigma = \ell/3$", ha="left", va="center", fontsize=8, color="#555555")
ax.set_xscale("log"); ax.set_xlim(5e-4, 40); ax.set_ylim(-0.03, 1.05)
ax.set_xlabel(r"Relative geolocation error $\sigma/\ell$")
ax.set_ylabel("Asset-level Spearman $\\rho_S$")
hs = [Line2D([], [], color="black", lw=1.0)] + [Line2D([], [], marker="o", ls="none", ms=4, color=cols[i], mec="white", mew=0.35) for i in range(len(ells))]
ls_ = ["Theory (Prop. 1)"] + [fr"$\ell$ = {e:,} km" for e in ells]
ax.legend(hs, ls_, loc="center left", bbox_to_anchor=(1.02, 0.5), handletextpad=0.5, labelspacing=0.45)
save(fig, "fig_master_curve")

# ------------------------------------------------------------------ Fig 6: firm heatmap
fm = np.array(E1["firm_mean"])
fig, ax = plt.subplots(figsize=(5.6, 2.95))
fig.subplots_adjust(left=0.13, right=0.88, bottom=0.17, top=0.97)
im = ax.imshow(fm, cmap="viridis", vmin=0, vmax=1, aspect="auto")
for i in range(fm.shape[0]):
    for j in range(fm.shape[1]):
        v = fm[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7.3,
                color="white" if v < 0.55 else "black")
ax.axvline(len(sigs) - 0.5, color="white", lw=2.2)
ax.set_xticks(range(len(sigs) + 1)); ax.set_xticklabels([str(s) for s in sigs] + ["country"])
ax.set_yticks(range(len(ells))); ax.set_yticklabels([f"{e:,}" for e in ells])
ax.set_xlabel(r"Geolocation error $\sigma$ (km) or country-level geocode")
ax.set_ylabel(r"Hazard correlation length $\ell$ (km)")
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
cax = fig.add_axes([0.90, 0.17, 0.022, 0.80])
cb = fig.colorbar(im, cax=cax); cb.set_label(r"Firm-level Spearman $\rho_S$", labelpad=4)
cb.outline.set_linewidth(0.5); cb.ax.tick_params(labelsize=7, width=0.5, length=2.5)
save(fig, "fig_firm_heatmap")

# ------------------------------------------------------------------ Fig 7: E2 accuracy
E2 = R["E2"]
acc, sd = np.array(E2["acc_mean"]), np.array(E2["acc_sd"])
eps = E2["eps"]
styles = [("Exact coordinates", "black", "o", "-"), (r"$\sigma$ = 5 km", OI["blue"], "s", "-"),
          (r"$\sigma$ = 25 km", OI["green"], "^", "-"), (r"$\sigma$ = 100 km", OI["orange"], "D", "-"),
          ("Country-level", OI["verm"], "v", (0, (4, 2)))]
fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.75), sharey=True)
fig.subplots_adjust(left=0.085, right=0.985, bottom=0.27, top=0.90, wspace=0.08)
for a, ax in enumerate(axes):
    for j, (lab, c, m, ls) in enumerate(styles):
        ax.fill_between(eps, acc[a, j] - sd[a, j], acc[a, j] + sd[a, j], color=c, alpha=0.12, lw=0)
        ax.plot(eps, acc[a, j], color=c, marker=m, ms=3.6, lw=1.0, ls=ls, mec="white", mew=0.35,
                label=lab)
    ax.set_title(["(a) Local hazard, $\\ell$ = 25 km", "(b) Regional hazard, $\\ell$ = 500 km"][a])
    ax.set_xlabel(r"Extraction error rate $\varepsilon$")
    ax.set_xticks(eps); ax.set_ylim(0.38, 1.02); ax.grid(axis="y", color="#EEEEEE", lw=0.5)
axes[0].set_ylabel("Quadrant accuracy")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=5, bbox_to_anchor=(0.53, 0.0), columnspacing=1.4,
           handlelength=2.0)
save(fig, "fig_quadrant_accuracy")

# ------------------------------------------------------------------ Fig 8: E3 propagation
parts = [np.load(f"results/parts/e3_{r}.npz") for r in range(20)]
y = np.concatenate([p["y"] for p in parts])
P = {k: np.concatenate([p[k] for p in parts]) for k in ["p_extr", "p_loc", "p_full"]}
yh = np.concatenate([p["yhat"] for p in parts])
meth = [("p_extr", "Extraction only", OI["orange"], "s"),
        ("p_loc", "Location + hazard model", OI["green"], "^"),
        ("p_full", "Full propagation", OI["blue"], "o")]
fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.05))
fig.subplots_adjust(left=0.085, right=0.985, bottom=0.31, top=0.91, wspace=0.28)
ax = axes[0]
ax.plot([0, 1], [0, 1], color="#999999", lw=0.8, ls=(0, (3, 2)), zorder=1)
for k, lab, c, m in meth:
    b = np.minimum((P[k] * 10).astype(int), 9)
    mx = [P[k][b == i].mean() for i in range(10) if (b == i).sum() >= 30]
    my = [y[b == i].mean() for i in range(10) if (b == i).sum() >= 30]
    ax.plot(mx, my, color=c, marker=m, ms=3.8, lw=1.0, mec="white", mew=0.35, label=lab, zorder=3)
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
ax.set_xlabel(r"Predicted $P(\mathrm{silent})$"); ax.set_ylabel("Observed frequency")
ax.set_title("(a) Reliability")
ax = axes[1]
pr_stats = {}
for k, lab, c, m in meth:
    pr, rc, th = precision_recall_curve(y, P[k])
    ax.plot(rc, pr, color=c, lw=1.1, label=lab)
    pr_stats[k] = (pr, rc, th)
pt_prec, pt_rec = y[yh == 1].mean(), yh[y == 1].mean()
ax.plot(pt_rec, pt_prec, marker="*", ms=9, color="black", ls="none", label="Point estimate", zorder=4)
sel = P["p_full"] >= 0.8
ax.plot(y[sel].sum() / y.sum(), y[sel].mean(), marker="D", ms=5, mfc="white", mec=OI["blue"], mew=1.2,
        ls="none", label=r"Full, flag if $P \geq 0.8$", zorder=4)
ax.axhline(y.mean(), color="#999999", lw=0.8, ls=(0, (3, 2)))
ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
ax.set_xlabel("Recall (share of silent-risk firms flagged)"); ax.set_ylabel("Precision")
ax.set_title("(b) Precision–recall")
h1, l1 = axes[0].get_legend_handles_labels(); h2, l2 = axes[1].get_legend_handles_labels()
base = Line2D([], [], color="#999999", lw=0.8, ls=(0, (3, 2)))
h = [h1[0], h2[3], h1[1], h2[4], h1[2], base]
l = [l1[0], l2[3], l1[1], l2[4], l1[2], "Perfect calibration / base rate"]
fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.53, 0.0), columnspacing=1.6,
           handlelength=2.0)
save(fig, "fig_propagation")

# numbers for the text: precision of full propagation at the point estimate's recall
pr, rc, th = pr_stats["p_full"]
idx = np.argmin(np.abs(rc[:-1] - pt_rec))
pr2, rc2, _ = pr_stats["p_extr"]; idx2 = np.argmin(np.abs(rc2[:-1] - pt_rec))
extra = {"point_prec_pooled": float(pt_prec), "point_rec_pooled": float(pt_rec),
         "full_prec_at_point_recall": float(pr[idx]), "extr_prec_at_point_recall": float(pr2[idx2]),
         "fig1_shares": [float(np.mean(Q == q)) for q in range(4)],
         "e2_max_sd": float(sd.max())}
json.dump(extra, open("results/results_extra.json", "w"), indent=1)
print(extra)
