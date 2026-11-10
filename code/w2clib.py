"""Core library for the Words-to-Coordinates (W2C) simulation study.

Real asset geography: WRI Global Power Plant Database (GPPD, v1.3.0).
Hazard fields: synthetic stationary Gaussian random fields on the sphere,
sampled with random Fourier features (squared-exponential kernel in chordal
distance). Disclosures and extraction errors are simulated.
"""
import json
import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

R_EARTH = 6371.0088                     # km
KM_PER_DEG = np.pi * R_EARTH / 180.0    # km per degree of latitude

# Disclosure levels 0..4 and their marginal shares in the simulated population
LEVEL_SHARES = np.array([0.15, 0.30, 0.25, 0.20, 0.10])
CUTS = norm.ppf(np.cumsum(LEVEL_SHARES)[:-1])

# Quadrant codes
BENIGN, CHEAP, SILENT, AWARE = 0, 1, 2, 3
QNAMES = {BENIGN: "Benign", CHEAP: "Cheap talk", SILENT: "Silent risk", AWARE: "Aware"}


def to_xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return R_EARTH * np.stack([np.cos(la) * np.cos(lo),
                               np.cos(la) * np.sin(lo),
                               np.sin(la)], axis=-1)


class Field:
    """Unit-variance Gaussian random field, SE kernel with length scale ell (km)."""

    def __init__(self, ell_km, n_feat, rng):
        self.W = rng.standard_normal((3, n_feat)) / ell_km
        self.b = rng.uniform(0.0, 2.0 * np.pi, n_feat)
        self.scale = np.sqrt(2.0 / n_feat)

    def at_xyz(self, xyz, chunk=4096):
        out = np.empty(xyz.shape[0])
        for s in range(0, xyz.shape[0], chunk):
            ph = (xyz[s:s + chunk] @ self.W + self.b).astype(np.float32)
            out[s:s + chunk] = self.scale * np.cos(ph).sum(axis=1, dtype=np.float64)
        return out

    def at(self, lat, lon):
        return self.at_xyz(to_xyz(np.asarray(lat), np.asarray(lon)))


def perturb(lat, lon, sigma_km, rng):
    """Isotropic Gaussian displacement with per-axis s.d. sigma_km (tangent plane)."""
    if sigma_km <= 0:
        return lat.copy(), lon.copy()
    dy = rng.standard_normal(lat.shape) * sigma_km
    dx = rng.standard_normal(lat.shape) * sigma_km
    lat2 = np.clip(lat + dy / KM_PER_DEG, -89.9, 89.9)
    lon2 = lon + dx / (KM_PER_DEG * np.cos(np.radians(lat)))
    lon2 = (lon2 + 180.0) % 360.0 - 180.0
    return lat2, lon2


def load_assets(min_plants=3, path="data/gppd.csv"):
    cols = ["country", "name", "capacity_mw", "latitude", "longitude", "owner", "primary_fuel"]
    allp = pd.read_csv(path, low_memory=False, usecols=cols)
    d = allp.dropna(subset=["owner"]).copy()
    d = d[d.groupby("owner")["owner"].transform("size") >= min_plants].reset_index(drop=True)
    d["firm"] = pd.factorize(d["owner"])[0]
    d["w"] = d["capacity_mw"] / d.groupby("firm")["capacity_mw"].transform("sum")
    return allp, d


def country_points(codes, allp, ne_path="data/ne_50m_admin0.geojson"):
    """Country-level geocode: Natural Earth label point; fallback to asset mean."""
    g = json.load(open(ne_path))
    pts = {}
    for f in g["features"]:
        p = f["properties"]
        for key in ("ADM0_A3", "ISO_A3_EH"):
            c = p.get(key)
            if c and c != "-99" and c not in pts:
                pts[c] = (p["LABEL_Y"], p["LABEL_X"])
    means = allp.groupby("country")[["latitude", "longitude"]].mean()
    lat = np.empty(len(codes)); lon = np.empty(len(codes))
    for i, c in enumerate(codes):
        if c in pts:
            lat[i], lon[i] = pts[c]
        else:
            lat[i], lon[i] = means.loc[c, "latitude"], means.loc[c, "longitude"]
    return lat, lon


def firm_exposure(z, firm, w, n_firms):
    """Capacity-weighted mean of g(z) = Phi(z) across a firm's assets."""
    return np.bincount(firm, weights=w * norm.cdf(z), minlength=n_firms)


def pct_rank(x):
    return (rankdata(x) - 0.5) / len(x)


def gen_disclosure(FE, beta, rng):
    """Latent-awareness model: disclosure level depends on true exposure rank."""
    zE = norm.ppf(np.clip(FE, 1e-6, 1 - 1e-6))
    L = beta * zE + np.sqrt(1.0 - beta ** 2) * rng.standard_normal(FE.shape)
    return np.searchsorted(CUTS, L)


def extract(D, eps, rng):
    """Extraction error: with prob. eps the level moves to an adjacent level."""
    flip = rng.random(D.shape) < eps
    step = np.where(rng.random(D.shape) < 0.5, -1, 1)
    Dh = D + flip * step
    Dh = np.where(Dh < 0, 1, Dh)
    Dh = np.where(Dh > 4, 3, Dh)
    return Dh


def quadrant(FE, D, tauE=0.5, tauD=2):
    hiE, hiD = FE > tauE, D >= tauD
    return np.select([hiE & hiD, hiE & ~hiD, ~hiE & hiD], [AWARE, SILENT, CHEAP], default=BENIGN)


def posterior_table(eps, rng, n_cal=500, alpha=1.0):
    """P(D* = j | D_hat = k) estimated on an annotated calibration sample."""
    Dc = rng.choice(5, size=n_cal, p=LEVEL_SHARES)
    Dh = extract(Dc, eps, rng)
    C = np.full((5, 5), alpha)            # rows: D_hat, cols: D*
    np.add.at(C, (Dh, Dc), 1.0)
    return C / C.sum(axis=1, keepdims=True)


def sample_posterior(Dh, P, rng):
    cdf = np.cumsum(P[Dh], axis=1)
    u = rng.random(len(Dh))[:, None]
    return (u > cdf).sum(axis=1)


def theory_spearman(sigma, ell):
    rho = ell ** 2 / (ell ** 2 + sigma ** 2)
    return 6.0 / np.pi * np.arcsin(rho / 2.0)
