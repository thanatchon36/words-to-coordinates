"""Experiment configuration shared by run_parts.py and combine.py."""
SEED, N_FEAT, BETA = 20261109, 1024, 0.4
ELLS = [10, 25, 50, 100, 250, 500, 1000]
SIGMAS = [1, 5, 10, 25, 50, 100, 250]
R1 = 30
E2_ELLS = [25, 500]
VARIANTS = [("exact", 0), ("5 km", 5), ("25 km", 25), ("100 km", 100), ("country", None)]
EPS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
R2, NX = 30, 3
ELL3, SIG3, EPS3, KAPPA, NMEM, K = 50, 25, 0.25, 0.4, 5, 80

