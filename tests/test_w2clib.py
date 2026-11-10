"""Unit tests for the simulation library (code/w2clib.py). No downloaded data needed."""
import numpy as np
import pytest
from scipy.stats import spearmanr

import w2clib as w


def rng(seed=0):
    return np.random.default_rng(seed)


def test_theory_spearman_limits():
    assert w.theory_spearman(0.0, 50.0) == pytest.approx(1.0)
    assert w.theory_spearman(1e6, 50.0) == pytest.approx(0.0, abs=1e-6)
    # sigma = ell/3 gives Pearson rho = 0.9, the paper's design rule
    rho = 6 / np.pi * np.arcsin(0.9 / 2)
    assert w.theory_spearman(50 / 3, 50.0) == pytest.approx(rho)


def test_to_xyz_on_sphere():
    lat = np.array([0.0, 45.0, -90.0, 13.75])
    lon = np.array([0.0, 100.0, 0.0, 100.5])
    assert np.linalg.norm(w.to_xyz(lat, lon), axis=1) == pytest.approx(np.full(4, w.R_EARTH))


def test_perturb_zero_sigma_is_identity():
    lat, lon = np.array([10.0, -20.0]), np.array([100.0, -60.0])
    la, lo = w.perturb(lat, lon, 0, rng())
    assert np.array_equal(la, lat) and np.array_equal(lo, lon)


def test_perturb_displacement_scale():
    n, sigma = 20000, 25.0
    lat, lon = np.zeros(n), np.zeros(n)
    la, lo = w.perturb(lat, lon, sigma, rng(1))
    dy, dx = la * w.KM_PER_DEG, lo * w.KM_PER_DEG
    assert dy.std() == pytest.approx(sigma, rel=0.03)
    assert dx.std() == pytest.approx(sigma, rel=0.03)


def test_field_unit_variance_and_theory():
    """Field values have unit variance, and the exposure correlation under location error follows the theory."""
    r = rng(2)
    n, ell, sigma = 4000, 100.0, 50.0
    lat, lon = r.uniform(-50, 50, n), r.uniform(-180, 180, n)
    f = w.Field(ell, 2048, r)
    z0 = f.at(lat, lon)
    assert z0.var() == pytest.approx(1.0, abs=0.15)
    z1 = f.at(*w.perturb(lat, lon, sigma, r))
    assert spearmanr(z0, z1)[0] == pytest.approx(w.theory_spearman(sigma, ell), abs=0.05)


def test_disclosure_level_shares():
    FE = rng(3).uniform(size=100000)
    D = w.gen_disclosure(FE, 0.4, rng(4))
    shares = np.bincount(D, minlength=5) / len(D)
    assert shares == pytest.approx(w.LEVEL_SHARES, abs=0.01)


def test_extract_stays_in_range_and_moves_one_level():
    D = np.repeat(np.arange(5), 2000)
    assert np.array_equal(w.extract(D, 0.0, rng()), D)
    Dh = w.extract(D, 0.5, rng(5))
    assert Dh.min() >= 0 and Dh.max() <= 4
    assert np.abs(Dh - D).max() == 1
    assert (Dh != D).mean() == pytest.approx(0.5, abs=0.02)


def test_quadrants():
    FE = np.array([0.9, 0.9, 0.1, 0.1])
    D = np.array([3, 0, 4, 1])
    assert list(w.quadrant(FE, D)) == [w.AWARE, w.SILENT, w.CHEAP, w.BENIGN]


def test_posterior_table_is_row_stochastic():
    P = w.posterior_table(0.25, rng(6))
    assert P.shape == (5, 5)
    assert P.sum(axis=1) == pytest.approx(np.ones(5))
    # the diagonal dominates when extraction is mostly right
    assert np.all(np.argmax(P, axis=1) == np.arange(5))


def test_sample_posterior_follows_table():
    P = np.tile(np.array([0.1, 0.2, 0.4, 0.2, 0.1]), (5, 1))
    draws = w.sample_posterior(np.zeros(50000, dtype=int), P, rng(7))
    assert np.bincount(draws, minlength=5) / len(draws) == pytest.approx(P[0], abs=0.01)


def test_firm_exposure_is_weighted_mean():
    z = np.array([0.0, 0.0, 10.0])
    firm = np.array([0, 0, 1])
    wt = np.array([0.5, 0.5, 1.0])
    assert w.firm_exposure(z, firm, wt, 2) == pytest.approx([0.5, 1.0])
