# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Zenodo archive, concept DOI [10.5281/zenodo.24102121](https://doi.org/10.5281/zenodo.24102121) (v0.1.0: 10.5281/zenodo.24102122), with DOI badge and
  `doi` in `CITATION.cff`, the README citation and the web reader.
- Links to the Hugging Face dataset in the README and the web reader.
- LinkedIn poster `docs/assets/linkedin_poster.png` (`make poster`), every number read from `results/results.json`.

## [0.1.0] - 2026-11-10

### Added
- Preprint *Words to Coordinates: An Uncertainty-Aware NLP–Geospatial Framework for Measuring the Gap Between
  Disclosed and Physical Climate Risk* (`paper/paper.pdf`) with its LaTeX source in arXiv style, bibliography,
  TikZ architecture figure and generated results table.
- Web reader of the preprint (`docs/paper/index.html`, built by `make web` from `paper/paper.tex` with pandoc),
  served on GitHub Pages at <https://thanatchon36.github.io/words-to-coordinates/paper/>, with a results strip read
  from `results/results.json`.
- Simulation library (`code/w2clib.py`): random Fourier feature hazard fields on the sphere, Gaussian location
  error, capacity-weighted firm exposure, the latent-awareness disclosure model, extraction error, quadrants and
  calibrated posterior sampling.
- Experiments E1–E3 (`code/run_parts.py`, resumable and seeded per unit) on the real locations of 11,107 power plants
  held by 1,247 owners (Global Power Plant Database v1.3.0), with cached per-unit results in `results/parts/`.
- Figure and table scripts, and a README banner from the same asset geography (`make banner`).
- Hugging Face dataset [`thanatchon36/words-to-coordinates`](https://huggingface.co/datasets/thanatchon36/words-to-coordinates)
  built by `make hf`: the asset table (owner names dropped), per-replicate results of E1–E3 and per-firm Monte Carlo
  probabilities of E3.
- Unit tests for the simulation library and the web reader's LaTeX preprocessing (`make test`), run in CI.
- `pyproject.toml` and `make setup` (uv, Python 3.12), MIT licence, `CITATION.cff` and `.zenodo.json`.
