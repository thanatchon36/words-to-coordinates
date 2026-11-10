"""README banner -> docs/assets/banner.png (1680 x 624 px).

Left: the real asset geography of the simulation study (Global Power Plant Database v1.3.0, installed capacity
per H3 cell) on a dark globe. Right: project name and tagline. Needs data/ (make data).
Usage (from the repository root): python code/make_banner.py
"""
import json
import os

import h3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm
import shapely
from pyproj import Transformer
from shapely.affinity import translate
from shapely.geometry import Polygon, box, shape

# Same projection (Equal Earth) and H3 handling as code/fig_global_map.py, which runs on import.
T = Transformer.from_crs("EPSG:4326", "EPSG:8857", always_xy=True)


def proj_poly(poly):
    poly = shapely.segmentize(poly, 1.0)
    x, y = T.transform(*np.asarray(poly.exterior.coords).T)
    return np.column_stack([x, y]) / 1e6


def split_antimeridian(coords_latlng):
    lats = np.array([c[0] for c in coords_latlng])
    lngs = np.array([c[1] for c in coords_latlng])
    if lngs.max() - lngs.min() <= 180:
        return [Polygon(np.column_stack([lngs, lats]))]
    p = Polygon(np.column_stack([np.where(lngs < 0, lngs + 360, lngs), lats]))
    parts = []
    for g in (p.intersection(box(0, -90, 180, 90)), translate(p.intersection(box(180, -90, 360, 90)), xoff=-360)):
        if not g.is_empty:
            parts += list(g.geoms) if hasattr(g, "geoms") else [g]
    return [q for q in parts if isinstance(q, Polygon) and q.area > 0]


BG, ACCENT, INK, MUTED = "#05080f", "#3ddc97", "#e8ecf2", "#8f9bb3"
RES = 2
OUT = "docs/assets/banner.png"

df = pd.read_csv("data/gppd.csv", low_memory=False, usecols=["latitude", "longitude", "capacity_mw"])
df["cell"] = [h3.latlng_to_cell(a, b, RES) for a, b in zip(df.latitude, df.longitude)]
agg = df.groupby("cell")["capacity_mw"].sum() / 1000.0  # GW
polys, vals = [], []
for cell, v in agg.items():
    for p in split_antimeridian(h3.cell_to_boundary(cell)):
        polys.append(proj_poly(p))
        vals.append(v)
vals = np.array(vals)

land_polys = []
for f in json.load(open("data/ne_110m_land.geojson"))["features"]:
    g = shape(f["geometry"])
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        land_polys.append(proj_poly(p))

edge = np.linspace(-90, 90, 181)
lon_line = np.linspace(-180, 180, 361)
ox = np.concatenate([np.full_like(edge, -180), lon_line, np.full_like(edge, 180)[::-1], lon_line[::-1]])
oy = np.concatenate([edge, np.full_like(lon_line, 90), edge[::-1], np.full_like(lon_line, -90)])
gx, gy = (np.asarray(c) / 1e6 for c in T.transform(ox, oy))

W, H, DPI = 1680, 624, 200
fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
ax = fig.add_axes([0.015, 0.06, 0.50, 0.88])
ax.set_facecolor(BG)
ax.fill(gx, gy, color="#0b1220", lw=0, zorder=0)
for la in range(-60, 91, 30):
    x, y = T.transform(lon_line, np.full_like(lon_line, la))
    ax.plot(np.array(x) / 1e6, np.array(y) / 1e6, color="#16213a", lw=0.3, zorder=1)
for lo in range(-180, 181, 30):
    x, y = T.transform(np.full_like(edge, lo), edge)
    ax.plot(np.array(x) / 1e6, np.array(y) / 1e6, color="#16213a", lw=0.3, zorder=1)
ax.add_collection(PolyCollection(land_polys, facecolor="#1a2236", edgecolor="none", zorder=2))
ax.add_collection(PolyCollection(polys, array=np.clip(vals, 0.01, None), cmap="viridis",
                                 norm=LogNorm(vmin=0.01, vmax=vals.max()), edgecolor=BG, lw=0.15, zorder=3))
ax.plot(gx, gy, color="#2a3550", lw=0.6, zorder=4)
ax.set_xlim(gx.min() * 1.01, gx.max() * 1.01)
ax.set_ylim(gy.min() * 1.02, gy.max() * 1.02)
ax.set_aspect("equal")
ax.axis("off")

font = {"family": "DejaVu Sans"}
x0 = 0.545
fig.text(x0, 0.64, "words-to-coordinates", color=ACCENT, fontsize=17.5, fontweight="bold", **font)
fig.text(x0, 0.40, "Measuring the gap between disclosed\nand physical climate risk",
         color=INK, fontsize=9.6, linespacing=1.5, **font)
fig.text(x0, 0.19, "IFRS S2 extraction · geocoding with precision classes\nhazard ensembles · Disclosure Gap Index",
         color=MUTED, fontsize=7.2, linespacing=1.6, **font)
fig.text(0.985, 0.035, f"{len(df):,} power plants, installed capacity per H3 cell · Global Power Plant Database v1.3.0 "
         "(WRI, CC BY 4.0) · Natural Earth", color=MUTED, fontsize=5.2, ha="right", **font)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=DPI, facecolor=BG)
print(OUT)
