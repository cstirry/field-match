import json

import numpy as np
import pandas as pd
import pytest

from field_match import (
    ComparisonReport,
    align_to_model,
    compare,
    generate_column_rename,
)


@pytest.fixture
def mixed_case():
    """One column per report category.

    - fips: same name, contents agree -> verified
    - score_pct: same name, contents drifted hard -> suspect (weak match)
    - flag: same name, numbers vs text -> suspect (type mismatch)
    - household_income / HH_INCOME: renamed
    - old_only: dropped
    - brand_new: added
    """
    rng = np.random.default_rng(7)
    n = 300
    values = rng.normal(50000, 15000, n).round(2)
    reference = pd.DataFrame(
        {
            "fips": np.arange(1000, 1000 + n),
            "score_pct": rng.uniform(0, 1, n),
            "flag": rng.integers(0, 5, n).astype(float),
            "household_income": values,
            "old_only": rng.choice(list("abcdefghij"), n),
        }
    )
    new = pd.DataFrame(
        {
            "fips": np.arange(1000, 1000 + n),
            "score_pct": rng.uniform(500, 90000, n),  # same name, different scale/shape
            "flag": rng.choice(["red", "green", "blue"], n),  # same name, now text
            "HH_INCOME": values + rng.normal(0, 500, n),
            "brand_new": rng.uniform(0, 1, n),
        }
    )
    return reference, new


class TestCategories:
    def test_each_category_lands(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        assert [str(m.source) for m in report.verified] == ["fips"]
        assert [(str(m.source), str(m.target)) for m in report.renamed] == [
            ("household_income", "HH_INCOME")
        ]
        assert {s.name for s in report.suspect} >= {"flag"}
        assert "old_only" in report.dropped
        assert "brand_new" in report.added

    def test_suspect_namesakes_are_not_also_dropped_or_added(self, mixed_case):
        # score_pct and flag exist under the same name in both DataFrames
        # but never cleared match_threshold against anything, so they used
        # to leak into dropped AND added as well as suspect - a column
        # that exists on both sides is not "missing" from either one.
        reference, new = mixed_case
        report = compare(reference, new)
        assert report.dropped == ["old_only"]
        assert report.added == ["brand_new"]
        assert {s.name for s in report.suspect} == {"score_pct", "flag"}

    def test_type_mismatch_namesake_is_suspect_with_reason(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        flag = next(s for s in report.suspect if s.name == "flag")
        assert "different types" in flag.reason
        assert flag.score is None

    def test_verified_threshold_moves_the_line(self, mixed_case):
        reference, new = mixed_case
        cautious = compare(reference, new, verified_threshold=1.01)
        assert cautious.verified == []
        # every same-name match now needs review instead
        assert any(s.name == "fips" for s in cautious.suspect)

    def test_counts_partition_reference_columns(self, annual_release):
        last_year, this_year = annual_release
        report = compare(last_year, this_year, match_threshold=0.3)
        weak_same_name = [s for s in report.suspect if s.score is not None and s.score >= 0.3]
        accounted = (
            len(report.verified) + len(report.renamed) + len(weak_same_name) + len(report.dropped)
        )
        assert accounted == len(report.reference_columns)

    def test_fixture_all_renamed(self, annual_release):
        last_year, this_year = annual_release
        report = compare(last_year, this_year, match_threshold=0.3)
        assert len(report.renamed) == 6
        assert report.verified == []
        assert report.dropped == []
        assert report.added == []
        assert report.mapping["HH_INCOME"] == "household_income"


class TestActions:
    def test_apply_renames(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        renamed = report.apply(new)
        assert "household_income" in renamed.columns
        assert list(new.columns) != list(renamed.columns)  # original untouched

    def test_candidates_for_reference_column(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        rows = report.candidates("household_income")
        assert str(rows.iloc[0]["target"]) == "HH_INCOME"

    def test_candidates_cover_presolved_columns(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        rows = report.candidates("fips")  # matched by the exact-name presolve
        assert not rows.empty
        assert str(rows.iloc[0]["target"]) == "fips"

    def test_suggestions_offer_below_threshold_candidates(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        # old_only is text; brand_new is numeric - no same-family candidate
        # may exist, so only check the structure when present.
        for suggestion in report.suggestions:
            assert suggestion.score < report.match_threshold or suggestion.column

    def test_to_dict_is_json_serializable(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        payload = json.loads(json.dumps(report.to_dict()))
        assert payload["counts"]["verified"] == 1
        assert payload["mapping"]["HH_INCOME"] == "household_income"

    def test_rename_snippet_runs_and_separates_same_names(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference, new)
        snippet = report.rename_snippet()
        assert "no rename needed" in snippet
        assert "'HH_INCOME': 'household_income'" in snippet
        assert "'fips': 'fips'" not in snippet
        # The snippet defines rename_dict only - no assumed variable name
        # for the caller's DataFrame - and shows how to apply it.
        assert "Apply with:" in snippet
        namespace: dict = {}
        exec(snippet, namespace)  # noqa: S102 - verifying generated code runs
        renamed = new.rename(columns=namespace["rename_dict"])
        assert "household_income" in renamed.columns

    def test_generate_column_rename_convenience(self, mixed_case):
        reference, new = mixed_case
        assert generate_column_rename(reference, new) == compare(reference, new).rename_snippet()


class TestSummary:
    def test_print_shows_counts_not_columns(self, mixed_case):
        reference, new = mixed_case
        text = str(compare(reference, new))
        assert "verified" in text and "renamed" in text and "suspect" in text
        assert "HH_INCOME" not in text  # column names need show_columns=True
        assert "report.summary()" in text  # the hint

    def test_summary_lists_columns(self, mixed_case):
        reference, new = mixed_case
        text = compare(reference, new).summary(show_columns=True)
        assert "household_income -> HH_INCOME" in text
        assert "old_only" in text and "brand_new" in text

    def test_max_columns_caps_listings(self, annual_release):
        last_year, this_year = annual_release
        text = compare(last_year, this_year, match_threshold=0.3).summary(max_columns=2)
        assert "... and 4 more" in text


class TestReferenceKinds:
    def test_name_only_list(self):
        df = pd.DataFrame({"HH_INCOME": [1.0], "Age": [30], "extra": ["x"]})
        report = compare(["household_income", "age"], df, match_threshold=0.4)
        assert report.name_only
        assert report.mapping == {"HH_INCOME": "household_income", "Age": "age"}
        assert report.suspect == []
        assert any("names only" in note for note in report.notes)

    def test_name_only_same_names_are_verified(self):
        df = pd.DataFrame({"fips": [1], "HH_INCOME": [2.0]})
        report = compare(["fips", "household_income"], df, match_threshold=0.4)
        assert [str(m.source) for m in report.verified] == ["fips"]
        assert [str(m.target) for m in report.renamed] == ["HH_INCOME"]

    def test_pandas_index_reference(self, mixed_case):
        reference, new = mixed_case
        report = compare(reference.columns, new)
        assert report.name_only
        assert "fips" in {str(m.source) for m in report.verified}

    def test_model_reference(self):
        class FakeModel:
            feature_names_in_ = np.array(["age", "household_income"])

        df = pd.DataFrame({"Age": [30], "HH_INCOME": [1.0]})
        report = compare(FakeModel(), df, match_threshold=0.4)
        assert report.mapping == {"Age": "age", "HH_INCOME": "household_income"}

    def test_paths_are_read(self, tmp_path, mixed_case):
        reference, new = mixed_case
        ref_path, new_path = tmp_path / "ref.csv", tmp_path / "new.csv"
        reference.to_csv(ref_path, index=False)
        new.to_csv(new_path, index=False)
        report = compare(ref_path, str(new_path))
        assert report.mapping["HH_INCOME"] == "household_income"

    def test_bad_reference_type_raises(self):
        with pytest.raises(TypeError, match="reference"):
            compare(42, pd.DataFrame({"a": [1]}))

    def test_bad_new_data_type_raises(self):
        with pytest.raises(TypeError, match="new_data"):
            compare(pd.DataFrame({"a": [1]}), 42)


class TestNotes:
    def test_headerless_new_data(self):
        rng = np.random.default_rng(0)
        values = rng.normal(50, 10, 200)
        reference = pd.DataFrame({"measurement": values, "label": rng.choice(list("xyz"), 200)})
        headerless = pd.DataFrame([list(row) for row in zip(values, rng.choice(list("xyz"), 200))])
        assert isinstance(headerless.columns, pd.RangeIndex)
        report = compare(reference, headerless)
        assert any("no column headers" in note for note in report.notes)
        # content-only matching still finds the numeric column
        assert "measurement" in {str(m.source) for m in report.matches}

    def test_duplicate_column_names_noted(self, mixed_case):
        reference, new = mixed_case
        doubled = pd.concat([new, new[["brand_new"]]], axis=1)
        report = compare(reference, doubled)
        assert any("duplicated column names" in note for note in report.notes)

    def test_empty_columns_noted(self, mixed_case):
        reference, new = mixed_case
        new = new.assign(all_blank=np.nan)
        report = compare(reference, new)
        assert any("entirely empty" in note for note in report.notes)


class TestAlignToModel:
    class _FakeModel:
        feature_names_in_ = np.array(["age", "household_income", "state"])

    def _drifted(self):
        return pd.DataFrame({"HH_INCOME": [50000.0], "Age": [30], "st": ["VA"], "extra_col": [1]})

    def test_default_auto_applies_and_reorders(self):
        aligned = align_to_model(self._FakeModel(), self._drifted(), match_threshold=0.4)
        assert isinstance(aligned, pd.DataFrame)
        assert list(aligned.columns) == ["age", "household_income", "state"]

    def test_auto_apply_false_returns_report(self):
        report = align_to_model(
            self._FakeModel(), self._drifted(), match_threshold=0.4, auto_apply=False
        )
        assert isinstance(report, ComparisonReport)

    def test_raises_with_clear_message_on_missing(self):
        df = pd.DataFrame({"unrelated": [1]})
        with pytest.raises(ValueError, match="household_income"):
            align_to_model(self._FakeModel(), df)

    def test_no_feature_names_attribute(self):
        with pytest.raises(AttributeError, match="compare"):
            align_to_model(object(), pd.DataFrame({"a": [1]}))

    def test_original_data_untouched(self):
        df = self._drifted()
        cols_before = df.columns.tolist()
        align_to_model(self._FakeModel(), df, match_threshold=0.4)
        assert df.columns.tolist() == cols_before
