
from datetime import date

from fastapi import FastAPI, HTTPException, Query

from app.data_acquisition.connectors.nasa_power import (
    fetch_precipitation
)

app = FastAPI(
    title="EarthTrend Explorer API",
    description="Environmental Data Acquisition Module",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "project": "EarthTrend Explorer",
        "module": "Environmental Data Acquisition",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/data/precipitation")
def get_precipitation(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be after or equal to start_date."
        )

    try:
        result = fetch_precipitation(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d")
        )
        return result

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error)
        ) from error