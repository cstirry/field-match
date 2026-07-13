"""Crosswalk CDC's 500 Cities data to its successor, PLACES, 2019 vs, 2020.

Run it with:

    python examples/cdc_place.py

The two CSVs are downloaded once into examples/data/

Data source and documentation:
https://data.cdc.gov/browse?category=500+Cities+%26+Places
"""

from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlretrieve

import pandas as pd

from field_match import compare

DATA_DIR = Path(__file__).resolve().parent / "data"

# Socrata dataset ids on data.cdc.gov
ID_500_CITIES_2019 = "6vp6-wxuq"  # 500 Cities: Local Data for Better Health, 2019 release
ID_PLACES_2020 = "q8xq-ygsk"  # PLACES: Local Data for Better Health, Place Data 2020 release

STATE = "MD"


def fetch(filename: str, dataset_id: str, where: str) -> Path:
    """Download a filtered slice of a data.cdc.gov dataset, once."""
    path = DATA_DIR / filename
    if not path.exists():
        DATA_DIR.mkdir(exist_ok=True)
        query = urlencode({"$where": where, "$limit": 50000})
        url = f"https://data.cdc.gov/resource/{dataset_id}.csv?{query}"
        print(f"Downloading {filename} ...")
        urlretrieve(url, path)
    return path


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Download comparable slices. First one state's city-level rows
    #    from the last 500 Cities release...
    # ------------------------------------------------------------------
    cities_2019 = pd.read_csv(
        fetch(
            f"500cities_2019_{STATE}.csv",
            ID_500_CITIES_2019,
            f"stateabbr='{STATE}' AND geographiclevel='City'",
        ),
        low_memory=False,
    )

    # ...then exactly those same places from the first PLACES release,
    # using the 2019 file's own FIPS codes as the filter.
    fips = sorted(cities_2019["cityfips"].dropna().astype(int).unique())
    print(f"2019 file covers {len(fips)} {STATE} cities; requesting the same from PLACES 2020\n")
    places_2020 = pd.read_csv(
        fetch(
            f"places_2020_{STATE}.csv",
            ID_PLACES_2020,
            "locationid in(" + ",".join(f"'{f}'" for f in fips) + ")",
        ),
        low_memory=False,
    )

    print(f"500 Cities 2019: {cities_2019.shape[0]} rows, {cities_2019.shape[1]} columns")
    print(f"PLACES 2020:     {places_2020.shape[0]} rows, {places_2020.shape[1]} columns\n")

    # ------------------------------------------------------------------
    # 2. Compare and review.
    # ------------------------------------------------------------------
    report = compare(cities_2019, places_2020)
    print(report.summary())

    # ------------------------------------------------------------------
    # 3. Why content matching matters here: the renamed columns score
    #    ZERO on name similarity ("cityname" vs "locationname" has no
    #    usable word boundary), so the values carried the whole match.
    # ------------------------------------------------------------------
    print("\nCandidates for the renamed columns (note name_score = 0):")
    print(report.candidates("cityname", limit=2).to_string(index=False))
    print(report.candidates("cityfips", limit=2).to_string(index=False))

    # ------------------------------------------------------------------
    # 4. Apply the reviewed mapping: the 2020 file now uses 2019's
    #    column names and can drop straight into an existing pipeline.
    # ------------------------------------------------------------------
    aligned = report.apply(places_2020)
    kept = [c for c in cities_2019.columns if c in aligned.columns]
    print(f"\nAfter report.apply(): {len(kept)} columns line up with the 2019 schema.")


if __name__ == "__main__":
    main()
