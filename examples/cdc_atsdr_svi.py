"""Crosswalk two releases of the CDC/ATSDR Social Vulnerability Index (SVI), 2010 vs. 2022.

Run it with:

    python examples/cdc_atsdr_svi.py

The two CSVs are downloaded once into examples/data/

Data source and documentation:
https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html
"""

from pathlib import Path
from urllib.request import urlretrieve

from field_match import compare

DATA_DIR = Path(__file__).resolve().parent / "data"

FILES = {
    "SVI_2010_US_county.csv": "https://svi.cdc.gov/Documents/Data/2010/csv/states_counties/SVI_2010_US_county.csv",
    "SVI_2022_US_county.csv": "https://svi.cdc.gov/Documents/Data/2022/csv/states_counties/SVI_2022_US_county.csv",
}


def fetch(filename: str) -> Path:
    """Download a file into examples/data/ once; reuse it afterwards."""
    path = DATA_DIR / filename
    if not path.exists():
        DATA_DIR.mkdir(exist_ok=True)
        print(f"Downloading {filename} ...")
        urlretrieve(FILES[filename], path)
    return path


def main() -> None:
    svi_2010 = fetch("SVI_2010_US_county.csv")
    svi_2022 = fetch("SVI_2022_US_county.csv")

    # ------------------------------------------------------------------
    # 1. Compare the 2022 release against 2010. compare() accepts file
    #    paths directly, and print(report) shows what happened.
    # ------------------------------------------------------------------
    print("Comparing (about 15 seconds)...\n")
    report = compare(svi_2010, svi_2022)
    print(report)

    # ------------------------------------------------------------------
    # 2. Read the suspect reasons. This is where reused names surface:
    #    in 2010 ST held text state abbreviations and STATE held numeric
    #    codes; by 2022 the numeric code is called ST. The contents give
    #    it away, so field-match refuses to pair them by name alone.
    # ------------------------------------------------------------------
    print("\nWhy each suspect column was flagged:")
    for s in report.suspect:
        print(f"  {s.name}: {s.reason}")

    # ------------------------------------------------------------------
    # 3. Not sure about one column? Drill into its ranked candidates.
    # ------------------------------------------------------------------
    print("\nEvery candidate considered for 2010's E_POV (top 5):")
    print(report.candidates("E_POV").to_string(index=False))

    # ------------------------------------------------------------------
    # 4. Happy with the mapping? Either apply it directly:
    #
    #        aligned_2022 = report.apply(pd.read_csv(svi_2022))
    #
    #    or write a rename snippet to paste into your own cleaning
    #    script and hand-check line by line, which is what we do here.
    # ------------------------------------------------------------------
    out_path = DATA_DIR / "svi_2010_to_2022_rename.py"
    out_path.write_text(report.rename_snippet() + "\n")
    print(f"\nWrote a reviewable rename snippet to {out_path}")


if __name__ == "__main__":
    main()
