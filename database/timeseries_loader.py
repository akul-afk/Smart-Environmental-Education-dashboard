"""
Time-Series Loader — Reads World Bank CSV datasets and extracts all yearly
values per country per factor.  Result is cached in memory for fast access.

Returns:
    dict[str, dict[str, list[tuple[int, float]]]]
    {factor_key: {country_code: [(year, value), ...]}}
"""

import os
import pandas as pd
from app_logger import logger

# Reuse aggregate filter from dataset_loader
from database.dataset_loader import _AGGREGATE_CODES, _CSV_MAP, _VALIDATION

# ── Module-level cache ──
_ts_cache: dict | None = None


def load_timeseries(datasets_dir: str = None) -> dict:
    """Read all 4 CSVs and extract every valid (year, value) pair per country.

    Returns nested dict:  {factor_key: {country_code: [(year, value), ...]}}
    Country names stored separately:  {"_names": {country_code: country_name}}

    Cached after first call — subsequent calls return the same object.
    """
    global _ts_cache
    if _ts_cache is not None:
        return _ts_cache

    if datasets_dir is None:
        datasets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets")

    result = {"_names": {}}

    for filename, factor_key in _CSV_MAP.items():
        path = os.path.join(datasets_dir, filename)
        if not os.path.exists(path):
            logger.warning("Timeseries: CSV not found: %s", path)
            continue

        df = pd.read_csv(path, skiprows=4, encoding="utf-8-sig")

        # Identify year columns (numeric strings ≥ 1960)
        year_cols = sorted(
            [c for c in df.columns if c.isdigit() and int(c) >= 1960],
            key=int
        )

        if not year_cols:
            logger.warning("Timeseries: no year columns in %s", filename)
            continue

        # Filter out aggregate rows
        mask = (
            df["Country Code"].notna() &
            ~df["Country Code"].isin(_AGGREGATE_CODES)
        )
        df = df.loc[mask].copy()
        df["Country Code"] = df["Country Code"].str.strip().str.upper()

        # Validation range for this factor
        lo, hi = _VALIDATION.get(factor_key, (None, None))

        factor_data = {}
        for _, row in df.iterrows():
            code = str(row["Country Code"]).strip()[:3]
            if not code:
                continue

            # Store country name
            if code not in result["_names"] and pd.notna(row.get("Country Name")):
                result["_names"][code] = str(row["Country Name"]).strip()

            series = []
            for yr_col in year_cols:
                val = pd.to_numeric(row.get(yr_col), errors="coerce")
                if pd.isna(val):
                    continue
                # Validate
                if lo is not None and val < lo:
                    continue
                if hi is not None and val > hi:
                    continue
                series.append((int(yr_col), round(float(val), 4)))

            if series:
                factor_data[code] = series

        result[factor_key] = factor_data
        logger.info("Timeseries: %s → %d countries, years %s–%s",
                    factor_key, len(factor_data), year_cols[0], year_cols[-1])

    _ts_cache = result
    total_countries = len(result.get("_names", {}))
    logger.info("Timeseries loader complete: %d countries across %d factors",
                total_countries, len(result) - 1)
    return result


if __name__ == "__main__":
    data = load_timeseries()
    print(f"Factors: {[k for k in data if k != '_names']}")
    print(f"Countries: {len(data['_names'])}")
    # Sample
    for fk in [k for k in data if k != "_names"]:
        sample_code = next(iter(data[fk]))
        series = data[fk][sample_code]
        name = data["_names"].get(sample_code, sample_code)
        print(f"  {fk}: {name} → {len(series)} points, {series[0][0]}–{series[-1][0]}")
