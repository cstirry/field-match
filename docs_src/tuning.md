# Tuning

All tuning parameters are optional and keyword-only.

| Parameter | Range | Default | Meaning |
|---|---|---|---|
| `match_threshold` | 0-1 | 0.5 | minimum score to propose a match; higher = fewer, more confident matches |
| `verified_threshold` | 0-1 | 0.75 | minimum score for a same-name match to count as verified instead of suspect |
| `name_weight` | 0-1 | 0.4 | 0 = judge only by values (automatic for headerless files), 1 = judge only by names |
| `sample_size` | rows | 2000 | files longer than this are sampled before content comparison |
| `exact_first` | bool | True | pair identically named, same-type columns immediately, skipping the expensive comparison |

## match_threshold

Candidate pairs score 0 (nothing alike) to 1 (identical). Pairs below `match_threshold` are never proposed.

- **Raise**: miss a real match rather than review a wrong one. Unmatched columns turn up as dropped/added.
- **Lower**: datasets far apart, real matches score low. [IMLS example](examples.md): at the default 0.5, several true renames are missed; at 0.4, they appear, along with one wrong suggestion that review catches.

## verified_threshold

A same-name match needs a score of at least `verified_threshold` to land in `verified`; below it, `suspect`. Stricter than the bar for proposing a match. Raise it for a more cautious report.

## name_weight

```
score = name_weight * name_similarity + (1 - name_weight) * content_similarity
```

- **Toward 0**: trust the values. Use when headers are junk (`Q1`, `var001`) or missing; headerless files are matched on contents alone automatically.
- **Toward 1**: trust the names. Use when contents are unreliable, e.g. mostly-empty columns.
- **Default 0.4**: content carries a match when names give nothing. [CDC PLACES example](examples.md): `cityname` to `locationname` scores 0 on name similarity; the values carry the match.

## sample_size and exact_first

- `sample_size`: content comparison samples long files at this many rows, deterministically (reproducible scores).
- `exact_first`: locks in identically named, same-type columns before the all-pairs comparison. Speeds up mostly-shared schemas and prevents a same-named column from being claimed by a fuzzy lookalike. Set `exact_first=False` to force the full comparison for every column.
