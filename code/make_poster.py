"""LinkedIn poster -> docs/assets/linkedin_poster.png (1440 x 1800 px, 4:5).

Every number on the poster is read from results/results.json; the map shows the real asset locations used in the
simulation (GPPD v1.3.0). Needs data/ (make data). Fira Sans is used when FONT_DIR points to its .ttf files,
otherwise DejaVu Sans.
Usage (from the repository root): FONT_DIR=/path/to/fira python code/make_poster.py
"""
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from pyproj import Transformer
from scipy.integrate import quad
from shapely.geometry import shape

from w2clib import load_assets

W, H = 1440, 1800
BG, PANEL, RULE = "#05080f", "#0a1120", "#1b2740"
ACCENT, ACCENT_2, INK, MUTED = "#3ddc97", "#b4f5d6", "#e8ecf2", "#8f9bb3"
OUT = "docs/assets/linkedin_poster.png"

font_dir = os.environ.get("FONT_DIR")
FAMILY = "DejaVu Sans"
if font_dir and Path(font_dir).is_dir():
    for f in Path(font_dir).glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))
    FAMILY = "Fira Sans"
plt.rcParams.update({"font.family": FAMILY, "text.color": INK})

res = json.load(open("results/results.json"))
E1, E2, S = res["E1"], res["E2"], res["E3"]["summary"]
ells, sigmas = np.array(E1["ells"]), np.array(E1["sigmas"])
country_local = max(row[-1] for ell, row in zip(E1["ells"], E1["firm_mean"]) if ell <= 100)
acc_eps20 = E2["acc_mean"][E2["ells"].index(25)][E2["variants"].index("exact")][E2["eps"].index(0.2)]
acc25 = E2["acc_mean"][E2["ells"].index(25)][E2["variants"].index("25 km")][0]

fig = plt.figure(figsize=(W / 72, H / 72), dpi=72, facecolor=BG)


def Y(px):  # pixel row from the top -> figure coordinate
    return 1 - px / H


def X(px):
    return px / W


def text(x, y, s, size, color=INK, weight="regular", **kw):
    return fig.text(X(x), Y(y), s, fontsize=size, color=color, fontweight=weight, va="top", **kw)


# soft glow behind the map
bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
yy, xx = np.mgrid[0:H, 0:W]
glow = np.exp(-(((xx - 720) / 640) ** 2 + ((yy - 1040) / 300) ** 2))
bg.imshow(glow, cmap=plt.matplotlib.colors.LinearSegmentedColormap.from_list("g", [BG, "#0b1a33"]),
          extent=[0, W, H, 0], aspect="auto")
bg.axis("off")

# ---------------------------------------------------------------- header and hook
text(94, 62, "WORDS TO COORDINATES", 27, ACCENT, "bold")
text(470, 64, "open-source measurement of climate-risk disclosure", 25, MUTED)
text(80, 112, f"{country_local:.2f}", 210, ACCENT, "bold")
text(100, 350, "Locate a firm's power plants only\nto the country, and its ranking on\n"
     "local climate hazards correlates\nat most this well with the truth.", 29, INK, linespacing=1.55)
text(100, 568, "W2C turns climate disclosures into\ncoordinates, and every label\ninto a probability.",
     30, ACCENT, "medium", linespacing=1.5)

# ---------------------------------------------------------------- theory panel (right)
ax = fig.add_axes([X(800), Y(700), X(560), (700 - 190) / H])
ax.set_facecolor("none")
r = np.logspace(-3, np.log10(25), 300)


def exact_spearman(ratio):
    a = ratio ** 2
    v, _ = quad(lambda t: np.arcsin(0.5 * np.exp(-a * t)) * np.exp(-t), 0, np.inf, limit=200)
    return 6 / np.pi * v


curve = np.array([exact_spearman(x) for x in r])
for lw, al in ((14, 0.06), (8, 0.12), (3.2, 1.0)):
    ax.plot(r, curve, color=ACCENT, lw=lw, alpha=al, solid_capstyle="round", zorder=2)
am = np.array(E1["asset_mean"])[:, :-1]
ratios = sigmas[None, :] / ells[:, None]
ax.scatter(ratios.ravel(), am.ravel(), s=70, color=INK, edgecolor=BG, lw=1.5, zorder=3)
ax.axvline(1 / 3, color=ACCENT_2, lw=1.2, ls=(0, (4, 4)), alpha=0.8, zorder=1)
ax.text(1 / 3 * 1.25, 0.97, "σ = ℓ/3", color=ACCENT_2, fontsize=21, va="top", fontweight="medium")
ax.set_xscale("log")
ax.set_xlim(1e-3, 25)
ax.set_ylim(-0.03, 1.05)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(RULE)
ax.tick_params(colors=MUTED, labelsize=16, length=0, pad=8)
ax.set_xticks([0.01, 0.1, 1, 10])
ax.set_xticklabels(["0.01", "0.1", "1", "10"])
ax.set_yticks([0, 0.5, 1])
ax.set_xlabel("location error ÷ hazard scale   (σ / ℓ)", color=MUTED, fontsize=17, labelpad=10)
ax.set_ylabel("exposure rank correlation", color=MUTED, fontsize=17, labelpad=8)
text(800, 112, f"{ratios.size} simulations, one curve", 25, INK, "semibold")
text(800, 150, "Corr = ℓ² / (ℓ² + σ²)", 23, ACCENT, "medium")
text(1050, 154, f"theory vs. simulation: mean gap {E1['mad']:.3f}", 17, MUTED)

# ---------------------------------------------------------------- world map of the real assets
T = Transformer.from_crs("EPSG:4326", "EPSG:8857", always_xy=True)
_, d = load_assets()
x, y = T.transform(d.longitude.values, d.latitude.values)
x, y = np.asarray(x) / 1e6, np.asarray(y) / 1e6
cap = d.capacity_mw.values
mp = fig.add_axes([X(40), Y(1318), X(1360), (1318 - 862) / H])
mp.set_facecolor("none")
for f in json.load(open("data/ne_110m_land.geojson"))["features"]:
    g = shape(f["geometry"])
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        px, py = T.transform(*np.asarray(p.exterior.coords).T)
        mp.fill(np.asarray(px) / 1e6, np.asarray(py) / 1e6, color="#111a2c", lw=0, zorder=0)
size = 1.5 + 9 * np.sqrt(cap / cap.max())
mp.scatter(x, y, s=size * 22, color=ACCENT, alpha=0.035, lw=0, zorder=1)
mp.scatter(x, y, s=size * 5, color=ACCENT, alpha=0.12, lw=0, zorder=2)
mp.scatter(x, y, s=size * 0.7, color=ACCENT_2, alpha=0.9, lw=0, zorder=3)
mp.set_xlim(-17.2, 17.2)
mp.set_ylim(-5.6, 8.35)
mp.set_aspect("equal")
mp.axis("off")

# Thailand callout: circle on the map, text in the empty Pacific to its right (placed in pixels)
tx, ty = (v / 1e6 for v in T.transform(100.9, 14.0))
mp.scatter([tx], [ty], s=900, facecolor="none", edgecolor=INK, lw=1.4, zorder=4)
fig.canvas.draw()
cx, cy = fig.transFigure.inverted().transform(mp.transData.transform((tx, ty)))
cx, cy = cx * W, (1 - cy) * H  # Thailand in pixels from the top-left
lx, ly = 1180, 960
fig.add_artist(plt.Line2D([X(cx + 16), X(lx - 12)], [Y(cy - 10), Y(ly + 22)], color=MUTED, lw=1.1))
text(lx, ly, "City-level locations,\n25 km hazard", 21, INK, "semibold", linespacing=1.35)
text(lx, ly + 70, f"right quadrant for {acc25:.0%}\nof firms, not 100%", 19, MUTED, linespacing=1.4)
text(94, 800, f"{len(d):,} real power plants  ·  {d.firm.nunique():,} owners  ·  {d.country.nunique()} countries",
     23, INK, "medium")
text(94, 836, "Global Power Plant Database v1.3.0", 18, MUTED)

# ---------------------------------------------------------------- stats row
fig.add_artist(plt.Line2D([X(94), X(1346)], [Y(1326), Y(1326)], color=RULE, lw=1.5))
stats = [
    (f"{acc_eps20:.3f}", "quadrant accuracy with\n20% of extractions wrong"),
    (f"{S['p_full']['ece'][0]:.3f}", f"calibration error, down\nfrom {S['p_extr']['ece'][0]:.3f}"),
    (f"{S['p_full']['prec80'][0]:.2f}", f"precision of silent-risk\nflags (vs {S['point']['prec'][0]:.2f})"),
    ("σ ≤ ℓ/3", "a geocoding spec\nfor any hazard"),
]
for i, (big, small) in enumerate(stats):
    x0 = 94 + i * 324
    text(x0, 1362, big, 60, ACCENT, "semibold")
    text(x0, 1450, small, 20, MUTED, linespacing=1.5)

# ---------------------------------------------------------------- links box
box = FancyBboxPatch((X(86), Y(1735)), X(1268), (1735 - 1548) / H, boxstyle="round,pad=0,rounding_size=0.012",
                     transform=fig.transFigure, facecolor=PANEL, edgecolor=RULE, lw=1.5, zorder=0)
fig.add_artist(box)
text(130, 1584, "Code + paper", 19, MUTED)
text(130, 1614, "github.com/thanatchon36/words-to-coordinates", 25, INK)
text(780, 1584, "Dataset", 19, MUTED)
text(780, 1614, "hf.co/datasets/thanatchon36/words-to-coordinates", 23.5, INK)
text(130, 1676, "Asset locations are real; hazards and disclosures are simulated, so the numbers measure the method, "
     "not any company.", 17, MUTED)

# ---------------------------------------------------------------- footer
text(94, 1760, "Thanatchon Chongmankhong  ·  views are my own  ·  DOI 10.5281/zenodo.24102121", 18.5, MUTED)
fig.text(X(1346), Y(1762), "Power plants: WRI GPPD v1.3.0 (CC BY 4.0) · Natural Earth", fontsize=14, color="#5d6880",
         ha="right", va="top")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=72, facecolor=BG)
print(OUT)
