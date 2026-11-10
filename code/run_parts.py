"""Resumable experiment runner. Usage (from the repository root):
   python code/run_parts.py e1 <ell_idx,...>   |  e2 <ell_idx,...>  |  e3 <rep,...>
Each unit uses its own seeded RNG, so results do not depend on chunking."""
import sys, os, json, time
import numpy as np
from scipy.stats import spearmanr
from w2clib import (Field, to_xyz, perturb, load_assets, country_points, firm_exposure,
                    pct_rank, gen_disclosure, extract, quadrant, posterior_table,
                    sample_posterior, SILENT)

from config import *  # noqa: F401,F403

def RNG(*k):
    return np.random.default_rng([SEED, *k])

allp, d = load_assets()
lat, lon = d.latitude.values, d.longitude.values
firm, w = d.firm.values, d.w.values
nF = d.firm.nunique()
xyz = to_xyz(lat, lon)
clat, clon = country_points(d.country.values, allp)
xyz_c = to_xyz(clat, clon)
os.makedirs("results/parts", exist_ok=True)
mode, units = sys.argv[1], [int(v) for v in sys.argv[2].split(",")]
t0 = time.time()

if mode == "e1":
    for i in units:
        ell = ELLS[i]
        A = np.zeros((len(SIGMAS) + 1, R1)); F = np.zeros_like(A)
        for r in range(R1):
            rng = RNG(1, i, r)
            f = Field(ell, N_FEAT, rng)
            z0 = f.at_xyz(xyz); E0 = firm_exposure(z0, firm, w, nF)
            for j, s in enumerate(SIGMAS):
                la, lo = perturb(lat, lon, s, rng); z1 = f.at(la, lo)
                A[j, r] = spearmanr(z0, z1)[0]
                F[j, r] = spearmanr(E0, firm_exposure(z1, firm, w, nF))[0]
            z1 = f.at_xyz(xyz_c)
            A[-1, r] = spearmanr(z0, z1)[0]
            F[-1, r] = spearmanr(E0, firm_exposure(z1, firm, w, nF))[0]
        sq = (xyz ** 2).sum(1); tot = 0.0
        for s0 in range(0, len(xyz), 1500):
            d2 = sq[s0:s0 + 1500, None] + sq[None, :] - 2 * xyz[s0:s0 + 1500] @ xyz.T
            tot += np.exp(-np.maximum(d2, 0) / (2 * ell ** 2)).sum()
        np.savez(f"results/parts/e1_{i}.npz", A=A, F=F, cbar=tot / len(xyz) ** 2)
        print(f"e1 {ell} {time.time() - t0:.0f}s", flush=True)

elif mode == "e2":
    for i in units:
        ell = E2_ELLS[i]
        acc = np.zeros((len(VARIANTS), len(EPS), R2)); f1s = np.zeros_like(acc); shares = []
        for r in range(R2):
            rng = RNG(2, i, r)
            f = Field(ell, N_FEAT, rng)
            z0 = f.at_xyz(xyz)
            FE0 = pct_rank(firm_exposure(z0, firm, w, nF))
            Dstar = gen_disclosure(FE0, BETA, rng)
            Q0 = quadrant(FE0, Dstar)
            shares.append(np.bincount(Q0, minlength=4) / nF)
            for j, (_, s) in enumerate(VARIANTS):
                if s is None: z1 = f.at_xyz(xyz_c)
                elif s == 0: z1 = z0
                else:
                    la, lo = perturb(lat, lon, s, rng); z1 = f.at(la, lo)
                FE1 = pct_rank(firm_exposure(z1, firm, w, nF))
                for k, e in enumerate(EPS):
                    a_, f_ = [], []
                    for _ in range(NX):
                        Q1 = quadrant(FE1, extract(Dstar, e, rng))
                        a_.append((Q1 == Q0).mean())
                        tp = ((Q1 == SILENT) & (Q0 == SILENT)).sum()
                        pr = tp / max((Q1 == SILENT).sum(), 1); rc = tp / max((Q0 == SILENT).sum(), 1)
                        f_.append(0 if tp == 0 else 2 * pr * rc / (pr + rc))
                    acc[j, k, r] = np.mean(a_); f1s[j, k, r] = np.mean(f_)
        np.savez(f"results/parts/e2_{i}.npz", acc=acc, f1=f1s, shares=np.array(shares))
        print(f"e2 {ell} {time.time() - t0:.0f}s", flush=True)

elif mode == "e3":
    sk = np.sqrt(1 - KAPPA ** 2)
    for r in units:
        rng = RNG(3, r)
        ft = Field(ELL3, N_FEAT, rng)
        etas = [Field(ELL3, N_FEAT, rng) for _ in range(NMEM)]
        FEt = pct_rank(firm_exposure(ft.at_xyz(xyz), firm, w, nF))
        Dstar = gen_disclosure(FEt, BETA, rng)
        Qt = quadrant(FEt, Dstar)
        lah, loh = perturb(lat, lon, SIG3, rng); xyz_h = to_xyz(lah, loh)
        Dh = extract(Dstar, EPS3, rng)
        P = posterior_table(EPS3, rng)
        zt_h = ft.at_xyz(xyz_h)
        ens = np.mean([sk * zt_h + KAPPA * e.at_xyz(xyz_h) for e in etas], axis=0)
        FEp = pct_rank(firm_exposure(ens, firm, w, nF))
        Qp = quadrant(FEp, Dh)
        c_extr = np.zeros(nF); c_loc = np.zeros(nF); c_full = np.zeros(nF)
        for k in range(K):
            Dk = sample_posterior(Dh, P, rng)
            c_extr += quadrant(FEp, Dk) == SILENT
            m = rng.integers(NMEM)
            la, lo = perturb(lah, loh, SIG3, rng); xk = to_xyz(la, lo)
            zk = sk * ft.at_xyz(xk) + KAPPA * etas[m].at_xyz(xk)
            FEk = pct_rank(firm_exposure(zk, firm, w, nF))
            c_loc += quadrant(FEk, Dh) == SILENT
            c_full += quadrant(FEk, Dk) == SILENT
        np.savez(f"results/parts/e3_{r}.npz", y=(Qt == SILENT).astype(int), yhat=(Qp == SILENT).astype(int),
                 p_extr=c_extr / K, p_loc=c_loc / K, p_full=c_full / K,
                 FE=FEt, D=Dstar, Q=Qt, P=P)
        print(f"e3 rep {r} {time.time() - t0:.0f}s", flush=True)
