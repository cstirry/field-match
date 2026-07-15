# Why field-match

Names, types, and values all shift between data releases, quietly breaking anything downstream that expects a stable schema. Anyone who works with recurring releases knows the ritual: a new file arrives, something downstream fails or silently produces wrong numbers, and you end up reading codebooks side by side to work out that `household_income` is now called `HH_INCOME` and that `ST` no longer means what it meant last year.

field-match replaces that ritual with one function call. It compares the new dataset against a reference on both column names *and* the values inside them, then sorts every column into verified, renamed, suspect, dropped, or added, with a similarity score behind each decision. You review a short report instead of digging through documentation.

## No rules to write

Validation frameworks make you author a schema first: every column, its type, its constraints, kept up to date by hand. field-match's starting point is different: **your last clean release is the expectation suite.** You declare nothing. The reference dataset already encodes what column names existed, what type each column was, and what its values looked like, so field-match checks all of that directly against the new release and, where something doesn't line up, proposes what happened instead of just failing.

That also defines the boundary honestly: field-match answers the schema question (which column is which, and did any change meaning). It does not check value-level rules like "no nulls" or "between 0 and 1". If you need those, a validation library is the right tool *after* the columns are aligned.

## How it relates to tools you may know

| Tool | The question it answers | The difference |
|---|---|---|
| Great Expectations, pandera | "Does incoming data conform to rules I wrote?" | They detect that something broke; field-match diagnoses what happened, with no rules to write or maintain. |
| datacompy, pandas `DataFrame.compare` | "Are these two tables equal, and which values differ?" | They need the column alignment as input. field-match produces that alignment. Use them after field-match if you also want a value-level diff. |
| splink, recordlinkage | "Is this row the same person or entity as that row?" | Record linkage matches rows. field-match matches columns. |
| Valentine | "Which schema-matching algorithm performs best?" | Valentine implements the academic algorithms for research benchmarking. field-match is the practitioner workflow: one call, a categorical report, review, apply. |

## Where it shines

Public interest datasets: annual government and institutional releases like the CDC's Social Vulnerability Index, PLACES, NAMCS, or the IMLS Public Libraries Survey. These are exactly the files where columns get renamed between years, codes change type, documentation lags, and a decade-long analysis depends on getting the crosswalk right. The [examples](examples.md) run field-match against four of them, real downloads included.
