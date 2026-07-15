# Examples with real data

Each script in [examples/](https://github.com/cstirry/field-match/tree/main/examples) downloads a real government data release and crosswalks it. Together they cover the situations field-match is built for, and each one teaches a different lesson.

```bash
pip install "field-match[optimal]"
python examples/cdc_atsdr_svi.py
python examples/cdc_places.py
python examples/imls_pls.py
python examples/namcs_formats.py
```

Each script saves its files in `examples/data/` the first time it runs, so you can also drag the same pair into the [web app](web-app.md) to see the comparison visually.

## SVI: the reused-name trap

[`cdc_atsdr_svi.py`](https://github.com/cstirry/field-match/blob/main/examples/cdc_atsdr_svi.py) compares the CDC/ATSDR Social Vulnerability Index, 2010 vs. 2022 county files. Most of the 103 columns were renamed between releases, and two were reused with different meanings: in 2010, `ST` held text state abbreviations and `STATE` held numeric codes; by 2022 the numeric code is called `ST`. A name-based merge would silently corrupt the state field. The content check catches it and reports both columns as suspect, with the true counterparts (`ST` to `ST_ABBR`, `STATE` to `ST`) found instead.

## CDC PLACES: content carries the match

[`cdc_places.py`](https://github.com/cstirry/field-match/blob/main/examples/cdc_places.py) covers the 500 Cities project becoming PLACES in 2020. The renamed columns are flattened lowercase words, so `cityname` vs. `locationname` scores exactly 0 on name similarity, and the values carry the whole match: `cityname` to `locationname`, `cityfips` to `locationid`, `populationcount` to `totalpopulation`. The script also demonstrates a useful API technique: using the reference file's own FIPS codes to request the comparable slice from the new data source, so the contents genuinely overlap.

## IMLS PLS: the threshold tradeoff

[`imls_pls.py`](https://github.com/cstirry/field-match/blob/main/examples/imls_pls.py) spans thirty years of the Public Libraries Survey, 1992 vs. 2022. That much drift thins the content overlap, so several true renames (`LIB_NAME` to `LIBNAME`, `LIB_ADDR` to `ADDRESS`) score just under the default `match_threshold`. Lowering it to 0.4 recovers them, along with one wrong suggestion that review catches: the threshold tradeoff in miniature.

## NAMCS: three formats, one answer

[`namcs_formats.py`](https://github.com/cstirry/field-match/blob/main/examples/namcs_formats.py) compares the National Ambulatory Medical Care Survey, 2022 vs. 2024, three times: once each from the SAS, Stata, and R releases NCHS publishes. All three give byte-for-byte identical results: 63 verified, 12 suspect (the `DX1`-`DX11` diagnosis codes and the `VISWT` survey weight, both genuinely drifted as the sample nearly doubled), 0 renamed, dropped, or added. The format the data arrived in does not change the answer.

Fair warning: this one downloads all six files, about 590 MB total, since the SAS and Stata releases are much larger than a typical CSV. The script's `FORMATS` list is easy to trim to just the format you use.
