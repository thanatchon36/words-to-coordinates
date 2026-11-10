import json
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import shape
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon as MplPolygon
from matplotlib.lines import Line2D
import figstyle  # noqa: F401
from figstyle import FIGDIR
from w2clib import to_xyz, KM_PER_DEG

LON0, LON1, LAT0, LAT1 = 96.9, 106.1, 5.3, 20.8
ELLS = [25, 100, 500]
SIGMA = 25.0
NFEAT = 2048

g = json.load(open("data/ne_50m_admin0.geojson"))
geoms = {f["properties"]["ADM0_A3"]: shape(f["geometry"]) for f in g["features"]}
tha = geoms["THA"]
view = shapely.box(LON0 - 1, LAT0 - 1, LON1 + 1, LAT1 + 1)

plants = pd.read_csv("data/gppd.csv", low_memory=False,
                     usecols=["country", "latitude", "longitude", "capacity_mw"])
plants = plants[plants.country == "THA"].sort_values("capacity_mw", ascending=False)

# pick three large plants that are far apart for the uncertainty circles
chosen = []
for _, r in plants.iterrows():
    if all(np.hypot((r.latitude - c[0]) * KM_PER_DEG,
                    (r.longitude - c[1]) * KM_PER_DEG * np.cos(np.radians(r.latitude))) > 380
           for c in chosen):
        chosen.append((r.latitude, r.longitude))
    if len(chosen) == 3:
        break

# common random draws -> the same pattern rendered at three spatial scales
rng = np.random.default_rng(7)
Z0 = rng.standard_normal((3, NFEAT)); B0 = rng.uniform(0, 2 * np.pi, NFEAT)
lons = np.arange(LON0, LON1 + 1e-9, 0.025); lats = np.arange(LAT0, LAT1 + 1e-9, 0.025)
LO, LA = np.meshgrid(lons, lats)
inside = shapely.contains_xy(tha, LO.ravel(), LA.ravel())
xyz = to_xyz(LA.ravel(), LO.ravel())


def field(ell):
    W = Z0 / ell
    out = np.empty(xyz.shape[0])
    for s in range(0, xyz.shape[0], 4096):
        ph = (xyz[s:s + 4096] @ W + B0).astype(np.float32)
        out[s:s + 4096] = np.sqrt(2.0 / NFEAT) * np.cos(ph).sum(1)
    out[~inside] = np.nan
    return out.reshape(LA.shape)


def draw_country(ax, geom, fc, ec, lw, z):
    for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        ax.add_patch(MplPolygon(np.asarray(p.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, zorder=z))


fig = plt.figure(figsize=(6.5, 3.85))
aspect = 1.0 / np.cos(np.radians(0.5 * (LAT0 + LAT1)))
pw, left, gap, bottom, height = 0.255, 0.075, 0.035, 0.215, 0.725
axes = [fig.add_axes([left + i * (pw + gap), bottom, pw, height]) for i in range(3)]
for i, (ax, ell) in enumerate(zip(axes, ELLS)):
    ax.set_facecolor("#F7F9FB")
    for code, geom in geoms.items():
        if code != "THA" and geom.intersects(view):
            draw_country(ax, geom, "#E6E6E6", "white", 0.4, 1)
    F = field(ell)
    im = ax.pcolormesh(LO, LA, F, cmap="RdBu_r", vmin=-3, vmax=3, shading="auto",
                       rasterized=True, zorder=2)
    draw_country(ax, tha, "none", "#4D4D4D", 0.5, 3)
    ax.scatter(plants.longitude, plants.latitude, s=3.6, c="black", edgecolors="white",
               linewidths=0.3, zorder=5)
    for la, lo in chosen:
        w = 4 * SIGMA / (KM_PER_DEG * np.cos(np.radians(la)))
        h = 4 * SIGMA / KM_PER_DEG
        ax.add_patch(Ellipse((lo, la), w, h, fill=False, ec="black", lw=0.9, ls=(0, (2.2, 1.4)),
                             zorder=6))
    ax.set_xlim(LON0, LON1); ax.set_ylim(LAT0, LAT1)
    ax.set_aspect(aspect)
    ax.set_title(f"({'abc'[i]})  $\\ell$ = {ell} km", pad=4)
    ax.set_xticks([98, 101, 104])
    ax.set_xticklabels(["98°E", "101°E", "104°E"])
    ax.set_yticks([8, 12, 16, 20])
    ax.set_yticklabels(["8°N", "12°N", "16°N", "20°N"] if i == 0 else [])
    for s in ax.spines.values():
        s.set_visible(True); s.set_linewidth(0.5); s.set_color("#7A7A7A")

cax = fig.add_axes([0.545, 0.105, 0.38, 0.027])
cb = fig.colorbar(im, cax=cax, orientation="horizontal")
cb.set_label("Synthetic hazard index (standardised)", labelpad=2)
cb.ax.tick_params(labelsize=7, width=0.5, length=2.5); cb.outline.set_linewidth(0.5)
handles = [Line2D([], [], marker="o", ls="none", mfc="black", mec="white", mew=0.3, ms=3.6,
                  label="Power plant (GPPD)"),
           Line2D([], [], color="black", lw=0.9, ls=(0, (2.2, 1.4)),
                  label=f"2$\\sigma$ location-error radius ($\\sigma$ = {SIGMA:.0f} km)")]
fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, 0.04), ncol=1,
           handlelength=2.2, borderaxespad=0.0, labelspacing=0.5)
fig.savefig(f"{FIGDIR}/fig_thailand.pdf")
fig.savefig("assets/fig_thailand.png", dpi=170)
print("plants", len(plants), "chosen", chosen)
