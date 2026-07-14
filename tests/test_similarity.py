import numpy as np
import pandas as pd
import pytest

from field_match.similarity import (
    boolean_similarity,
    datetime_similarity,
    name_similarity,
    numeric_similarity,
    text_similarity,
)


class TestNameSimilarity:
    def test_identical(self):
        assert name_similarity("income", "income") == 1.0

    def test_case_and_separator_insensitive(self):
        assert name_similarity("CustomerID", "customer_id") == 1.0

    def test_word_order(self):
        assert name_similarity("id_customer", "customer_id") == 1.0

    def test_partial_overlap_beats_none(self):
        related = name_similarity("total_income_2021", "total_income_2022")
        unrelated = name_similarity("total_income_2021", "zip_code")
        assert related > unrelated

    def test_abbreviation(self):
        assert name_similarity("qty", "quantity") > 0.5

    def test_empty(self):
        assert name_similarity("", "income") == 0.0


class TestNumericSimilarity:
    def test_identical_distributions(self):
        s = pd.Series(np.arange(100, dtype=float))
        assert numeric_similarity(s, s) == 1.0

    def test_different_shape_distributions_score_low(self):
        # Shifted-but-same-shape columns intentionally score HIGH (annual
        # drift); genuinely different shapes/scales must score low.
        s1 = pd.Series(np.random.default_rng(0).normal(0, 1, 500))
        s2 = pd.Series(np.random.default_rng(1).uniform(-5000, 5000, 500))
        assert numeric_similarity(s1, s2) < 0.5

    def test_similar_beats_different(self):
        rng = np.random.default_rng(0)
        ages_1 = pd.Series(rng.integers(18, 90, 300).astype(float))
        ages_2 = pd.Series(rng.integers(18, 90, 300).astype(float))
        incomes = pd.Series(rng.normal(55000, 20000, 300))
        assert numeric_similarity(ages_1, ages_2) > numeric_similarity(ages_1, incomes)

    def test_negative_values_bounded(self):
        s1 = pd.Series([-100.0, -50.0, -10.0])
        s2 = pd.Series([-90.0, -40.0, -5.0])
        assert 0.0 <= numeric_similarity(s1, s2) <= 1.0

    def test_all_nan_returns_zero(self):
        s1 = pd.Series([np.nan, np.nan], dtype=float)
        s2 = pd.Series([1.0, 2.0])
        assert numeric_similarity(s1, s2) == 0.0

    def test_empty_returns_zero(self):
        assert numeric_similarity(pd.Series([], dtype=float), pd.Series([1.0])) == 0.0


class TestDatetimeSimilarity:
    def test_same_period_beats_different(self):
        y2021 = pd.Series(pd.date_range("2021-01-01", "2021-12-31", freq="D"))
        y2021_b = pd.Series(pd.date_range("2021-01-15", "2021-12-15", freq="D"))
        y1990 = pd.Series(pd.date_range("1990-01-01", "1990-12-31", freq="D"))
        assert datetime_similarity(y2021, y2021_b) > datetime_similarity(y2021, y1990)

    def test_bounded(self):
        s1 = pd.Series(pd.to_datetime(["2021-01-01", "2021-06-01"]))
        s2 = pd.Series(pd.to_datetime(["1980-01-01"]))
        assert 0.0 <= datetime_similarity(s1, s2) <= 1.0


class TestBooleanSimilarity:
    def test_identical_proportions(self):
        s1 = pd.Series([True, False, True, False])
        s2 = pd.Series([False, True])
        assert boolean_similarity(s1, s2) == 1.0

    def test_always_bounded(self):
        # Old implementation returned negative values here.
        s1 = pd.Series([True] * 99 + [False])
        s2 = pd.Series([False] * 99 + [True])
        assert 0.0 <= boolean_similarity(s1, s2) <= 1.0

    def test_empty_returns_zero(self):
        assert boolean_similarity(pd.Series([], dtype=bool), pd.Series([True])) == 0.0


class TestTextSimilarity:
    def test_identical_categories(self):
        s = pd.Series(["VA", "MD", "DC", "VA"])
        assert text_similarity(s, s) == 1.0

    def test_overlapping_categories_beat_disjoint(self):
        states_1 = pd.Series(["VA", "MD", "DC", "WV"])
        states_2 = pd.Series(["VA", "MD", "PA", "DE"])
        colors = pd.Series(["red", "green", "blue"])
        assert text_similarity(states_1, states_2) > text_similarity(states_1, colors)

    def test_sampling_is_deterministic(self):
        s1 = pd.Series([f"value {i}" for i in range(5000)])
        s2 = pd.Series([f"value {i}" for i in range(2500, 7500)])
        assert text_similarity(s1, s2) == text_similarity(s1, s2)

    def test_empty_returns_zero(self):
        assert text_similarity(pd.Series([], dtype=str), pd.Series(["a"])) == 0.0


@pytest.mark.parametrize(
    "func",
    [numeric_similarity, boolean_similarity, text_similarity],
)
def test_symmetry(func):
    if func is boolean_similarity:
        s1, s2 = pd.Series([True, True, False]), pd.Series([False, False, True])
    elif func is text_similarity:
        s1, s2 = pd.Series(["a", "b", "c"]), pd.Series(["b", "c", "d"])
    else:
        s1, s2 = pd.Series([1.0, 2.0, 3.0]), pd.Series([2.0, 3.0, 4.0])
    assert func(s1, s2) == pytest.approx(func(s2, s1))


class TestShiftInvariance:
    """Annual releases shift in location but keep shape - must still match."""

    def test_next_years_dates_match(self):
        rng = np.random.default_rng(0)
        d2021 = pd.Series(
            pd.to_datetime("2021-01-01") + pd.to_timedelta(rng.integers(0, 364, 300), unit="D")
        )
        d2022 = pd.Series(
            pd.to_datetime("2022-01-01") + pd.to_timedelta(rng.integers(0, 364, 300), unit="D")
        )
        assert datetime_similarity(d2021, d2022) > 0.7

    def test_continuing_sequential_ids_match(self):
        ids_2021 = pd.Series(np.arange(1, 401, dtype=float))
        ids_2022 = pd.Series(np.arange(5001, 5401, dtype=float))
        assert numeric_similarity(ids_2021, ids_2022) > 0.7

    def test_different_shapes_still_distinguished(self):
        rng = np.random.default_rng(0)
        ages = pd.Series(rng.integers(18, 90, 300).astype(float))
        incomes = pd.Series(rng.normal(55000, 20000, 300))
        # centering must not make age look like income (spreads differ hugely)
        assert numeric_similarity(ages, incomes) < 0.5
