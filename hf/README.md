---
license: cc-by-4.0
pretty_name: "words-to-coordinates: simulation data for measuring the gap between disclosed and physical climate risk"
language:
  - en
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - climate-risk
  - climate-disclosure
  - physical-risk
  - geospatial
  - geocoding
  - uncertainty-quantification
  - sustainable-finance
  - power-plants
  - synthetic
configs:
  - config_name: e3_firm_predictions
    data_files: results/e3_firm_predictions.csv
    default: true
  - config_name: assets
    data_files: assets/assets.csv
  - config_name: e1_fidelity
    data_files: results/e1_fidelity.csv
  - config_name: e2_quadrant_accuracy
    data_files: results/e2_quadrant_accuracy.csv
  - config_name: e3_summary
    data_files: results/e3_summary.csv
---

# words-to-coordinates: simulation data for measuring the gap between disclosed and physical climate risk

> **Only the asset locations are real.** `assets/assets.csv` comes from the Global Power Plant Database v1.3.0.
> Hazard fields, disclosure levels, extraction errors and therefore every result in `results/` are synthetic. Owner
> names were used only to group plants into pseudo-firms and have been removed; no row refers to a real company's
> disclosure or risk.

Data for the preprint *Words to Coordinates: An Uncertainty-Aware NLP–Geospatial Framework for Measuring the Gap
Between Disclosed and Physical Climate Risk* by Thanatchon Chongmankhong
([read online](https://thanatchon36.github.io/words-to-coordinates/paper/) ·
[PDF](https://github.com/thanatchon36/words-to-coordinates/blob/main/paper/paper.pdf)).
The paper proposes the Disclosure Gap Index (DGI), which compares a firm's modelled physical exposure with its
disclosure intensity and places it in one of four quadrants (aware, silent risk, cheap talk, benign), derives a
closed-form relation between geolocation error σ and exposure fidelity for a hazard with correlation length ℓ
(Corr = ℓ² / (ℓ² + σ²)), and propagates extraction, geolocation and hazard-model uncertainty by Monte Carlo.
Code: <https://github.com/thanatchon36/words-to-coordinates>; archived on Zenodo:
[10.5281/zenodo.24102121](https://doi.org/10.5281/zenodo.24102121).

*Independent personal research. Does not represent the views of any employer or institution.*

## Files

| path | content |
|---|---|
| `assets/assets.csv` | **real locations.** The 11,107 power plants of the 1,247 owners with at least three plants in 76 countries: `asset`, pseudo-firm id `firm`, ISO3 `country`, `latitude`, `longitude`, `capacity_mw`, `primary_fuel`, and `weight`, the plant's share of its firm's capacity (used to aggregate exposure) |
| `assets/country_points.csv` | the point each country is geocoded to in the country-level variant (Natural Earth label point; asset mean where missing) |
| `results/e1_fidelity.csv` | **E1, synthetic hazards.** Spearman correlation between hazard values at true and degraded locations, for assets and for capacity-weighted firm exposure: 7 correlation lengths ℓ (10–1,000 km) × 7 location-error scales σ (1–250 km) plus country-level geocoding × 30 replicates (1,680 rows) |
| `results/e2_quadrant_accuracy.csv` | **E2.** Four-class quadrant accuracy and silent-risk F1 against the true quadrants, for ℓ = 25 and 500 km, five location variants (exact, 5 km, 25 km, 100 km, country) and extraction error rates 0–0.5, 30 replicates (1,800 rows) |
| `results/e2_quadrant_shares.csv` | share of firms in each true quadrant per E2 replicate |
| `results/e3_firm_predictions.csv` | **E3.** One row per firm and replicate (20 × 1,247 = 24,940): true exposure rank, true disclosure level (0–4), true quadrant, whether the firm is truly silent risk, the point classification, and P(silent) from Monte Carlo propagation of extraction error only, location + hazard-model error only, and all three (ℓ = 50 km, σ = 25 km, extraction error 0.25, five hazard-model members, 80 draws) |
| `results/e3_posterior_tables.csv` | the calibrated P(true level \| extracted level) used in each E3 replicate |
| `results/e3_summary.csv` | Brier score, expected calibration error, average precision and precision/recall/share flagged at P(silent) ≥ 0.8, mean and s.d. over replicates (Table 3 of the paper) |
| `results/results.json`, `results/results_extra.json` | the summaries the paper's figures, table and text are built from |
| `config.json` | experiment parameters and the master seed (20261109) |
| `SHA256SUMS` | checksums of every file above |

`firm` in `assets/assets.csv` and in `results/e3_firm_predictions.csv` is the same id, so per-firm probabilities can
be joined to asset locations and mapped.

## How the synthetic parts are generated

Hazard fields are unit-variance stationary Gaussian random fields on the sphere with a squared-exponential kernel in
chordal distance, sampled with 1,024 random Fourier features. Firm exposure is the capacity-weighted mean of Φ(z)
over the firm's plants, ranked within the sample. Disclosure levels follow a latent-awareness model: a latent score
0.4 · Φ⁻¹(exposure rank) + noise, cut into five levels with shares 15/30/25/20/10%. Extraction error moves a level to
an adjacent one with the stated probability. Location error is isotropic Gaussian with per-axis s.d. σ. In E3, the
hazard-model ensemble members share the true field with weight √(1 − 0.4²) and add independent fields with weight 0.4.
Every experimental unit draws from its own stream derived from the master seed, so `make experiments` in the code
repository reproduces these files exactly.

## Licence

CC BY 4.0; see `LICENSE`. `assets/assets.csv` is derived from the Global Power Plant Database (World Resources
Institute, CC BY 4.0), which must also be credited; Natural Earth is public domain.

## Citation

```bibtex
@misc{chongmankhong2026words,
  author = {Chongmankhong, Thanatchon},
  title  = {Words to Coordinates: An Uncertainty-Aware {NLP}--Geospatial Framework for Measuring
            the Gap Between Disclosed and Physical Climate Risk},
  year   = {2026},
  doi    = {10.5281/zenodo.24102121},
  url    = {https://thanatchon36.github.io/words-to-coordinates/paper/},
  note   = {Preprint; simulation results use real asset locations with synthetic hazards and disclosures}
}
```

Global Power Plant Database: Byers, L., Friedrich, J., Hennig, R., Kressig, A., Li, X., McCormick, C. and
Malaguzzi Valeri, L. (2018). *A Global Database of Power Plants*. World Resources Institute.
