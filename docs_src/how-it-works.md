# How matching works

`compare()` runs in three stages. Each stage is public, so anyone building custom logic can use the pieces directly.

## Stage 1: exact names first

Columns named identically on both sides (ignoring case), holding the same type of data, with contents that agree, pair up immediately and skip the expensive part. This is both a speed win on mostly-shared schemas and a correctness guard: a column cannot be stolen from its namesake by a fuzzy lookalike. Controlled by `exact_first` (default True).

Note what this does *not* do: a same-named pair whose contents disagree is not forced together. It falls through to the full comparison, which is how reused names like SVI's `ST`/`STATE` swap get caught.

## Stage 2: scoring every pair

Every remaining reference column is scored against every remaining new column, on two signals:

**Names.** Word-aware fuzzy matching: names are split into words (handling `snake_case`, `camelCase`, and spaces), then paired allowing exact matches, abbreviations (`qty` inside `quantity`), and near-typos. `CustomerID`, `customer_id`, and `id_customer` all agree. Unrelated words sharing incidental letters score zero.

**Contents.** Compared in a way that suits the inferred type:

| Type of column | How it is compared |
|---|---|
| numbers | do the two columns hold a similar spread of values? (Kolmogorov-Smirnov distance, raw and median-centered, so shifted ranges like next year's ID sequence still match) |
| dates | the same test, on the dates; dates stored as text are recognized automatically |
| yes/no | is the share of "yes" values similar? (yes/no and 0/1 text recognized automatically) |
| text and categories | how much do the value sets overlap, plus character-level overlap for formatting drift |

Columns are compared by inferred type family, not exact dtype: `int64` matches `float64`, and numeric, date, or boolean values stored as text are coerced before comparison.

The two signals blend into one 0-1 score via `name_weight`. The full table is available as `report.scores`, or standalone via `similarity_scores(df1, df2)`, which is also handy for one-off questions like hunting near-duplicate columns within a single file (`similarity_scores(df, df)`).

## Stage 3: assignment

Scores say how well each pair fits; assignment decides who gets whom when columns compete. `compare()` uses optimal one-to-one assignment (the Hungarian algorithm, via `scipy` from the `[optimal]` extra), so no two columns claim the same match and the pairing is globally best rather than greedy.

The lower-level `match_fields()` exposes the strategy as a parameter: `"optimal"` (default; falls back to greedy with a warning if scipy is missing), `"greedy"` (no extra dependency), or `"all"` (no picking at all; every candidate above `match_threshold` is returned for manual review, which a one-answer-per-column report cannot represent).

## The five similarity functions

All importable for custom logic; each takes two Series and returns a score in [0, 1]: `name_similarity`, `numeric_similarity`, `datetime_similarity`, `boolean_similarity`, `text_similarity`. See the [API reference](api.md).

## Limitations

Content matching keys on the *shape* of a column's values, not their meaning. Numeric and datetime columns are compared by distribution, so two unrelated columns with similar distributions, say any two roughly-normal columns on comparable scales, can score high on content alone. One-to-one assignment and `name_weight` keep this in check in practice, but a match that rests on contents while scoring near 0 on the name is exactly the kind to eyeball. That is what the `renamed` and `suspect` piles, and `report.candidates(column)`, are for: review before you `apply()`.
