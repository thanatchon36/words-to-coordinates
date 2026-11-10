"""Hugging Face dataset -> build/hf/ (uploaded to https://huggingface.co/datasets/thanatchon36/words-to-coordinates).

Writes the asset table the simulation uses (from GPPD v1.3.0, owner names dropped), the per-replicate results of
E1-E3 from results/parts/, the summaries, the configuration and SHA256SUMS. The dataset card is
hf/README.md in this repository. Needs data/ (make data).
Usage (from the repository root): python code/make_hf_dataset.py
"""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from w2clib import QNAMES, country_points, load_assets

OUT = Path("build/hf")


def write(df: pd.DataFrame, rel: str):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, float_format="%.6g")
    print(f"{rel}: {len(df):,} rows")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # ---- assets: the 11,107 plants of owners with >= 3 plants; firm ids are the pseudo-firms of the paper
    allp, d = load_assets()
    clat, clon = country_points(d.country.values, allp)
    assets = pd.DataFrame({
        "asset": np.arange(len(d)), "firm": d.firm.values, "country": d.country.values,
        "latitude": d.latitude.values, "longitude": d.longitude.values, "capacity_mw": d.capacity_mw.values,
        "primary_fuel": d.primary_fuel.values, "weight": d.w.values,
    })
    write(assets, "assets/assets.csv")
    cp = (pd.DataFrame({"country": d.country.values, "latitude": clat, "longitude": clon})
          .drop_duplicates("country").sort_values("country"))
    write(cp, "assets/country_points.csv")

    # ---- E1: exposure fidelity under location error, per replicate
    locs = [str(s) for s in C.SIGMAS] + ["country"]
    rows = []
    for i, ell in enumerate(C.ELLS):
        z = np.load(f"results/parts/e1_{i}.npz")
        for j, loc in enumerate(locs):
            for r in range(z["A"].shape[1]):
                rows.append((ell, loc, r, z["A"][j, r], z["F"][j, r]))
    write(pd.DataFrame(rows, columns=["ell_km", "sigma_km", "rep", "asset_spearman", "firm_spearman"]),
          "results/e1_fidelity.csv")

    # ---- E2: quadrant accuracy and silent-risk F1 by location variant and extraction error, per replicate
    rows, shares = [], []
    for i, ell in enumerate(C.E2_ELLS):
        z = np.load(f"results/parts/e2_{i}.npz")
        for j, (name, _) in enumerate(C.VARIANTS):
            for k, eps in enumerate(C.EPS):
                for r in range(z["acc"].shape[2]):
                    rows.append((ell, name, eps, r, z["acc"][j, k, r], z["f1"][j, k, r]))
        for r, sh in enumerate(z["shares"]):
            shares.append((ell, r, *sh))
    write(pd.DataFrame(rows, columns=["ell_km", "location", "extraction_error", "rep", "quadrant_accuracy",
                                      "silent_f1"]), "results/e2_quadrant_accuracy.csv")
    write(pd.DataFrame(shares, columns=["ell_km", "rep"] + [QNAMES[q].lower().replace(" ", "_") for q in range(4)]),
          "results/e2_quadrant_shares.csv")

    # ---- E3: per-firm truth, point classification and Monte Carlo probabilities, per replicate
    firms, post = [], []
    for r in range(20):
        z = np.load(f"results/parts/e3_{r}.npz")
        firms.append(pd.DataFrame({
            "rep": r, "firm": np.arange(len(z["y"])), "true_exposure_rank": z["FE"], "true_level": z["D"],
            "true_quadrant": [QNAMES[q] for q in z["Q"]], "silent": z["y"], "point_silent": z["yhat"],
            "p_silent_extraction": z["p_extr"], "p_silent_location_hazard": z["p_loc"], "p_silent_full": z["p_full"],
        }))
        for k in range(5):
            for j in range(5):
                post.append((r, k, j, z["P"][k, j]))
    write(pd.concat(firms, ignore_index=True), "results/e3_firm_predictions.csv")
    write(pd.DataFrame(post, columns=["rep", "extracted_level", "true_level", "probability"]),
          "results/e3_posterior_tables.csv")

    res = json.load(open("results/results.json"))
    names = {"point": "Point estimate", "p_extr": "MC: extraction only", "p_loc": "MC: location + hazard model",
             "p_full": "MC: full propagation"}
    rows = [(names[m], metric, v[0], v[1]) for m, d_ in res["E3"]["summary"].items() for metric, v in d_.items()]
    write(pd.DataFrame(rows, columns=["method", "metric", "mean", "sd"]), "results/e3_summary.csv")

    for f in ("results/results.json", "results/results_extra.json"):
        shutil.copyfile(f, OUT / f)
    cfg = {k: getattr(C, k) for k in dir(C) if k.isupper()}
    (OUT / "config.json").write_text(json.dumps(cfg, indent=1))
    shutil.copyfile("hf/README.md", OUT / "README.md")
    shutil.copyfile("hf/LICENSE", OUT / "LICENSE")

    sums = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}")
    (OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n")


if __name__ == "__main__":
    main()
