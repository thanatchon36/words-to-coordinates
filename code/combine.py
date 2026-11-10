"""Merges partial results in results/parts into results/results.json."""
import json, numpy as np
from scipy.integrate import quad
from sklearn.metrics import average_precision_score
from config import *  # noqa: F401,F403

def exact_spearman(ratio):
    a = ratio ** 2
    v, _ = quad(lambda t: np.arcsin(0.5 * np.exp(-a * t)) * np.exp(-t), 0, np.inf, limit=200)
    return 6 / np.pi * v

def corr_spearman(ratio, c):
    rho = 1 / (1 + ratio ** 2); rc = (rho - c) / (1 - c)
    return 6 / np.pi * np.arcsin(rc / 2)

out = {}
A = np.stack([np.load(f"results/parts/e1_{i}.npz")["A"] for i in range(len(ELLS))])
F = np.stack([np.load(f"results/parts/e1_{i}.npz")["F"] for i in range(len(ELLS))])
cbar = [float(np.load(f"results/parts/e1_{i}.npz")["cbar"]) for i in range(len(ELLS))]
Am = A[:, :-1].mean(-1)
th = np.array([[exact_spearman(s / l) for s in SIGMAS] for l in ELLS])
thc = np.array([[corr_spearman(s / l, cbar[i]) for s in SIGMAS] for i, l in enumerate(ELLS)])
out["E1"] = dict(ells=ELLS, sigmas=SIGMAS, reps=R1, asset_mean=A.mean(-1).tolist(),
                 asset_sd=A.std(-1).tolist(), firm_mean=F.mean(-1).tolist(), firm_sd=F.std(-1).tolist(),
                 cbar=cbar, theory=th.tolist(), mad=float(np.abs(Am - th).mean()),
                 maxdev=float(np.abs(Am - th).max()), mad_corr=float(np.abs(Am - thc).mean()))

acc = np.stack([np.load(f"results/parts/e2_{i}.npz")["acc"] for i in range(2)])
f1 = np.stack([np.load(f"results/parts/e2_{i}.npz")["f1"] for i in range(2)])
sh = np.concatenate([np.load(f"results/parts/e2_{i}.npz")["shares"] for i in range(2)])
out["E2"] = dict(ells=E2_ELLS, variants=[v[0] for v in VARIANTS], eps=EPS, reps=R2,
                 acc_mean=acc.mean(-1).tolist(), acc_sd=acc.std(-1).tolist(),
                 f1_mean=f1.mean(-1).tolist(), f1_sd=f1.std(-1).tolist(),
                 shares=sh.mean(0).tolist())

parts = [np.load(f"results/parts/e3_{r}.npz") for r in range(20)]
def summ(key):
    br, ap, ece, p80, r80, n80 = [], [], [], [], [], []
    for z in parts:
        p, y = z[key], z["y"]
        br.append(np.mean((p - y) ** 2)); ap.append(average_precision_score(y, p))
        b = np.minimum((p * 10).astype(int), 9)
        ece.append(sum(abs(p[b == k].mean() - y[b == k].mean()) * (b == k).mean() for k in range(10) if (b == k).any()))
        s = p >= 0.8; p80.append(y[s].mean() if s.any() else np.nan); r80.append(y[s].sum() / y.sum()); n80.append(s.mean())
    f = lambda v: [float(np.nanmean(v)), float(np.nanstd(v))]
    return dict(brier=f(br), ap=f(ap), ece=f(ece), prec80=f(p80), rec80=f(r80), flag80=f(n80))
S = {k: summ(k) for k in ["p_extr", "p_loc", "p_full"]}
pb, pp, pr, pf = [], [], [], []
for z in parts:
    y, h = z["y"], z["yhat"]
    pb.append(np.mean((y - h) ** 2)); pp.append(y[h == 1].mean()); pr.append(h[y == 1].mean()); pf.append(h.mean())
S["point"] = dict(brier=[float(np.mean(pb)), float(np.std(pb))], prec=[float(np.mean(pp)), float(np.std(pp))],
                  rec=[float(np.mean(pr)), float(np.std(pr))], flag=[float(np.mean(pf)), float(np.std(pf))])
out["E3"] = dict(ell=ELL3, sigma=SIG3, eps=EPS3, kappa=KAPPA, n_members=NMEM, K=K, reps=20,
                 summary=S, base_rate=float(np.mean([z["y"].mean() for z in parts])))
json.dump(out, open("results/results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out["E1"].items() if k in ("mad", "maxdev", "mad_corr", "cbar")}, indent=0))
fm = np.array(out["E1"]["firm_mean"]); am = np.array(out["E1"]["asset_mean"])
print("asset mean\n", np.round(am, 3)); print("firm mean\n", np.round(fm, 3))
print("E2 acc ell=25\n", np.round(acc.mean(-1)[0], 3)); print("E2 acc ell=500\n", np.round(acc.mean(-1)[1], 3))
print("E2 f1 ell=25\n", np.round(f1.mean(-1)[0], 3)); print("E2 f1 ell=500\n", np.round(f1.mean(-1)[1], 3))
print("shares", np.round(sh.mean(0), 3))
print(json.dumps(out["E3"]["summary"], indent=0)); print("base", out["E3"]["base_rate"])
