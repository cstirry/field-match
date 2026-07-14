import numpy as np
import pandas as pd
import pytest

from field_match import match_fields, similarity_scores


def test_scores_structure(annual_release):
    last_year, this_year = annual_release
    scores = similarity_scores(last_year, this_year)
    assert list(scores.columns) == [
        "source",
        "target",
        "family",
        "name_score",
        "content_score",
        "score",
    ]
    assert ((scores["score"] >= 0) & (scores["score"] <= 1)).all()


def test_end_to_end_recovers_true_mapping(annual_release):
    last_year, this_year = annual_release
    mapping = {
        str(m.target): str(m.source)
        for m in match_fields(last_year, this_year, match_threshold=0.3)
    }
    assert mapping["Age of Respondent"] == "age"
    assert mapping["HH_INCOME"] == "household_income"
    assert mapping["st"] == "state"
    assert mapping["date_of_survey"] == "survey_date"  # matched despite string dtype
    assert mapping["employed"] == "is_employed"
    # sequential IDs continue from a new offset; shift-invariant scoring catches it
    assert mapping["ID"] == "respondent_id"


def test_one_to_one_assignment(annual_release):
    last_year, this_year = annual_release
    matches = match_fields(last_year, this_year, match_threshold=0.0)
    targets = [m.target for m in matches]
    sources = [m.source for m in matches]
    assert len(targets) == len(set(targets)), "a target column was matched twice"
    assert len(sources) == len(set(sources)), "a source column was matched twice"


def test_string_dates_matched_as_datetime(annual_release):
    last_year, this_year = annual_release
    scores = similarity_scores(last_year, this_year)
    pair = scores[(scores["source"] == "survey_date") & (scores["target"] == "date_of_survey")]
    assert not pair.empty
    assert pair.iloc[0]["family"] == "datetime"


def test_int_matches_float():
    df1 = pd.DataFrame({"count": pd.Series([1, 2, 3], dtype="int64")})
    df2 = pd.DataFrame({"n": pd.Series([1.0, 2.0, 3.0], dtype="float64")})
    scores = similarity_scores(df1, df2)
    assert len(scores) == 1  # old version skipped this pair on dtype mismatch


def test_threshold_filters(annual_release):
    last_year, this_year = annual_release
    assert match_fields(last_year, this_year, match_threshold=1.01) == []


def test_name_weight_validation(annual_release):
    last_year, this_year = annual_release
    with pytest.raises(ValueError):
        similarity_scores(last_year, this_year, name_weight=1.5)


def test_empty_dataframes():
    assert match_fields(pd.DataFrame(), pd.DataFrame()) == []


def test_all_nan_column_does_not_crash():
    df1 = pd.DataFrame({"a": [np.nan, np.nan]})
    df2 = pd.DataFrame({"b": [1.0, 2.0]})
    scores = similarity_scores(df1, df2)
    assert ((scores["score"] >= 0) & (scores["score"] <= 1)).all()


class TestAssignmentStrategies:
    def _ambiguous(self):
        # Two source columns that both look like income; one target.
        df1 = pd.DataFrame({"income": [1.0, 2.0, 3.0], "income_2": [1.0, 2.0, 3.0]})
        df2 = pd.DataFrame({"income": [1.0, 2.0, 3.0]})
        return df1, df2

    def test_optimal_and_greedy_are_one_to_one(self):
        df1, df2 = self._ambiguous()
        for strategy in ("optimal", "greedy"):
            matches = match_fields(df1, df2, match_threshold=0.0, assignment=strategy)
            targets = [m.target for m in matches]
            assert len(targets) == len(set(targets))

    def test_optimal_falls_back_to_greedy_without_scipy(self, annual_release, monkeypatch):
        # With scipy unavailable, assignment="optimal" must warn and fall
        # through to the greedy result instead of crashing.
        import sys

        monkeypatch.setitem(sys.modules, "scipy", None)
        monkeypatch.setitem(sys.modules, "scipy.optimize", None)

        last_year, this_year = annual_release
        with pytest.warns(UserWarning, match="scipy"):
            fell_back = match_fields(
                last_year, this_year, match_threshold=0.3, assignment="optimal"
            )
        greedy = match_fields(last_year, this_year, match_threshold=0.3, assignment="greedy")
        assert fell_back == greedy

    def test_all_returns_every_candidate_above_threshold(self):
        df1, df2 = self._ambiguous()
        matches = match_fields(df1, df2, match_threshold=0.0, assignment="all")
        # both source columns get a candidate against the same target -
        # nothing is picked or deduped
        assert len(matches) == 2
        assert {m.source for m in matches} == {"income", "income_2"}
        assert all(m.target == "income" for m in matches)

    def test_all_respects_threshold(self):
        rng = np.random.default_rng(0)
        df1 = pd.DataFrame({"age": rng.integers(18, 90, 100)})
        df2 = pd.DataFrame({"unrelated": rng.normal(1e9, 1, 100)})
        assert match_fields(df1, df2, match_threshold=0.9, assignment="all") == []

    def test_invalid_strategy_raises(self, annual_release):
        last_year, this_year = annual_release
        with pytest.raises(ValueError, match="assignment"):
            match_fields(last_year, this_year, assignment="bogus")


class TestExactFirst:
    def test_same_named_columns_pair_with_each_other(self):
        # income and revenue hold interchangeable values; without the
        # exact-name presolve, either could claim either. With it, each
        # column must pair with its namesake.
        values = list(np.arange(100, dtype=float))
        df1 = pd.DataFrame({"income": values, "revenue": values})
        df2 = pd.DataFrame({"revenue": values, "income": values})
        mapping = {m.source: m.target for m in match_fields(df1, df2, match_threshold=0.5)}
        assert mapping == {"income": "income", "revenue": "revenue"}

    def test_case_insensitive(self):
        df1 = pd.DataFrame({"FIPS": [51059, 51013]})
        df2 = pd.DataFrame({"fips": [51059, 51107]})
        (match,) = match_fields(df1, df2, match_threshold=0.5)
        assert (match.source, match.target) == ("FIPS", "fips")
        assert match.name_score == 1.0

    def test_family_mismatch_is_not_forced(self):
        # Same name but numbers in one file, free text in the other:
        # the presolve must not lock these together.
        df1 = pd.DataFrame({"code": [1.0, 2.0, 3.0]})
        df2 = pd.DataFrame({"code": ["apples", "pears", "plums"]})
        assert match_fields(df1, df2, match_threshold=0.5) == []

    def test_duplicate_names_fall_through_to_full_comparison(self):
        # "ID" and "id" collide case-insensitively within df1, so the
        # presolve skips them; the full comparison still matches one.
        df1 = pd.DataFrame({"ID": [1.0, 2.0, 3.0], "id": [1.0, 2.0, 3.0]})
        df2 = pd.DataFrame({"id": [1.0, 2.0, 3.0]})
        matches = match_fields(df1, df2, match_threshold=0.5)
        assert len(matches) == 1
        assert matches[0].target == "id"

    def test_below_threshold_namesakes_not_matched(self):
        rng = np.random.default_rng(0)
        df1 = pd.DataFrame({"value": rng.normal(0, 1, 200)})
        df2 = pd.DataFrame({"value": rng.uniform(1e8, 1e9, 200)})
        assert match_fields(df1, df2, match_threshold=0.9) == []

    def test_exact_first_false_matches_full_comparison(self, annual_release):
        # The fixture has no identically named columns, so the presolve
        # must be a no-op and both settings must agree.
        last_year, this_year = annual_release
        with_presolve = match_fields(last_year, this_year, match_threshold=0.3)
        without = match_fields(last_year, this_year, match_threshold=0.3, exact_first=False)
        assert with_presolve == without
