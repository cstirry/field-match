"""The main entry point: compare new data against a reference and report.

``compare()`` accepts whatever reference you have - a previous dataset,
a list of expected column names, or a fitted sklearn model - and returns
a :class:`ComparisonReport`: the summary of what happened (verified,
renamed, suspect, dropped, added) plus the evidence behind it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .io import read_table
from .matching import (
    _SCORE_COLUMNS,
    FieldMatch,
    _infer_family,
    _match_with_scores,
    _resolve_assignment,
)
from .similarity import name_similarity

__all__ = [
    "Candidate",
    "ComparisonReport",
    "Suspect",
    "align_to_model",
    "compare",
    "generate_column_rename",
]


@dataclass(frozen=True)
class Suspect:
    """A column name both datasets share whose contents do not line up."""

    name: str
    reason: str
    score: float | None = None  # the namesake pair's own score, when comparable


@dataclass(frozen=True)
class Candidate:
    """The closest available candidate for an otherwise unmatched column."""

    column: str  # the dropped reference column
    candidate: str  # its closest column in the new data
    score: float


_BLURBS = {
    "verified": "column name and contents both match",
    "renamed": "contents match, but under a different column name",
    "suspect": "column name matches, but contents do not",
    "dropped": "missing from the new dataset",
    "added": "missing from the reference dataset",
}


@dataclass(frozen=True)
class ComparisonReport:
    """Everything :func:`compare` found, summary and evidence together.

    The five category fields answer "what happened":

    - ``verified``: matched under the same name with contents that agree.
    - ``renamed``: matched confidently, but under a different name.
    - ``suspect``: the name exists on both sides but the pair does not
      line up (different content types, drifted contents, or each side
      matched something else).
    - ``dropped``: reference columns with no acceptable match.
    - ``added``: new columns nothing claimed.

    ``print(report)`` shows the counts; ``report.summary()`` adds the
    column names. The evidence behind every decision is in
    ``report.scores`` and ``report.candidates(column)``.

    Attributes
    ----------
    verified : list of FieldMatch
        Matched under the same name with contents that agree.
    renamed : list of FieldMatch
        Matched confidently, but under a different name.
    suspect : list of Suspect
        Same name on both sides, but the pair does not line up; each
        entry carries a plain-language ``reason``.
    dropped : list of str
        Reference columns with no acceptable match.
    added : list of str
        New columns nothing claimed.
    suggestions : list of Candidate
        For each dropped column, its closest below-threshold
        candidate, if any.
    matches : list of FieldMatch
        Every accepted match: verified, renamed, and drifted namesakes.
    mapping : dict of str to str
        ``{new_column: reference_column}`` for every accepted match.
    scores : pandas.DataFrame
        The full evidence table, one row per compared pair (see
        :func:`field_match.matching.similarity_scores`).
    notes : list of str
        Warnings about conditions that affect what could be verified
        (headerless data, duplicate names, empty columns).
    reference_columns : list of str
        Every column name from the reference side.
    new_columns : list of str
        Every column name from the new data.
    row_counts : tuple of (int or None, int)
        Reference row count (``None`` for a names-only comparison) and
        new data row count.
    match_threshold : float
        The ``match_threshold`` this report was generated with.
    verified_threshold : float
        The ``verified_threshold`` this report was generated with.
    name_only : bool
        Whether the reference was column names only, so contents were
        not checked.
    """

    verified: list[FieldMatch]
    renamed: list[FieldMatch]
    suspect: list[Suspect]
    dropped: list[str]
    added: list[str]
    suggestions: list[Candidate]
    matches: list[FieldMatch]  # every accepted match (verified + renamed + drifted namesakes)
    mapping: dict[str, str]  # {new_column: reference_column}
    scores: pd.DataFrame  # the full evidence table (see similarity_scores)
    notes: list[str]
    reference_columns: list[str]
    new_columns: list[str]
    row_counts: tuple[int | None, int]  # reference rows (None if names-only), new rows
    match_threshold: float
    verified_threshold: float
    name_only: bool

    # ---------------------------------------------------------- actions
    def apply(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of ``new_df`` renamed to the reference's names."""
        return new_df.rename(columns=self.mapping)

    def candidates(self, column, limit: int = 5) -> pd.DataFrame:
        """Ranked candidates for one column, from the evidence table.

        Looks the column up on the reference side first, then the new
        side, and returns its best-scoring counterparts.
        """
        col = str(column)
        rows = self.scores[self.scores["source"].astype(str) == col]
        if rows.empty:
            rows = self.scores[self.scores["target"].astype(str) == col]
        return rows.sort_values("score", ascending=False).head(limit).reset_index(drop=True)

    def rename_snippet(self) -> str:
        """A reviewable rename_dict, for pasting into your own script.

        Same-name matches are listed in a leading comment (verified,
        nothing to rename); actual renames go in the dict, in the new
        file's own column order so the snippet reads alongside the file.
        Only the dict is emitted - apply it with your own DataFrame's
        variable name, as shown in the trailing comment.
        """
        position = {str(col): i for i, col in enumerate(self.new_columns)}
        ordered = sorted(self.matches, key=lambda m: position.get(str(m.target), len(position)))
        same_name = [m for m in ordered if str(m.target) == str(m.source)]
        renames = [m for m in ordered if str(m.target) != str(m.source)]

        lines = []
        if same_name:
            lines.append("# Matched with the same name in both files - no rename needed:")
            lines.extend(f"#   {m.target!r}  (score={m.score:.2f}, {m.family})" for m in same_name)
        lines.append("rename_dict = {")
        for m in renames:
            lines.append(f"    {m.target!r}: {m.source!r},  # score={m.score:.2f} ({m.family})")
        lines.append("}")
        lines.append("# Apply with: new_df = new_df.rename(columns=rename_dict)")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """A JSON-friendly version of the report, for logs and alerts."""
        return {
            "counts": {
                "verified": len(self.verified),
                "renamed": len(self.renamed),
                "suspect": len(self.suspect),
                "dropped": len(self.dropped),
                "added": len(self.added),
            },
            "verified": [asdict(m) for m in self.verified],
            "renamed": [asdict(m) for m in self.renamed],
            "suspect": [asdict(s) for s in self.suspect],
            "dropped": list(self.dropped),
            "added": list(self.added),
            "suggestions": [asdict(c) for c in self.suggestions],
            "mapping": dict(self.mapping),
            "notes": list(self.notes),
            "reference_columns": list(self.reference_columns),
            "new_columns": list(self.new_columns),
            "row_counts": list(self.row_counts),
            "match_threshold": self.match_threshold,
            "verified_threshold": self.verified_threshold,
            "name_only": self.name_only,
        }

    # ---------------------------------------------------------- display
    def summary(self, show_columns: bool = True, max_columns: int = 8) -> str:
        """The report as readable text.

        ``show_columns=False`` gives just the counts and notes;
        ``True`` (default) also lists what is in each category, capped
        at ``max_columns`` entries per category.
        """

        def clip(items: list[str]) -> str:
            shown = ", ".join(items[:max_columns])
            extra = len(items) - max_columns
            return shown + (f", ... and {extra} more" if extra > 0 else "")

        ref_rows, new_rows = self.row_counts
        rows_bit = (
            f"{ref_rows:,} vs {new_rows:,} rows"
            if ref_rows is not None
            else f"{new_rows:,} new rows"
        )
        lines = [
            f"field-match comparison: {len(self.reference_columns)} reference columns "
            f"vs {len(self.new_columns)} new columns",
            f"({rows_bit}; match_threshold {self.match_threshold:.2f}, "
            f"verified_threshold {self.verified_threshold:.2f})",
            "",
        ]
        counts = {name: len(getattr(self, name)) for name in _BLURBS}
        width = max(len(str(n)) for n in counts.values())
        for name, count in counts.items():
            lines.append(f"  {count:>{width}}  {name:<9} {_BLURBS[name]}")

        for note in self.notes:
            lines.append("")
            lines.append(f"  note: {note}")

        if not show_columns:
            lines.append("")
            lines.append("Use report.summary() to list the columns in each category.")
            return "\n".join(lines)

        if self.verified:
            lines += ["", "verified: " + clip([str(m.source) for m in self.verified])]
        if self.renamed:
            lines += ["", "renamed:"]
            lines += [
                f"  {m.source} -> {m.target}  (score {m.score:.2f}, {m.family})"
                for m in self.renamed[:max_columns]
            ]
            if len(self.renamed) > max_columns:
                lines.append(f"  ... and {len(self.renamed) - max_columns} more")
        if self.suspect:
            lines += ["", "suspect:"]
            lines += [f"  {s.name}: {s.reason}" for s in self.suspect[:max_columns]]
            if len(self.suspect) > max_columns:
                lines.append(f"  ... and {len(self.suspect) - max_columns} more")
        if self.dropped:
            lines += ["", "dropped: " + clip(self.dropped)]
        if self.added:
            lines += ["", "added: " + clip(self.added)]
        if self.suggestions:
            target_owner = {str(m.target): str(m.source) for m in self.matches}
            lines += ["", "closest candidates for dropped columns:"]
            for c in self.suggestions[:max_columns]:
                why = (
                    f"already claimed by {target_owner[c.candidate]}"
                    if c.candidate in target_owner
                    else "below match_threshold"
                )
                lines.append(f"  {c.column}: {c.candidate}  (score {c.score:.2f}, {why})")
            if len(self.suggestions) > max_columns:
                lines.append(f"  ... and {len(self.suggestions) - max_columns} more")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary(show_columns=False)


def _same_name(match: FieldMatch) -> bool:
    return str(match.source).strip().lower() == str(match.target).strip().lower()


def _coerce_reference(reference):
    """Sort out what kind of reference we were given.

    Returns ``(reference_df_or_None, expected_names_or_None)``: a
    DataFrame for full name+content comparison, or a list of names for
    name-only comparison.
    """
    if isinstance(reference, (str, Path)):
        reference = read_table(reference)
    if isinstance(reference, pd.DataFrame):
        return reference, None
    feature_names = getattr(reference, "feature_names_in_", None)
    if feature_names is not None:
        return None, [str(c) for c in feature_names]
    if isinstance(reference, (list, tuple, set, pd.Index, pd.Series)):
        names = sorted(reference, key=str) if isinstance(reference, set) else list(reference)
        return None, [str(c) for c in names]
    raise TypeError(
        "reference must be a DataFrame, a path to a data file, a list of "
        f"expected column names, or a fitted model, got {type(reference).__name__}"
    )


def _headerless(df: pd.DataFrame) -> bool:
    """True when the columns are pandas' automatic numbering (no headers)."""
    return isinstance(df.columns, pd.RangeIndex)


def _data_notes(df: pd.DataFrame, side: str) -> tuple[pd.DataFrame, list[str]]:
    """Warnings about one DataFrame: duplicate names, empty columns.

    Returns the frame with duplicate-named columns reduced to their
    first occurrence (pandas cannot address the copies individually),
    along with the notes.
    """
    notes = []
    duplicated = sorted({str(c) for c in df.columns[df.columns.duplicated()]})
    if duplicated:
        notes.append(
            f"the {side} has duplicated column names ({', '.join(duplicated)}); "
            "only the first occurrence of each was matched"
        )
        df = df.loc[:, ~df.columns.duplicated()]
    empty = [str(c) for c in df.columns if df[c].isna().all()]
    if empty:
        shown = ", ".join(empty[:6]) + (", ..." if len(empty) > 6 else "")
        notes.append(
            f"{len(empty)} {side} column(s) are entirely empty and cannot be "
            f"checked by contents: {shown}"
        )
    return df, notes


def _match_names_only(
    expected: list[str], actual: list[str], match_threshold: float
) -> tuple[list[FieldMatch], pd.DataFrame]:
    """Name-only matching for when the reference has no values."""
    rows = [
        {
            "source": e,
            "target": a,
            "family": "name_only",
            "name_score": round(name_similarity(e, a), 3),
            "content_score": 0.0,
            "score": round(name_similarity(e, a), 3),
        }
        for e in expected
        for a in actual
    ]
    scores = pd.DataFrame(rows, columns=_SCORE_COLUMNS)
    if scores.empty:
        return [], scores
    scores = scores.sort_values(["source", "score"], ascending=[True, False]).reset_index(drop=True)

    matrix = scores.pivot_table(index="source", columns="target", values="score").fillna(0.0)
    sources, targets = list(matrix.index), list(matrix.columns)
    values = matrix.to_numpy()
    pairs = _resolve_assignment(matrix, "optimal")
    matches = [
        FieldMatch(
            source=sources[i],
            target=targets[j],
            score=round(float(values[i, j]), 3),
            name_score=round(float(values[i, j]), 3),
            content_score=0.0,
            family="name_only",
        )
        for i, j in pairs
        if values[i, j] >= match_threshold
    ]
    return sorted(matches, key=lambda m: m.score, reverse=True), scores


def _find_suspects(
    reference: pd.DataFrame,
    new_data: pd.DataFrame,
    matches: list[FieldMatch],
    scores: pd.DataFrame,
    verified_threshold: float,
    sample_size: int,
    random_state: int,
) -> tuple[list[Suspect], set[str], set[str]]:
    """Shared column names whose pairs do not line up.

    Also returns the reference-side and new-side column names accounted
    for by these suspects, so the caller can keep them out of dropped/
    added - a column flagged as suspect is not also "missing".
    """
    suspects = []
    accounted_ref: set[str] = set()
    accounted_new: set[str] = set()

    # Matched their namesake, but the contents drifted more than usual.
    for m in matches:
        if _same_name(m) and m.score < verified_threshold:
            suspects.append(
                Suspect(
                    name=str(m.source),
                    reason=(
                        f"matched its namesake, but the contents drifted "
                        f"(score {m.score:.2f} is below verified_threshold "
                        f"{verified_threshold:.2f})"
                    ),
                    score=m.score,
                )
            )
            accounted_ref.add(str(m.source))
            accounted_new.add(str(m.target))

    # Namesakes that were NOT matched to each other.
    def _sample(df):
        return df.sample(sample_size, random_state=random_state) if len(df) > sample_size else df

    def _unique_by_lower(df):
        names: dict[str, list] = {}
        for col in df.columns:
            names.setdefault(str(col).lower(), []).append(col)
        return {k: cols[0] for k, cols in names.items() if len(cols) == 1}

    matched_pairs = {(str(m.source).lower(), str(m.target).lower()) for m in matches}
    ref_names, new_names = _unique_by_lower(reference), _unique_by_lower(new_data)
    sampled_ref, sampled_new = _sample(reference), _sample(new_data)

    for key in sorted(ref_names.keys() & new_names.keys()):
        if (key, key) in matched_pairs:
            continue
        ref_col, new_col = ref_names[key], new_names[key]
        ref_family = _infer_family(sampled_ref[ref_col])[0]
        new_family = _infer_family(sampled_new[new_col])[0]
        if ref_family != new_family:
            reason = (
                f"contents are different types ({ref_family} in the reference, "
                f"{new_family} in the new data)"
            )
            pair_score = None
        else:
            pair = scores[
                (scores["source"].astype(str) == str(ref_col))
                & (scores["target"].astype(str) == str(new_col))
            ]
            pair_score = float(pair.iloc[0]["score"]) if len(pair) else None
            reason = (
                f"namesakes scored only {pair_score:.2f} against each other"
                if pair_score is not None
                else "namesakes were not comparable"
            )
        ref_match = next((m for m in matches if str(m.source) == str(ref_col)), None)
        new_match = next((m for m in matches if str(m.target) == str(new_col)), None)
        if ref_match is not None:
            reason += f"; the reference column matched {str(ref_match.target)!r} instead"
        if new_match is not None:
            reason += f"; the new column matched from {str(new_match.source)!r} instead"
        suspects.append(Suspect(name=str(ref_col), reason=reason, score=pair_score))
        accounted_ref.add(str(ref_col))
        accounted_new.add(str(new_col))

    return suspects, accounted_ref, accounted_new


def compare(
    reference,
    new_data,
    *,
    match_threshold: float = 0.5,
    verified_threshold: float = 0.75,
    name_weight: float = 0.4,
    sample_size: int = 2000,
    random_state: int = 0,
    exact_first: bool = True,
) -> ComparisonReport:
    """Compare new data against a reference and report what changed.

    Parameters
    ----------
    reference:
        Whatever you have; the more it contains, the more can be
        verified. A DataFrame (or path to one) compares names AND
        contents. A list of expected column names (or anything with
        ``feature_names_in_``, like a fitted sklearn model) compares
        names only, and the report says so.
    new_data:
        The data to check: a DataFrame or a path readable by
        :func:`read_table`.
    match_threshold:
        Minimum score in ``[0, 1]`` to propose a match at all; higher
        means fewer, more confident matches. Default 0.5.
    verified_threshold:
        Minimum score in ``[0, 1]`` for a same-name match to count as
        verified; below it the pair is listed as suspect. Higher sends
        more borderline same-name matches to suspect. Default 0.75.
    name_weight:
        How the score is split between names and contents: 0 judges
        only by the values (used automatically for headerless data),
        1 only by the names. Default 0.4.
    sample_size:
        Rows sampled from large files before content comparison.
    random_state:
        Seed for sampling, for reproducible scores.
    exact_first:
        Pair identically named, same-type columns immediately instead
        of comparing them against everything (faster, and namesakes
        cannot be stolen by fuzzy lookalikes). Default True.

    Returns
    -------
    ComparisonReport
    """
    if isinstance(new_data, (str, Path)):
        new_data = read_table(new_data)
    if not isinstance(new_data, pd.DataFrame):
        raise TypeError(
            f"new_data must be a DataFrame or a path to a data file, got {type(new_data).__name__}"
        )
    reference_df, expected_names = _coerce_reference(reference)

    notes = []
    new_columns = [str(c) for c in new_data.columns]

    if reference_df is not None:
        # ---------------------------------------------- full comparison
        if _headerless(reference_df) or _headerless(new_data):
            side = "reference" if _headerless(reference_df) else "new data"
            if _headerless(reference_df) and _headerless(new_data):
                side = "reference and new data"
            notes.append(
                f"the {side} has no column headers (columns are numbered); "
                "matching used contents only"
            )
            name_weight = 0.0
        reference_df, ref_notes = _data_notes(reference_df, "reference")
        new_data, new_notes = _data_notes(new_data, "new data")
        notes += ref_notes + new_notes
        new_columns = [str(c) for c in new_data.columns]

        matches, scores = _match_with_scores(
            reference_df,
            new_data,
            match_threshold=match_threshold,
            name_weight=name_weight,
            sample_size=sample_size,
            random_state=random_state,
            assignment="optimal",
            exact_first=exact_first,
        )
        suspects, suspect_ref_names, suspect_new_names = _find_suspects(
            reference_df,
            new_data,
            matches,
            scores,
            verified_threshold,
            sample_size,
            random_state,
        )
        reference_columns = [str(c) for c in reference_df.columns]
        row_counts = (len(reference_df), len(new_data))
        name_only = False
    else:
        # ------------------------------------------ name-only comparison
        notes.append("reference given as column names only; contents were not checked")
        new_data, new_notes = _data_notes(new_data, "new data")
        notes += new_notes
        new_columns = [str(c) for c in new_data.columns]
        matches, scores = _match_names_only(expected_names, new_columns, match_threshold)
        suspects, suspect_ref_names, suspect_new_names = [], set(), set()
        reference_columns = expected_names
        row_counts = (None, len(new_data))
        name_only = True

    verified = [m for m in matches if _same_name(m) and m.score >= verified_threshold]
    renamed = [m for m in matches if not _same_name(m)]
    matched_sources = {str(m.source) for m in matches}
    matched_targets = {str(m.target) for m in matches}
    # A column already accounted for as suspect is not also "missing" -
    # dropped/added are for columns with no explanation at all.
    dropped = [
        c for c in reference_columns if c not in matched_sources and c not in suspect_ref_names
    ]
    added = [c for c in new_columns if c not in matched_targets and c not in suspect_new_names]
    mapping = {str(m.target): str(m.source) for m in matches}

    suggestions = []
    for column in dropped:
        rows = scores[scores["source"].astype(str) == column]
        if rows.empty:
            continue
        best = rows.sort_values("score", ascending=False).iloc[0]
        suggestions.append(
            Candidate(column=column, candidate=str(best["target"]), score=float(best["score"]))
        )
    suggestions.sort(key=lambda c: c.score, reverse=True)

    return ComparisonReport(
        verified=verified,
        renamed=renamed,
        suspect=suspects,
        dropped=dropped,
        added=added,
        suggestions=suggestions,
        matches=matches,
        mapping=mapping,
        scores=scores,
        notes=notes,
        reference_columns=reference_columns,
        new_columns=new_columns,
        row_counts=row_counts,
        match_threshold=match_threshold,
        verified_threshold=verified_threshold,
        name_only=name_only,
    )


def generate_column_rename(data1, data2, *, match_threshold: float = 0.5, **kwargs) -> str:
    """Generate a reviewable rename_dict for ``data2``'s columns.

    Convenience for ``compare(data1, data2).rename_snippet()``: only
    actual renames go in the dict, same-name matches are noted in a
    leading comment, and entries follow ``data2``'s own column order so
    the snippet reads alongside the file it renames.
    """
    return compare(data1, data2, match_threshold=match_threshold, **kwargs).rename_snippet()


def align_to_model(
    model,
    data: pd.DataFrame,
    *,
    match_threshold: float = 0.5,
    auto_apply: bool = True,
) -> ComparisonReport | pd.DataFrame:
    """Align ``data``'s columns to a fitted sklearn model's expected input.

    Thin wrapper around :func:`compare` using the model's
    ``feature_names_in_`` as the expected schema. Defaults to
    ``auto_apply=True`` (returns a ready-to-predict DataFrame, raising
    if any expected column has no match) since this is normally the
    last step before calling ``model.predict()``. Pass
    ``auto_apply=False`` to get the :class:`ComparisonReport` and
    review first.
    """
    expected = getattr(model, "feature_names_in_", None)
    if expected is None:
        raise AttributeError(
            "model has no feature_names_in_; call compare(expected_columns, data) "
            "with your own list of expected names instead"
        )
    expected = [str(c) for c in expected]
    report = compare(expected, data, match_threshold=match_threshold)
    if not auto_apply:
        return report
    if report.dropped:
        raise ValueError(
            f"Could not match expected column(s): {report.dropped}. "
            f"Unmatched columns in the data: {report.added}. "
            "Lower match_threshold, fix the source data, or pass auto_apply=False "
            "to review the ComparisonReport yourself."
        )
    return report.apply(data)[expected]
