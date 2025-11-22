import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Station

app = FastAPI(title="EV Charging Map API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StationCreate(Station):
    pass


class StationOut(Station):
    id: str


@app.get("/")
def read_root():
    return {"message": "EV Charging Map Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "Unknown"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


@app.get("/schema")
def get_schema():
    # Minimal schema exposure for viewer/tools
    return {
        "station": {
            "fields": list(Station.model_fields.keys())
        }
    }


# Utilities

def _to_station_out(doc) -> StationOut:
    if not doc:
        raise HTTPException(status_code=404, detail="Station not found")
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return StationOut(**doc)


@app.get("/api/stations", response_model=List[StationOut])
def list_stations(
    connector: Optional[str] = Query(default=None, description="Filter by connector type"),
    min_power: Optional[float] = Query(default=None, description="Minimum power in kW"),
    city: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Search name or address contains"),
    limit: int = Query(default=200, ge=1, le=1000)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    filter_dict = {}
    if connector:
        filter_dict["connectors"] = connector
    if min_power is not None:
        filter_dict["power_kw"] = {"$gte": float(min_power)}
    if city:
        filter_dict["city"] = {"$regex": city, "$options": "i"}
    if q:
        filter_dict["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"address": {"$regex": q, "$options": "i"}},
        ]

    docs = db["station"].find(filter_dict).limit(int(limit))
    return [_to_station_out(d) for d in docs]


@app.get("/api/stations/near", response_model=List[StationOut])
def stations_near(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(25, gt=0, le=1000)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Naive bounding box search (no geo index in this environment)
    # 1 deg lat ~ 111 km, 1 deg lon ~ 111*cos(lat)
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * max(0.01, abs(__import__('math').cos(lat * __import__('math').pi / 180))))

    filter_dict = {
        "latitude": {"$gte": lat - lat_delta, "$lte": lat + lat_delta},
        "longitude": {"$gte": lng - lng_delta, "$lte": lng + lng_delta},
    }
    docs = db["station"].find(filter_dict).limit(500)
    return [_to_station_out(d) for d in docs]


@app.post("/api/stations", response_model=str)
def create_station(station: StationCreate):
    inserted_id = create_document("station", station)
    return inserted_id


@app.get("/api/stations/{station_id}", response_model=StationOut)
def get_station(station_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["station"].find_one({"_id": ObjectId(station_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid station id")
    return _to_station_out(doc)


# Seed some demo stations (India) if collection is empty
@app.post("/api/seed")
def seed_demo_data():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    count = db["station"].count_documents({})
    if count > 0:
        return {"inserted": 0, "message": "Stations already present"}

    demo: List[Station] = [
        Station(
            name="Chargeway - Indiranagar",
            network="Chargeway",
            latitude=12.9716,
            longitude=77.5946,
            address="100 Feet Rd, Indiranagar",
            city="Bengaluru",
            state="Karnataka",
            country="IN",
            postal_code="560038",
            connectors=["CCS2", "Type2"],
            power_kw=60,
            price="₹20/kWh",
            amenities=["Restrooms", "Cafe"],
            phone="080-123456",
            hours="24/7",
        ),
        Station(
            name="Chargeway - BKC",
            network="Chargeway",
            latitude=19.0678,
            longitude=72.8677,
            address="Bandra Kurla Complex",
            city="Mumbai",
            state="Maharashtra",
            country="IN",
            postal_code="400051",
            connectors=["CCS2"],
            power_kw=120,
            price="₹22/kWh",
            amenities=["Mall", "Food Court"],
        ),
        Station(
            name="Chargeway - Cyber City",
            network="Chargeway",
            latitude=28.4946,
            longitude=77.0888,
            address="DLF Cyber City",
            city="Gurugram",
            state="Haryana",
            country="IN",
            postal_code="122002",
            connectors=["CCS2", "CHAdeMO"],
            power_kw=50,
            price="₹18/kWh",
            amenities=["Parking", "Restrooms"],
        ),
    ]

    inserted = 0
    for s in demo:
        create_document("station", s)
        inserted += 1
    return {"inserted": inserted}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
