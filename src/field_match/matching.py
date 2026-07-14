"""Matching machinery: score column pairs and pick the best matching.

Most users want :func:`field_match.compare`, which wraps this module and
returns a reviewable report. The pieces here are public for anyone who
needs raw scores (:func:`similarity_scores`) or raw matches with control
over how competition is resolved (:func:`match_fields`).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .similarity import (
    boolean_similarity,
    datetime_similarity,
    name_similarity,
    numeric_similarity,
    text_similarity,
)

__all__ = [
    "FieldMatch",
    "similarity_scores",
    "match_fields",
]

_PARSE_THRESHOLD = 0.9  # fraction of values that must parse to coerce a column

_SCORE_COLUMNS = ["source", "target", "family", "name_score", "content_score", "score"]


@dataclass(frozen=True)
class FieldMatch:
    """A proposed match between one column in each DataFrame."""

    source: str  # column in data1 (the reference)
    target: str  # column in data2 (the new file)
    score: float  # combined score in [0, 1]
    name_score: float
    content_score: float
    family: str  # inferred type family used for comparison


def _infer_family(series: pd.Series) -> tuple[str, pd.Series]:
    """Infer the type *family* of a column, coercing object columns.

    Real-world CSVs often load numbers or dates as strings; this lets
    e.g. a string column ``["2021-01-02", ...]`` match a true datetime
    column. Returns the family name and the (possibly coerced) series.
    """
    if pd.api.types.is_bool_dtype(series):
        return "boolean", series
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime", series
    if pd.api.types.is_numeric_dtype(series):
        return "numeric", series

    # Object / string / categorical: try to coerce.
    non_null = series.dropna()
    if non_null.empty:
        return "text", series

    as_numeric = pd.to_numeric(non_null, errors="coerce")
    if as_numeric.notna().mean() >= _PARSE_THRESHOLD:
        return "numeric", as_numeric

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # pandas warns on unparseable formats
        as_datetime = pd.to_datetime(non_null, errors="coerce", format="mixed")
    if as_datetime.notna().mean() >= _PARSE_THRESHOLD:
        return "datetime", as_datetime

    unique_lower = set(non_null.astype(str).str.strip().str.lower().unique())
    if unique_lower <= {"true", "false", "t", "f", "yes", "no", "y", "n", "0", "1"}:
        truthy = {"true", "t", "yes", "y", "1"}
        return "boolean", non_null.astype(str).str.strip().str.lower().isin(truthy)

    return "text", series


_CONTENT_FUNCS = {
    "numeric": numeric_similarity,
    "datetime": datetime_similarity,
    "boolean": boolean_similarity,
    "text": text_similarity,
}


def similarity_scores(
    data1: pd.DataFrame,
    data2: pd.DataFrame,
    *,
    name_weight: float = 0.4,
    sample_size: int = 2000,
    random_state: int = 0,
) -> pd.DataFrame:
    """Score every comparable column pair between two DataFrames.

    This is the raw evidence table with no matching applied: one row per
    candidate pair, scored but not picked. Use it when you want scores
    without a full :func:`field_match.compare` run - checking one column
    against another dataset (``similarity_scores(df1[["age"]], df2)``),
    hunting near-duplicate columns within one file
    (``similarity_scores(df, df)``), or feeding custom logic. After a
    ``compare()`` call, the same table is available as ``report.scores``.

    Columns are compared when they belong to the same inferred type
    family (numeric, datetime, boolean, text). Object columns whose
    values overwhelmingly parse as numbers/dates/booleans are coerced
    first, so ``"2021-06-01"`` strings can match a datetime column.

    Parameters
    ----------
    data1:
        The reference DataFrame (e.g. last year's cleaned data).
    data2:
        The new DataFrame whose columns you want to identify.
    name_weight:
        Weight in ``[0, 1]`` given to column-*name* similarity; the
        remainder goes to column-*content* similarity. 0 judges only by
        the values, 1 only by the names.
    sample_size:
        Columns longer than this are sampled before content comparison.
    random_state:
        Seed for sampling, for reproducible scores.

    Returns
    -------
    pandas.DataFrame
        One row per compared pair with columns ``source``, ``target``,
        ``family``, ``name_score``, ``content_score``, ``score``,
        sorted by ``source`` then descending ``score``.
    """
    if not 0.0 <= name_weight <= 1.0:
        raise ValueError(f"name_weight must be in [0, 1], got {name_weight}")

    def _prepare(df: pd.DataFrame) -> dict[str, tuple[str, pd.Series]]:
        sampled = df.sample(sample_size, random_state=random_state) if len(df) > sample_size else df
        return {col: _infer_family(sampled[col]) for col in sampled.columns}

    prepared_1, prepared_2 = _prepare(data1), _prepare(data2)

    rows = []
    for col_1, (family_1, series_1) in prepared_1.items():
        for col_2, (family_2, series_2) in prepared_2.items():
            if family_1 != family_2:
                continue
            content = float(_CONTENT_FUNCS[family_1](series_1, series_2))
            content = min(max(content, 0.0), 1.0)
            name = name_similarity(col_1, col_2)
            rows.append(
                {
                    "source": col_1,
                    "target": col_2,
                    "family": family_1,
                    "name_score": round(name, 3),
                    "content_score": round(content, 3),
                    "score": round(name_weight * name + (1 - name_weight) * content, 3),
                }
            )

    scores = pd.DataFrame(rows, columns=_SCORE_COLUMNS)
    return scores.sort_values(["source", "score"], ascending=[True, False]).reset_index(drop=True)


_ASSIGNMENT_STRATEGIES = ("optimal", "greedy", "all")


def _resolve_assignment(matrix: pd.DataFrame, strategy: str) -> list[tuple[int, int]] | None:
    """Return (row_index, col_index) pairs into ``matrix`` per ``strategy``.

    - ``"optimal"``: Hungarian algorithm - globally maximizes total score,
      one-to-one. Falls back to ``"greedy"`` with a warning if scipy isn't
      installed.
    - ``"greedy"``: repeatedly take the single highest remaining score and
      remove its row and column - one-to-one but not globally optimal.
      Cheaper than optimal and needs no extra dependency.
    - ``"all"``: no picking at all - every (row, column) pair is a
      candidate; the caller filters by score/threshold themselves. Use
      this to see every plausible match rather than have the library
      choose one, e.g. when a column genuinely has several legitimate
      counterparts. Returns ``None`` as a signal to skip pair-based
      lookup and use the full matrix instead.
    """
    if strategy not in _ASSIGNMENT_STRATEGIES:
        raise ValueError(f"assignment must be one of {_ASSIGNMENT_STRATEGIES}, got {strategy!r}")

    if strategy == "all":
        return None

    values = matrix.to_numpy()

    if strategy == "optimal":
        try:
            from scipy.optimize import linear_sum_assignment

            row_idx, col_idx = linear_sum_assignment(values, maximize=True)
            return list(zip(row_idx, col_idx))
        except ImportError:
            warnings.warn(
                "assignment='optimal' requires scipy; install with "
                "`pip install 'field-match[optimal]'`. Falling back to assignment='greedy'.",
                stacklevel=3,
            )
            # fall through to greedy

    pairs = []
    working = values.copy()
    for _ in range(min(working.shape)):
        i, j = np.unravel_index(np.argmax(working), working.shape)
        if working[i, j] <= 0:
            break
        pairs.append((i, j))
        working[i, :] = -1.0
        working[:, j] = -1.0
    return pairs


def _presolve_exact(
    data1: pd.DataFrame,
    data2: pd.DataFrame,
    match_threshold: float,
    name_weight: float,
    sample_size: int,
    random_state: int,
) -> tuple[list[FieldMatch], pd.DataFrame, pd.DataFrame]:
    """Pair columns whose names match exactly, before the all-pairs comparison.

    A column whose name appears verbatim (ignoring case) in both frames
    and whose contents fall in the same type family is almost certainly
    the same field, so it is accepted directly - its content is compared
    against its namesake only, not against every other column. This
    keeps large same-schema files fast and stops a same-named column
    from being claimed by a fuzzy competitor.

    Names duplicated within a frame, cross-family namesakes, and pairs
    scoring below ``match_threshold`` are left in the frames for the
    full comparison. Returns the accepted matches and both frames with
    the accepted columns removed.
    """

    def _sample(df: pd.DataFrame) -> pd.DataFrame:
        return df.sample(sample_size, random_state=random_state) if len(df) > sample_size else df

    def _by_name(df: pd.DataFrame) -> dict[str, list]:
        names: dict[str, list] = {}
        for col in df.columns:
            names.setdefault(str(col).lower(), []).append(col)
        return names

    sampled_1, sampled_2 = _sample(data1), _sample(data2)
    names_1, names_2 = _by_name(data1), _by_name(data2)

    matches = []
    used_1, used_2 = [], []
    for key, cols_1 in names_1.items():
        cols_2 = names_2.get(key)
        if cols_2 is None or len(cols_1) != 1 or len(cols_2) != 1:
            continue
        col_1, col_2 = cols_1[0], cols_2[0]
        family_1, series_1 = _infer_family(sampled_1[col_1])
        family_2, series_2 = _infer_family(sampled_2[col_2])
        if family_1 != family_2:
            continue
        content = float(_CONTENT_FUNCS[family_1](series_1, series_2))
        content = min(max(content, 0.0), 1.0)
        score = name_weight * 1.0 + (1 - name_weight) * content
        if score < match_threshold:
            continue
        matches.append(
            FieldMatch(
                source=col_1,
                target=col_2,
                score=round(score, 3),
                name_score=1.0,
                content_score=round(content, 3),
                family=family_1,
            )
        )
        used_1.append(col_1)
        used_2.append(col_2)

    return matches, data1.drop(columns=used_1), data2.drop(columns=used_2)


def _match_with_scores(
    data1: pd.DataFrame,
    data2: pd.DataFrame,
    match_threshold: float,
    name_weight: float,
    sample_size: int,
    random_state: int,
    assignment: str,
    exact_first: bool,
) -> tuple[list[FieldMatch], pd.DataFrame]:
    """Run the full matching machine and keep the evidence.

    Returns the accepted matches and the complete scores table,
    including one row for each pair the exact-name presolve accepted,
    so drill-downs never come back empty for the best-matched columns.
    """
    if assignment not in _ASSIGNMENT_STRATEGIES:
        raise ValueError(f"assignment must be one of {_ASSIGNMENT_STRATEGIES}, got {assignment!r}")

    exact_matches: list[FieldMatch] = []
    if exact_first and assignment != "all":
        exact_matches, data1, data2 = _presolve_exact(
            data1, data2, match_threshold, name_weight, sample_size, random_state
        )

    scores = similarity_scores(
        data1, data2, name_weight=name_weight, sample_size=sample_size, random_state=random_state
    )

    full_scores = scores
    if exact_matches:
        exact_rows = pd.DataFrame(
            [
                {
                    "source": m.source,
                    "target": m.target,
                    "family": m.family,
                    "name_score": m.name_score,
                    "content_score": m.content_score,
                    "score": m.score,
                }
                for m in exact_matches
            ],
            columns=_SCORE_COLUMNS,
        )
        full_scores = (
            exact_rows if scores.empty else pd.concat([exact_rows, scores], ignore_index=True)
        )
        full_scores = full_scores.sort_values(
            ["source", "score"], ascending=[True, False]
        ).reset_index(drop=True)

    if scores.empty:
        matches = sorted(exact_matches, key=lambda m: m.score, reverse=True)
        return matches, full_scores

    if assignment == "all":
        # No picking - every pair that was actually compared (same type
        # family) and clears the threshold, no dedup in either direction.
        matches = [
            FieldMatch(
                source=r.source,
                target=r.target,
                score=float(r.score),
                name_score=float(r.name_score),
                content_score=float(r.content_score),
                family=str(r.family),
            )
            for r in scores.itertuples()
            if r.score >= match_threshold
        ]
        return sorted(matches, key=lambda m: m.score, reverse=True), full_scores

    matrix = scores.pivot_table(index="source", columns="target", values="score").fillna(0.0)
    sources, targets = list(matrix.index), list(matrix.columns)
    pairs = _resolve_assignment(matrix, assignment)

    lookup = scores.set_index(["source", "target"])
    matches = []
    for i, j in pairs:
        source, target = sources[i], targets[j]
        if (source, target) not in lookup.index:
            continue
        row = lookup.loc[(source, target)]
        if row["score"] >= match_threshold:
            matches.append(
                FieldMatch(
                    source=source,
                    target=target,
                    score=float(row["score"]),
                    name_score=float(row["name_score"]),
                    content_score=float(row["content_score"]),
                    family=str(row["family"]),
                )
            )
    matches = sorted(exact_matches + matches, key=lambda m: m.score, reverse=True)
    return matches, full_scores


def match_fields(
    data1: pd.DataFrame,
    data2: pd.DataFrame,
    *,
    match_threshold: float = 0.5,
    name_weight: float = 0.4,
    sample_size: int = 2000,
    random_state: int = 0,
    assignment: str = "optimal",
    exact_first: bool = True,
) -> list[FieldMatch]:
    """Find the best column matching between two DataFrames.

    The raw match list with no report around it - most users want
    :func:`field_match.compare` instead. This is the home of the
    ``assignment`` knob, including ``"all"``, which a report cannot
    represent (one column, many candidates).

    Parameters
    ----------
    match_threshold:
        Minimum combined score in ``[0, 1]`` to accept a match; higher
        means fewer, more confident matches.
    assignment:
        How to resolve competing matches - ``"optimal"`` (default, globally
        best one-to-one pairing via the Hungarian algorithm), ``"greedy"``
        (faster one-to-one approximation, no scipy required), or
        ``"all"`` (every candidate pair scoring at or above
        ``match_threshold``, no picking at all).
    exact_first:
        If True (default), columns whose names match exactly (ignoring
        case) and whose contents are the same type family are paired
        immediately and skip the all-pairs comparison. Much faster when
        the two files mostly share a schema. Ignored for
        ``assignment="all"``, which by definition reports every candidate
        pair. Set False to force the full comparison for every column.

    Returns matches with ``score >= match_threshold``, sorted by
    descending score.
    """
    matches, _ = _match_with_scores(
        data1,
        data2,
        match_threshold=match_threshold,
        name_weight=name_weight,
        sample_size=sample_size,
        random_state=random_state,
        assignment=assignment,
        exact_first=exact_first,
    )
    return matches
