"""Similarity measures for column names and column contents.

All functions return a float in ``[0.0, 1.0]`` where 1.0 means identical
and 0.0 means no similarity. Every function is defensive about empty or
all-NaN input and returns 0.0 in those cases.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

__all__ = [
    "name_similarity",
    "numeric_similarity",
    "datetime_similarity",
    "boolean_similarity",
    "text_similarity",
]

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SPLIT_RE = re.compile(r"[^a-z0-9]+")


def _tokenize_name(name: str) -> list[str]:
    """Split a column name into normalized tokens.

    Handles snake_case, kebab-case, camelCase, spaces and digits:
    ``"CustomerID"`` -> ``["customer", "id"]``.
    """
    name = _CAMEL_RE.sub(" ", str(name))
    return [t for t in _SPLIT_RE.split(name.lower()) if t]


def _is_subsequence(short: str, long: str) -> bool:
    """True if ``short``'s characters appear in ``long`` in order."""
    it = iter(long)
    return all(ch in it for ch in short)


def _token_pair_score(t1: str, t2: str) -> float:
    """Similarity between two individual name tokens."""
    if t1 == t2:
        return 1.0
    short, long = (t1, t2) if len(t1) <= len(t2) else (t2, t1)
    # Abbreviation: qty ⊂ quantity, hh ⊂ household. Require 2+ chars so
    # single letters don't match everything.
    if len(short) >= 2 and _is_subsequence(short, long):
        return 0.8
    # Typos: nearly identical spellings only.
    ratio = SequenceMatcher(None, t1, t2).ratio()
    return ratio if ratio >= 0.8 else 0.0


def name_similarity(name_1: str, name_2: str) -> float:
    """Fuzzy similarity between two column *names*.

    Tokenizes both names (snake_case, camelCase, spaces) and greedily
    pairs tokens. A token pair scores 1.0 for an exact match, 0.8 when
    one is an ordered-subsequence abbreviation of the other
    (``qty``/``quantity``, ``hh``/``household``), or its character ratio
    for near-typos. Unrelated words score 0 - incidental shared letters
    don't count.
    """
    s1, s2 = str(name_1), str(name_2)
    if not s1 or not s2:
        return 0.0
    if s1.lower() == s2.lower():
        return 1.0

    tokens_1, tokens_2 = _tokenize_name(s1), _tokenize_name(s2)
    if not tokens_1 or not tokens_2:
        return 0.0

    # Greedy one-to-one token pairing, best pairs first.
    candidates = sorted(
        (
            (_token_pair_score(t1, t2), i, j)
            for i, t1 in enumerate(tokens_1)
            for j, t2 in enumerate(tokens_2)
        ),
        reverse=True,
    )
    used_1: set[int] = set()
    used_2: set[int] = set()
    total = 0.0
    for score, i, j in candidates:
        if score <= 0.0:
            break
        if i in used_1 or j in used_2:
            continue
        used_1.add(i)
        used_2.add(j)
        total += score

    # Blend symmetric normalization with containment: "age" inside
    # "Age of Respondent" is a strong signal even though the longer
    # name has extra tokens.
    symmetric = total / max(len(tokens_1), len(tokens_2))
    containment = total / min(len(tokens_1), len(tokens_2))
    return 0.6 * symmetric + 0.4 * containment


def _ks_similarity(values_1: np.ndarray, values_2: np.ndarray) -> float:
    """``1 - KS statistic`` between two samples.

    The two-sample Kolmogorov-Smirnov statistic is the maximum distance
    between the empirical CDFs. It is bounded in [0, 1], compares whole
    distributions rather than summary statistics, and is well-defined
    for negative values and any scale.
    """
    if len(values_1) == 0 or len(values_2) == 0:
        return 0.0
    all_values = np.concatenate([values_1, values_2])
    all_values.sort(kind="mergesort")
    cdf_1 = np.searchsorted(np.sort(values_1), all_values, side="right") / len(values_1)
    cdf_2 = np.searchsorted(np.sort(values_2), all_values, side="right") / len(values_2)
    ks_stat = float(np.max(np.abs(cdf_1 - cdf_2)))
    return 1.0 - ks_stat


_SHIFT_DISCOUNT = 0.85  # centered-only agreement scores slightly below raw agreement


def _distribution_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Blend raw and shift-invariant distribution similarity.

    Annually released data often shifts in *location* while keeping its
    *shape* (next year's survey dates, sequential IDs continuing where
    last year's stopped). Raw KS similarity is 0 for such columns even
    though they clearly correspond. So we also compare the
    median-centered distributions, discounted so that raw alignment
    wins when both signals are present.
    """
    if len(v1) == 0 or len(v2) == 0:
        return 0.0
    raw = _ks_similarity(v1, v2)
    centered = _ks_similarity(v1 - np.median(v1), v2 - np.median(v2))
    return max(raw, _SHIFT_DISCOUNT * centered)


def numeric_similarity(series_1: pd.Series, series_2: pd.Series) -> float:
    """Similarity between two numeric columns.

    Compares the full empirical distributions via the two-sample
    Kolmogorov-Smirnov statistic, both raw and median-centered (see
    :func:`_distribution_similarity`). Unlike comparing means/ranges,
    this is robust to outliers, negative values, and location shifts
    between annual releases.
    """
    v1 = pd.to_numeric(series_1, errors="coerce").dropna().to_numpy(dtype=float)
    v2 = pd.to_numeric(series_2, errors="coerce").dropna().to_numpy(dtype=float)
    return _distribution_similarity(v1, v2)


def datetime_similarity(series_1: pd.Series, series_2: pd.Series) -> float:
    """Similarity between two datetime columns.

    KS distance on epoch values, both raw and median-centered - so this
    year's survey dates still match last year's ``survey_date`` column
    even though the two ranges never overlap.
    """
    v1 = pd.to_datetime(series_1, errors="coerce").dropna()
    v2 = pd.to_datetime(series_2, errors="coerce").dropna()
    if v1.empty or v2.empty:
        return 0.0
    return _distribution_similarity(
        v1.astype("int64").to_numpy(dtype=float),
        v2.astype("int64").to_numpy(dtype=float),
    )


def boolean_similarity(series_1: pd.Series, series_2: pd.Series) -> float:
    """Similarity between two boolean columns.

    Simply ``1 - |p1 - p2|`` where ``p`` is the proportion of True
    values. Always bounded in [0, 1].
    """
    s1, s2 = series_1.dropna(), series_2.dropna()
    if s1.empty or s2.empty:
        return 0.0
    return 1.0 - abs(float(s1.mean()) - float(s2.mean()))


def _char_ngrams(value: str, n: int = 3) -> set[str]:
    padded = f" {value.lower()} "
    if len(padded) < n:
        return {padded}
    return {padded[i : i + n] for i in range(len(padded) - n + 1)}


def text_similarity(
    series_1: pd.Series,
    series_2: pd.Series,
    sample_size: int = 500,
    random_state: int = 0,
) -> float:
    """Similarity between two text/categorical columns.

    Blends two signals:

    * exact-value Jaccard overlap of the unique values (strong signal for
      categorical codes, IDs, state names, ...), and
    * character 3-gram Jaccard of the pooled values (catches formatting
      drift, e.g. ``"VA"`` vs ``"Virginia"`` scores low here but free-text
      fields about the same topic score high).

    Long columns are sampled for performance.
    """
    s1 = series_1.dropna().astype(str)
    s2 = series_2.dropna().astype(str)
    if s1.empty or s2.empty:
        return 0.0

    unique_1, unique_2 = set(s1.unique()), set(s2.unique())
    value_jaccard = len(unique_1 & unique_2) / len(unique_1 | unique_2)

    if len(s1) > sample_size:
        s1 = s1.sample(sample_size, random_state=random_state)
    if len(s2) > sample_size:
        s2 = s2.sample(sample_size, random_state=random_state)

    ngrams_1: set[str] = set().union(*(_char_ngrams(v) for v in s1))
    ngrams_2: set[str] = set().union(*(_char_ngrams(v) for v in s2))
    ngram_jaccard = (
        len(ngrams_1 & ngrams_2) / len(ngrams_1 | ngrams_2) if ngrams_1 | ngrams_2 else 0.0
    )

    return max(value_jaccard, 0.7 * ngram_jaccard + 0.3 * value_jaccard)
