
import requests
import pandas as pd
import json

from pathlib import Path


NASA_POWER_URL = (
    "https://power.larc.nasa.gov/api/temporal/daily/point"
)

# Directory for storing original NASA data
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_precipitation(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str
) -> dict:

    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date,
        "end": end_date,
        "format": "JSON",
        "time-standard": "UTC"
    }

    try:
        response = requests.get(
            NASA_POWER_URL,
            params=params,
            timeout=60
        )

        response.raise_for_status()
        payload = response.json()

    except requests.RequestException as error:
        raise RuntimeError(
            f"NASA POWER request failed: {error}"
        ) from error

    except ValueError as error:
        raise RuntimeError(
            "NASA POWER returned an invalid JSON response."
        ) from error

    # Save the original NASA POWER response
    file_path = (
        DATA_DIR /
        f"precipitation_{latitude}_{longitude}_{start_date}_{end_date}.json"
    )

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(
                payload,
                file,
                indent=4,
                ensure_ascii=False
            )

    except OSError as error:
        raise RuntimeError(
            f"Failed to save NASA POWER data: {error}"
        ) from error

    try:
        properties = payload["properties"]
        parameter_data = properties["parameter"]["PRECTOTCORR"]

        parameter_info = payload.get("parameters", {}).get(
            "PRECTOTCORR", {}
        )

        units = parameter_info.get("units", "unknown")

        df = pd.DataFrame(
            parameter_data.items(),
            columns=["date", "precipitation"]
        )

        df["date"] = pd.to_datetime(
            df["date"],
            format="%Y%m%d"
        )

        df["precipitation"] = pd.to_numeric(
            df["precipitation"],
            errors="coerce"
        )

        # Replace NASA POWER fill values
        df.loc[
            df["precipitation"] == -999.0,
            "precipitation"
        ] = float("nan")

        df = df.sort_values("date").reset_index(drop=True)

    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            "Unexpected NASA POWER response structure."
        ) from error

    records = []

    for _, row in df.iterrows():
        value = row["precipitation"]

        records.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "precipitation": (
                None if pd.isna(value) else float(value)
            )
        })

    return {
        "source": "NASA POWER",
        "dataset": "Daily PRECTOTCORR",
        "latitude": latitude,
        "longitude": longitude,
        "units": units,
        "time_standard": "UTC",
        "records_count": len(records),
        "records": records
    }
