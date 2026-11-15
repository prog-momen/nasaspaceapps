
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def clean_precipitation_data(
    input_file: str
) -> dict:

    input_path = RAW_DIR / input_file

    if not input_path.exists():
        raise FileNotFoundError(
            f"Raw data file not found: {input_path}"
        )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Load original NASA POWER JSON
    with open(input_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    parameter_data = (
        payload["properties"]["parameter"]["PRECTOTCORR"]
    )

    # Convert JSON data to DataFrame
    df = pd.DataFrame(
        parameter_data.items(),
        columns=["date", "precipitation"]
    )

    # Standardize data types
    df["date"] = pd.to_datetime(
        df["date"],
        format="%Y%m%d"
    )

    df["precipitation"] = pd.to_numeric(
        df["precipitation"],
        errors="coerce"
    )

    # Replace NASA POWER fill values
    df["precipitation"] = df[
        "precipitation"
    ].replace(-999.0, float("nan"))

    # Sort chronologically
    df = df.sort_values(
        "date"
    ).reset_index(drop=True)

    # Remove missing and duplicate records
    original_count = len(df)

    df = df.dropna(
        subset=["precipitation"]
    )

    df = df.drop_duplicates(
        subset=["date"]
    )

    removed_count = original_count - len(df)

    # Save processed dataset
    output_path = (
        PROCESSED_DIR /
        f"{input_path.stem}_cleaned.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        date_format="%Y-%m-%d"
    )

    return {
        "status": "success",
        "source_file": input_file,
        "output_file": output_path.name,
        "original_records": original_count,
        "cleaned_records": len(df),
        "removed_records": removed_count,
        "missing_values": int(
            df["precipitation"].isna().sum()
        ),
        "first_date": str(df["date"].min().date()),
        "last_date": str(df["date"].max().date())
    }
