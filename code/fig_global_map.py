import json
import numpy as np
import pandas as pd
import h3
import shapely
from shapely.geometry import shape, Polygon, box
from shapely.affinity import translate
from pyproj import Transformer
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm
import figstyle  # noqa: F401
from figstyle import FIGDIR

T = Transformer.from_crs("EPSG:4326", "EPSG:8857", always_xy=True)
RES = 2


def proj_poly(poly):
    poly = shapely.segmentize(poly, 1.0)
    x, y = T.transform(*np.asarray(poly.exterior.coords).T)
    return np.column_stack([x, y]) / 1e6


def split_antimeridian(coords_latlng):
    lats = np.array([c[0] for c in coords_latlng]); lngs = np.array([c[1] for c in coords_latlng])
    if lngs.max() - lngs.min() <= 180:
        return [Polygon(np.column_stack([lngs, lats]))]
    lng2 = np.where(lngs < 0, lngs + 360, lngs)
    p = Polygon(np.column_stack([lng2, lats]))
    parts = []
    a = p.intersection(box(0, -90, 180, 90))
    b = translate(p.intersection(box(180, -90, 360, 90)), xoff=-360)
    for g in (a, b):
        if g.is_empty:
            continue
        parts += list(g.geoms) if hasattr(g, "geoms") else [g]
    return [q for q in parts if isinstance(q, Polygon) and q.area > 0]


df = pd.read_csv("data/gppd.csv", low_memory=False, usecols=["latitude", "longitude", "capacity_mw"])
df["cell"] = [h3.latlng_to_cell(a, b, RES) for a, b in zip(df.latitude, df.longitude)]
agg = df.groupby("cell")["capacity_mw"].sum() / 1000.0  # GW

polys, vals = [], []
for cell, v in agg.items():
    for p in split_antimeridian(h3.cell_to_boundary(cell)):
        polys.append(proj_poly(p)); vals.append(v)
vals = np.array(vals)

land = json.load(open("data/ne_110m_land.geojson"))
land_polys = []
for f in land["features"]:
    g = shape(f["geometry"])
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        land_polys.append(proj_poly(p))

# globe outline and graticule
edge = np.linspace(-90, 90, 181)
lon_line = np.linspace(-180, 180, 361)
ox = np.concatenate([np.full_like(edge, -180), lon_line, np.full_like(edge, 180)[::-1], lon_line[::-1]])
oy = np.concatenate([edge, np.full_like(lon_line, 90), edge[::-1], np.full_like(lon_line, -90)])
gx, gy = T.transform(ox, oy)

fig = plt.figure(figsize=(6.5, 3.55))
ax = fig.add_axes([0.01, 0.17, 0.98, 0.81])
ax.fill(np.array(gx) / 1e6, np.array(gy) / 1e6, color="#F7F9FB", zorder=0, lw=0)
for la in range(-60, 91, 30):
    x, y = T.transform(lon_line, np.full_like(lon_line, la))
    ax.plot(np.array(x) / 1e6, np.array(y) / 1e6, color="#D9DEE3", lw=0.35, zorder=1)
for lo in range(-180, 181, 30):
    x, y = T.transform(np.full_like(edge, lo), edge)
    ax.plot(np.array(x) / 1e6, np.array(y) / 1e6, color="#D9DEE3", lw=0.35, zorder=1)
ax.add_collection(PolyCollection(land_polys, facecolor="#E4E4E4", edgecolor="white", lw=0.25, zorder=2))
norm = LogNorm(vmin=0.01, vmax=vals.max())
pc = PolyCollection(polys, array=np.clip(vals, 0.01, None), cmap="viridis", norm=norm,
                    edgecolor="white", lw=0.12, zorder=3)
ax.add_collection(pc)
ax.plot(np.array(gx) / 1e6, np.array(gy) / 1e6, color="#7A7A7A", lw=0.6, zorder=4)
ax.set_xlim(np.min(gx) / 1e6 * 1.01, np.max(gx) / 1e6 * 1.01)
ax.set_ylim(np.min(gy) / 1e6 * 1.02, np.max(gy) / 1e6 * 1.02)
ax.set_aspect("equal"); ax.axis("off")

cax = fig.add_axes([0.30, 0.10, 0.40, 0.028])
cb = fig.colorbar(pc, cax=cax, orientation="horizontal")
cb.set_label("Installed capacity per H3 cell (GW, log scale)", labelpad=3)
cb.ax.tick_params(labelsize=7, width=0.5, length=2.5)
cb.outline.set_linewidth(0.5)
fig.savefig(f"{FIGDIR}/fig_global_map.pdf")
fig.savefig("assets/fig_global_map.png", dpi=170)
print("cells", len(agg), "max GW", vals.max().round(1), "plants", len(df))
