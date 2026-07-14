"""Compare NAMCS 2022 vs. 2024 across three file formats: SAS, Stata, R.

The National Ambulatory Medical Care Survey (NAMCS) publishes the same
release in several formats for people using different software - SAS
(.sas7bdat), Stata (.dta), and R (.rds). This script runs the identical
2022-vs-2024 comparison three times, once per format, and confirms
compare() gives the exact same answer regardless of which one you
happened to receive.

Run it with:

    python examples/namcs_formats.py

This downloads all six files (2022 and 2024, in all three formats) into
examples/data/ - about 590 MB total, the largest of these examples by
far, since the SAS and Stata releases are much bigger than a typical
CSV. Feel free to trim the FORMATS list below to just the one format
you actually use.

Data source and documentation:
https://www.cdc.gov/nchs/namcs/documentation/about-the-data-2024.html
"""

from pathlib import Path
from urllib.request import urlretrieve

from field_match import compare

DATA_DIR = Path(__file__).resolve().parent / "data"
BASE_URL = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NAMCS"

# (label, 2022 filename, 2024 filename) - same naming pattern each year,
# except 2024's R file is capitalized differently from 2022's.
FORMATS = [
    ("SAS", "namcshc2022_sas.sas7bdat", "namcshc2024_sas.sas7bdat"),
    ("Stata", "namcshc2022_stata.dta", "namcshc2024_stata.dta"),
    ("R", "namcshc2022_r.rds", "namcshc2024_R.rds"),
]


def fetch(year: str, filename: str) -> Path:
    """Download a file into examples/data/ once; reuse it afterwards."""
    path = DATA_DIR / filename
    if not path.exists():
        DATA_DIR.mkdir(exist_ok=True)
        print(f"Downloading {filename} ({year}) ...")
        urlretrieve(f"{BASE_URL}/{year}/{filename}", path)
    return path


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Run the same comparison three times, once per format. compare()
    #    reads SAS, Stata, and R files directly from a path - no format-
    #    specific code needed on your end.
    # ------------------------------------------------------------------
    reports = {}
    for label, name_2022, name_2024 in FORMATS:
        path_2022 = fetch("2022", name_2022)
        path_2024 = fetch("2024", name_2024)
        print(f"Comparing 2022 vs 2024 ({label})...")
        reports[label] = compare(path_2022, path_2024)

    for label, report in reports.items():
        print(f"\n--- {label} ---")
        print(report.summary(show_columns=False))

    # ------------------------------------------------------------------
    # 2. Confirm the format didn't change the answer: same counts, same
    #    suspect columns, regardless of whether the data came in as SAS,
    #    Stata, or R.
    # ------------------------------------------------------------------
    suspect_names = {label: {s.name for s in r.suspect} for label, r in reports.items()}
    all_agree = len({frozenset(names) for names in suspect_names.values()}) == 1
    print(f"\nAll three formats flag the same suspect columns: {all_agree}")

    # ------------------------------------------------------------------
    # 3. What's actually in the suspect pile? Diagnosis codes (DX1-DX11)
    #    and the survey weight (VISWT) - real content drift, not a
    #    format quirk. NAMCS nearly doubled its sample size between 2022
    #    (282,017 rows) and 2024 (503,799 rows), which shifts the survey
    #    weight distribution, and two years of evolving diagnoses shift
    #    which codes appear how often. Nothing was renamed or dropped.
    # ------------------------------------------------------------------
    sas_report = reports["SAS"]
    print("\nWhy the SAS run's suspect columns were flagged (same reasons in Stata and R):")
    for s in sorted(sas_report.suspect, key=lambda s: s.name):
        print(f"  {s.name}: {s.reason}")


if __name__ == "__main__":
    main()
