"""Statistics tests. ALL series here are SYNTHETIC (generated in the test, seeded) or the real captured POWER fixture.
Synthetic series are never presented as NASA results."""
import numpy as np
import pymannkendall as pmk
import pytest

from app.analysis import stats as st

RNG = np.random.default_rng(12345)


def synthetic(n, slope, noise, seed=1):
    r = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    return t, slope * t + r.normal(0, noise, n)


def test_increasing_series_is_significant_and_positive():
    t, x = synthetic(30, 0.5, 1.0)
    r = st.mann_kendall(x)
    sen = st.sen_slope(x, t, r.var_S)
    assert r.p_value < 0.001 and r.tau > 0.7 and r.S > 0
    assert sen["ci_low"] <= 0.5 <= sen["ci_high"] and abs(sen["slope"] - 0.5) < 0.1


def test_decreasing_series_is_significant_and_negative():
    t, x = synthetic(30, -0.5, 1.0, seed=2)
    r = st.mann_kendall(x)
    sen = st.sen_slope(x, t, r.var_S)
    assert r.p_value < 0.001 and r.tau < -0.7 and sen["slope"] < 0 and sen["ci_high"] < 0


def test_constant_series_gives_no_trend_without_errors():
    x = np.full(25, 7.0)
    r = st.mann_kendall(x)
    sen = st.sen_slope(x, np.arange(25.0), r.var_S)
    assert r.S == 0 and r.p_value == 1.0 and r.tau == 0.0 and sen["slope"] == 0.0 and r.var_S == 0


def test_trendless_noise_is_not_significant():
    _, x = synthetic(40, 0.0, 1.0, seed=7)
    assert st.mann_kendall(x).p_value > 0.05


def test_matches_pymannkendall_original_with_ties():
    r = np.random.default_rng(3)
    x = np.round(r.normal(0, 1, 60).cumsum() * 0.3, 1)         # rounding creates ties
    ours = st.mann_kendall(x)
    ref = pmk.original_test(x)
    assert ours.S == ref.s and ours.var_S == pytest.approx(ref.var_s)
    assert ours.z == pytest.approx(ref.z) and ours.p_value == pytest.approx(ref.p)
    t = np.arange(60.0)
    assert st.sen_slope(x, t, ours.var_S)["slope"] == pytest.approx(ref.slope)


def test_matches_pymannkendall_seasonal():
    r = np.random.default_rng(4)
    years, months = 20, 12
    t = np.repeat(np.arange(years), months) + np.tile(np.arange(months), years) / 12
    x = 10 * np.sin(2 * np.pi * np.tile(np.arange(months), years) / 12) + 0.05 * t + r.normal(0, 1, years * months)
    season = np.tile(np.arange(1, 13), years)
    ours = st.seasonal_mann_kendall(x, season)
    ref = pmk.seasonal_test(x, period=12)
    assert ours.S == ref.s and ours.var_S == pytest.approx(ref.var_s)
    assert ours.p_value == pytest.approx(ref.p, rel=1e-6)
    # seasonal Sen slope: both are per YEAR (one step per season-year)
    sen = st.sen_slope(x, t, ours.var_S, season=season)
    assert sen["slope"] == pytest.approx(ref.slope, rel=1e-2)


def test_hamed_rao_matches_pymannkendall_on_autocorrelated_series():
    r = np.random.default_rng(5)
    e = r.normal(0, 1, 60)
    x = np.zeros(60)
    for i in range(1, 60):
        x[i] = 0.7 * x[i - 1] + e[i]
    t = np.arange(60.0)
    base = st.mann_kendall(x)
    sen = st.sen_slope(x, t, base.var_S)
    factor = st.hamed_rao_variance_factor(x, t, sen["slope"])
    ours = st.apply_variance_factor(base, factor)
    ref = pmk.hamed_rao_modification_test(x)
    assert factor > 1.0                                           # positive autocorrelation inflates variance
    assert ours.p_value > base.p_value                            # corrected p is less optimistic
    assert ours.p_value == pytest.approx(ref.p, rel=0.05)
    assert ours.z == pytest.approx(ref.z, rel=0.05)


def test_sen_slope_uses_real_time_axis_not_the_index():
    # irregular sampling: exact line y = 2*t with gaps
    t = np.array([2000, 2001, 2002, 2007, 2008, 2015, 2016, 2017], float)
    x = 2.0 * t
    var = st.mann_kendall(x).var_S
    assert st.sen_slope(x, t, var)["slope"] == pytest.approx(2.0)
    assert st.sen_slope(x, np.arange(len(x), dtype=float), var)["slope"] != pytest.approx(2.0)   # index-based would be wrong


def test_seasonality_test_detects_and_rejects():
    months = np.tile(np.arange(1, 13), 15)
    seasonal = 10 * np.sin(2 * np.pi * months / 12) + np.random.default_rng(6).normal(0, 1, len(months))
    assert st.seasonality_test(seasonal, months)["significant"]
    flat = np.random.default_rng(8).normal(0, 1, len(months))
    assert not st.seasonality_test(flat, months)["significant"]
    assert not st.seasonality_test(np.ones(len(months)), months)["applicable"]


def test_ljung_box_flags_autocorrelation():
    r = np.random.default_rng(9)
    white = r.normal(0, 1, 200)
    ar = np.zeros(200)
    for i in range(1, 200):
        ar[i] = 0.8 * ar[i - 1] + r.normal()
    assert st.ljung_box(white, 10)[1] > 0.05 and st.ljung_box(ar, 10)[1] < 0.001
