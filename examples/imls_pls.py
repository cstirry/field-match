"""Crosswalk two releases of the IMLS Public Libraries Survey (PLS), 1992 vs. 2022.

Run it with:

    python examples/imls_pls.py

The two zips/CSVs are downloaded once into examples/data/

Data source and documentation:
https://www.imls.gov/research-evaluation/surveys/public-libraries-survey-pls
"""

import re
import zipfile
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pandas as pd

from field_match import match_fields

DATA_DIR = Path(__file__).resolve().parent / "data"
SURVEY_PAGE = "https://www.imls.gov/research-evaluation/surveys/public-libraries-survey-pls"


def find_zip_links() -> dict[str, str]:
    """Scrape the PLS survey page for the CSV zip download links."""
    request = Request(SURVEY_PAGE, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request) as response:
        html = response.read().decode("utf-8", errors="replace")
    return {
        href.rsplit("/", 1)[-1]: urljoin(SURVEY_PAGE, href)
        for href in re.findall(r'href="([^"]*_csv\.zip)"', html)
    }


def fetch_outlet_csv(zip_name: str, links: dict[str, str]) -> Path:
    """Download one year's zip (once) and extract its outlet CSV.

    Each PLS zip holds several CSVs; the outlet file (one row per
    library building or bookmobile) is the one with "out" in its name,
    the same rule an ingestion pipeline would use.
    """
    zip_path = DATA_DIR / zip_name
    if not zip_path.exists():
        DATA_DIR.mkdir(exist_ok=True)
        print(f"Downloading {zip_name} ...")
        request = Request(links[zip_name], headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request) as response:
            zip_path.write_bytes(response.read())
    with zipfile.ZipFile(zip_path) as archive:
        member = next(
            name
            for name in archive.namelist()
            if "out" in name.lower() and name.lower().endswith(".csv")
        )
        out_path = DATA_DIR / Path(member).name
        out_path.write_bytes(archive.read(member))
    return out_path


def show(matches, label):
    print(f"{label}:")
    for m in matches:
        if str(m.source).lower() != str(m.target).lower():
            print(f"  {m.source:>12} -> {m.target:<10} score={m.score:.2f} ({m.family})")
    print()


def main() -> None:
    links = find_zip_links()
    fy1992 = next(name for name in links if "92" in name)
    fy2022 = next(name for name in links if "2022" in name)

    outlets_1992 = pd.read_csv(fetch_outlet_csv(fy1992, links), encoding="latin-1", low_memory=False)
    outlets_2022 = pd.read_csv(fetch_outlet_csv(fy2022, links), encoding="latin-1", low_memory=False)
    print(f"FY1992 outlets: {outlets_1992.shape[0]} rows, {outlets_1992.shape[1]} columns")
    print(f"FY2022 outlets: {outlets_2022.shape[0]} rows, {outlets_2022.shape[1]} columns\n")

    # ------------------------------------------------------------------
    # 1. At the default threshold, the confident renames come through.
    # ------------------------------------------------------------------
    confident = match_fields(outlets_1992, outlets_2022, match_threshold=0.5)
    show(confident, "Renames found at threshold 0.5")

    # ------------------------------------------------------------------
    # 2. Thirty years of drift leaves some true matches just under 0.5
    #    (library names and addresses changed a lot since 1992). Lower
    #    the threshold and they appear, along with one suggestion that
    #    is wrong (PUB_FIPS is not LOCALE) - which is exactly why the
    #    lower you set the threshold, the more carefully you review.
    # ------------------------------------------------------------------
    permissive = match_fields(outlets_1992, outlets_2022, match_threshold=0.4)
    already = {(m.source, m.target) for m in confident}
    extra = [m for m in permissive if (m.source, m.target) not in already]
    show(extra, "Additional matches when threshold drops to 0.4")

    unmatched = sorted(
        set(map(str, outlets_1992.columns)) - {str(m.source) for m in permissive}
    )
    print(f"1992 columns with no counterpart even at 0.4: {unmatched}")
    print("(LIB_CODE really did become LIBID, but its values changed too much")
    print("for content to confirm it; a codebook check settles ones like this.)")


if __name__ == "__main__":
    main()
