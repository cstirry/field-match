# Tuning

All tuning parameters are optional and keyword-only (pass them by name). The defaults are sensible for typical release-to-release comparisons; reach for these when the data is unusual.

| Parameter | Range | Default | Meaning |
|---|---|---|---|
| `match_threshold` | 0-1 | 0.5 | minimum score to propose a match; higher = fewer, more confident matches |
| `verified_threshold` | 0-1 | 0.75 | minimum score for a same-name match to count as verified instead of suspect |
| `name_weight` | 0-1 | 0.4 | 0 = judge only by values (automatic for headerless files), 1 = judge only by names |
| `sample_size` | rows | 2000 | files longer than this are sampled before content comparison |
| `exact_first` | bool | True | pair identically named, same-type columns immediately, skipping the expensive comparison |

## match_threshold: how sure before proposing a match

Every candidate pair gets a score from 0 (nothing alike) to 1 (identical). Pairs below `match_threshold` are never proposed.

- **Raise it** when you would rather miss a real match than review a wrong one. Unmatched columns turn up as dropped/added instead.
- **Lower it** when the datasets are far apart and real matches score low. The [IMLS example](examples.md) spans thirty years of drift: at the default 0.5 several true renames are missed, at 0.4 they appear, along with one wrong suggestion that review catches. That tradeoff is the knob's whole purpose.

## verified_threshold: how sure before you can stop looking

A same-name match needs a score of at least `verified_threshold` to land in the verified pile; below it, the pair is listed as suspect. This is the bar for "safe to ignore", so it is deliberately stricter than the bar for "worth proposing". Raise it for a more cautious report; a column whose contents shifted between releases then gets flagged for a look instead of waved through.

## name_weight: names versus values

The final score blends name similarity and content similarity:

```
score = name_weight * name_similarity + (1 - name_weight) * content_similarity
```

- **Toward 0**: trust the values. Use when headers are junk (`Q1`, `var001`) or missing. Headerless files are detected automatically and matched on contents alone.
- **Toward 1**: trust the names. Use when contents are unreliable, e.g. mostly-empty columns.
- The default 0.4 lets content carry a match when names give nothing: in the [CDC PLACES example](examples.md), `cityname` became `locationname`, which scores 0 on name similarity, and the values carry the match entirely.

## sample_size and exact_first: speed

Content comparison samples long files at `sample_size` rows (deterministically, so scores are reproducible). And `exact_first` locks in identically named, same-type columns before the all-pairs comparison, which both speeds things up on mostly-shared schemas and prevents a same-named column from being claimed by a fuzzy lookalike. Set `exact_first=False` to force the full comparison for every column.
