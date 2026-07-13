import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def annual_release():
    """Simulate the target use case: last year's cleaned file vs this
    year's release with renamed columns and dtype drift."""
    rng = np.random.default_rng(42)
    n = 400
    last_year = pd.DataFrame(
        {
            "respondent_id": np.arange(1, n + 1),
            "age": rng.integers(18, 90, n),
            "household_income": rng.normal(58000, 21000, n).round(2),
            "state": rng.choice(["VA", "MD", "DC", "WV", "PA"], n),
            "survey_date": pd.to_datetime("2021-01-01")
            + pd.to_timedelta(rng.integers(0, 364, n), unit="D"),
            "is_employed": rng.random(n) > 0.35,
        }
    )
    this_year = pd.DataFrame(
        {
            "ID": np.arange(5001, 5001 + n),
            "Age of Respondent": rng.integers(18, 90, n),
            "HH_INCOME": rng.normal(60000, 22000, n).round(2),
            "st": rng.choice(["VA", "MD", "DC", "WV", "PA"], n),
            # dtype drift: dates released as strings this year
            "date_of_survey": (
                pd.to_datetime("2022-01-01") + pd.to_timedelta(rng.integers(0, 364, n), unit="D")
            ).strftime("%Y-%m-%d"),
            "employed": rng.random(n) > 0.4,
        }
    )
    return last_year, this_year
