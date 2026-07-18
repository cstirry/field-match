# How matching works

`compare()` builds the crosswalk in three stages. Each stage is public, so custom logic can use the pieces directly.

## Stage 1: exact names first

Columns named identically on both sides (ignoring case), same type, contents that agree: paired immediately, skipping the expensive comparison. Controlled by `exact_first` (default `True`).

Same-named pairs whose contents disagree are not forced together; they fall through to the full comparison. This is how reused names like SVI's `ST`/`STATE` swap get caught.

## Stage 2: scoring every pair

Every remaining reference column scored against every remaining new column, on two signals:

**Names**: word-aware fuzzy matching. Names split into words (`snake_case`, `camelCase`, spaces), matched allowing exact matches, abbreviations (`qty` inside `quantity`), and near-typos. `CustomerID`, `customer_id`, and `id_customer` all agree.

**Contents**, by inferred type:

| Type of column | How it is compared |
|---|---|
| numbers | distribution similarity (Kolmogorov-Smirnov, raw and median-centered, so shifted ranges like next year's ID sequence still match) |
| dates | same test, on the dates; text dates recognized automatically |
| yes/no | share of "yes" values; yes/no and 0/1 text recognized automatically |
| text and categories | value-set overlap, plus character-level overlap for formatting drift |

Columns compared by inferred type family, not exact dtype: `int64` matches `float64`; numeric, date, or boolean values stored as text are coerced first.

Signals blend into one 0-1 score via `name_weight`. Full table: `report.scores`, or standalone via `similarity_scores(df1, df2)`.

## Stage 3: assignment

`compare()` uses optimal one-to-one assignment (Hungarian algorithm, via `scipy` from the `[optimal]` extra): no two columns claim the same match, globally best rather than greedy.

`match_fields()` exposes the strategy directly:

- `"optimal"` (default): falls back to greedy with a warning if scipy is missing.
- `"greedy"`: no extra dependency.
- `"all"`: every candidate above `match_threshold`, unresolved, for manual review.

## The five similarity functions

`name_similarity`, `numeric_similarity`, `datetime_similarity`, `boolean_similarity`, `text_similarity`. Each takes two Series, returns a score in [0, 1]. See the [API reference](api.md).

## Limitations

Content matching keys on the *shape* of values, not their meaning: two unrelated columns with similar distributions can score high on content alone. One-to-one assignment and `name_weight` keep this in check in practice. A match resting on content while scoring near 0 on name is the kind to eyeball: that is what `renamed`, `suspect`, and `report.candidates(column)` are for. Review before `apply()`.
