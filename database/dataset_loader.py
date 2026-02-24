"""
Dataset Loader — Reads World Bank CSV datasets, merges them, validates data,
and upserts into the environmental_country_stats table.

CSV files expected in datasets/:
  - co2_per_capita.csv
  - renewable_energy_share.csv
  - forest_area_percent.csv
  - pm25_air_pollution.csv
"""

import os
import pandas as pd
from app_logger import logger

# ── Known aggregate / region codes to exclude ──
_AGGREGATE_CODES = {
    "AFE", "AFW", "ARB", "CEB", "CSS", "EAP", "EAR", "EAS", "ECA", "ECS",
    "EMU", "EUU", "FCS", "HIC", "HPC", "IBD", "IBT", "IDA", "IDB", "IDX",
    "INX", "LAC", "LCN", "LDC", "LIC", "LMC", "LMY", "LTE", "MEA", "MIC",
    "MNA", "NAC", "OED", "OSS", "PRE", "PSS", "PST", "SAS", "SSA", "SSF",
    "SST", "TEA", "TEC", "TLA", "TMN", "TSA", "TSS", "UMC", "WLD",
}

# ── CSV file → column mapping ──
_CSV_MAP = {
    "co2_per_capita.csv":          "co2_per_capita",
    "renewable_energy_share.csv":  "renewable_percentage",
    "forest_area_percent.csv":     "forest_area_percentage",
    "pm25_air_pollution.csv":      "pm25",
}

# ── Validation ranges ──
_VALIDATION = {
    "co2_per_capita":         (0, None),     # >= 0
    "renewable_percentage":   (0, 100),      # 0–100
    "forest_area_percentage": (0, 100),      # 0–100
    "pm25":                   (0, None),     # >= 0
}


def _find_best_year(dfs: dict[str, pd.DataFrame]) -> str:
    """Find the latest year column that has the best data coverage across all datasets."""
    # Collect year columns common to all datasets (numeric strings)
    year_cols = None
    for df in dfs.values():
        numeric_cols = {c for c in df.columns if c.isdigit() and int(c) >= 1960}
        year_cols = numeric_cols if year_cols is None else year_cols & numeric_cols

    if not year_cols:
        raise ValueError("No overlapping year columns found across datasets")

    # Score each year by total non-null values across all datasets
    year_scores = {}
    for year in sorted(year_cols, reverse=True):
        total = sum(
            pd.to_numeric(df[year], errors="coerce").notna().sum()
            for df in dfs.values()
        )
        year_scores[year] = total

    # Pick latest year among those within 95% of the best coverage
    max_score = max(year_scores.values())
    threshold = max_score * 0.95
    candidates = [y for y, s in year_scores.items() if s >= threshold]
    best = max(candidates, key=int)
    logger.info("Dataset loader: selected year %s (coverage score %d / max %d)",
                best, year_scores[best], max_score)
    return best


def _read_csv(filepath: str) -> pd.DataFrame:
    """Read a World Bank CSV (4 header rows to skip)."""
    df = pd.read_csv(filepath, skiprows=4, encoding="utf-8-sig")
    return df


def _validate_value(value, col_name):
    """Validate a single value against its allowed range. Returns None if invalid."""
    if pd.isna(value):
        return None
    lo, hi = _VALIDATION.get(col_name, (None, None))
    if lo is not None and value < lo:
        return None
    if hi is not None and value > hi:
        return None
    return float(value)


def load_and_merge_datasets(datasets_dir: str = None):
    """
    Read all 4 CSV files, merge on Country Code, validate, and upsert into DB.

    Returns:
        dict with keys: year, rows_processed, rows_inserted, rows_updated,
                        errors, sample (list of first 5 rows as dicts)
    """
    if datasets_dir is None:
        datasets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datasets")

    # ── Step 1: Read CSVs ──
    raw_dfs = {}
    for filename, col_name in _CSV_MAP.items():
        path = os.path.join(datasets_dir, filename)
        if not os.path.exists(path):
            logger.error("Dataset file not found: %s", path)
            continue
        raw_dfs[col_name] = _read_csv(path)
        logger.info("Read %s: %d rows", filename, len(raw_dfs[col_name]))

    if not raw_dfs:
        raise FileNotFoundError("No dataset CSV files found in " + datasets_dir)

    # ── Step 2: Find best year ──
    best_year = _find_best_year(raw_dfs)

    # ── Step 3: Extract & clean per-dataset ──
    cleaned = {}
    for col_name, df in raw_dfs.items():
        # Filter out aggregates and rows without country codes
        mask = (
            df["Country Code"].notna() &
            ~df["Country Code"].isin(_AGGREGATE_CODES)
        )
        subset = df.loc[mask, ["Country Name", "Country Code", best_year]].copy()
        subset.rename(columns={best_year: col_name}, inplace=True)
        subset[col_name] = pd.to_numeric(subset[col_name], errors="coerce")
        subset["Country Code"] = subset["Country Code"].str.strip().str.upper()
        subset.dropna(subset=["Country Code"], inplace=True)
        cleaned[col_name] = subset

    # ── Step 4: Merge on Country Code ──
    merged = None
    for col_name, subset in cleaned.items():
        if merged is None:
            merged = subset
        else:
            merged = merged.merge(
                subset[["Country Code", col_name]],
                on="Country Code",
                how="outer",
            )

    # Fill country names from any source for rows that came via outer join
    for col_name, subset in cleaned.items():
        name_map = subset.set_index("Country Code")["Country Name"]
        mask = merged["Country Name"].isna()
        merged.loc[mask, "Country Name"] = merged.loc[mask, "Country Code"].map(name_map)

    # Drop rows where we still have no name
    merged.dropna(subset=["Country Name"], inplace=True)

    # ── Step 5: Validate ranges ──
    errors = 0
    for col_name in _CSV_MAP.values():
        if col_name not in merged.columns:
            continue
        original = merged[col_name].copy()
        merged[col_name] = merged[col_name].apply(lambda v: _validate_value(v, col_name))
        invalid_count = original.notna().sum() - merged[col_name].notna().sum()
        if invalid_count > 0:
            logger.warning("Validation: %d invalid values set to NULL in %s", invalid_count, col_name)
            errors += invalid_count

    merged["year"] = int(best_year)

    logger.info("Merged dataset: %d rows, %d columns", len(merged), len(merged.columns))

    # ── Step 6: Upsert into DB ──
    from database.db_connection import get_db
    conn = get_db()
    cur = conn.cursor()

    rows_inserted = 0
    rows_updated = 0

    for _, row in merged.iterrows():
        cc = str(row["Country Code"]).strip()[:3]
        cn = str(row["Country Name"]).strip()[:150]
        co2 = None if pd.isna(row.get("co2_per_capita")) else float(row["co2_per_capita"])
        ren = None if pd.isna(row.get("renewable_percentage")) else float(row["renewable_percentage"])
        for_ = None if pd.isna(row.get("forest_area_percentage")) else float(row["forest_area_percentage"])
        pm = None if pd.isna(row.get("pm25")) else float(row["pm25"])
        yr = int(row["year"])

        cur.execute("""
            INSERT INTO environmental_country_stats
                (country_code, country_name, co2_per_capita, renewable_percentage,
                 forest_area_percentage, pm25, year, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (country_code) DO UPDATE SET
                country_name = EXCLUDED.country_name,
                co2_per_capita = EXCLUDED.co2_per_capita,
                renewable_percentage = EXCLUDED.renewable_percentage,
                forest_area_percentage = EXCLUDED.forest_area_percentage,
                pm25 = EXCLUDED.pm25,
                year = EXCLUDED.year,
                last_updated = CURRENT_TIMESTAMP
            RETURNING (xmax = 0) AS inserted
        """, (cc, cn, co2, ren, for_, pm, yr))

        result = cur.fetchone()
        if result and result[0]:
            rows_inserted += 1
        else:
            rows_updated += 1

    conn.commit()
    cur.close()

    rows_processed = len(merged)
    sample = merged.head(5).to_dict(orient="records")

    logger.info(
        "Dataset loader complete — year: %s | processed: %d | inserted: %d | updated: %d | validation_errors: %d",
        best_year, rows_processed, rows_inserted, rows_updated, errors,
    )

    return {
        "year": int(best_year),
        "rows_processed": rows_processed,
        "rows_inserted": rows_inserted,
        "rows_updated": rows_updated,
        "errors": errors,
        "sample": sample,
    }


if __name__ == "__main__":
    result = load_and_merge_datasets()
    print(f"\n{'='*60}")
    print(f"Year: {result['year']}")
    print(f"Rows processed: {result['rows_processed']}")
    print(f"Rows inserted:  {result['rows_inserted']}")
    print(f"Rows updated:   {result['rows_updated']}")
    print(f"Validation errors: {result['errors']}")
    print(f"\nSample (first 5 rows):")
    for row in result["sample"]:
        print(f"  {row}")
