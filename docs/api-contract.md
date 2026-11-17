# API Contract

Base URL (local): `http://localhost:8000`

## POST /api/v1/routes/optimize/

Plans the route between two US locations and the cheapest fuel stops along it.

### Request

```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA",
  "initial_fuel_gallons": 0
}
```

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `start` | string | yes | `"City, ST"` resolves offline; any other text (address, landmark) uses Nominatim. |
| `finish` | string | yes | Same as `start`. |
| `initial_fuel_gallons` | number | no | 0 to 50. Default 0: the trip includes the departure fill-up (see `docs/domain-rules.md`). |

### Response 200

```json
{
  "route": {
    "distance_miles": 2810.4,
    "duration_minutes": 2701.2,
    "geometry": {"type": "LineString", "coordinates": [[-74.00597, 40.71278], "..."]}
  },
  "fuel_stops": [
    {
      "station_id": 1234,
      "name": "PILOT TRAVEL CENTER #1243",
      "address": "I-80, EXIT 27",
      "city": "Delaware",
      "state": "NJ",
      "location": {"type": "Point", "coordinates": [-75.06, 40.88]},
      "location_precision": "city",
      "mile": 70.5,
      "price_per_gallon": 3.079,
      "gallons": 33.5,
      "cost": 103.14
    }
  ],
  "summary": {
    "distance_miles": 2810.4,
    "total_gallons_consumed": 281.04,
    "initial_fuel_gallons": 0.0,
    "total_gallons_purchased": 281.04,
    "remaining_fuel_gallons": 0.0,
    "total_fuel_cost": 857.34,
    "number_of_stops": 19
  },
  "map_url": "http://localhost:8000/api/v1/routes/map/?start=New+York%2C+NY&finish=Los+Angeles%2C+CA&initial_fuel_gallons=0"
}
```

- Coordinates follow GeoJSON order: `[longitude, latitude]`.
- `location_precision: "city"`: station positions are their city's center, not the exact pump.
- The route geometry is simplified (~50 m tolerance) to keep the response small.
- Rounding: miles and minutes 1 decimal, gallons 2, prices 3, money 2. Totals are computed before rounding.
- `total_fuel_cost` excludes `initial_fuel_gallons`, which is not purchased.

### Errors

Every error body has `error` (stable code) and `detail` (human message).

| Status | `error` | When | Extra fields |
|--------|---------|------|--------------|
| 400 | `invalid_request` | Missing field, wrong type, `initial_fuel_gallons` outside 0–50 | `fields` |
| 404 | `location_not_found` | `start` or `finish` cannot be resolved | `field` |
| 422 | `route_not_found` | No drivable route between the two points | |
| 422 | `no_station_near_origin` | Empty tank and no station in the first 15 miles | `at_mile` |
| 422 | `gap_exceeds_range` | A stretch longer than 500 miles without stations | `at_mile` |
| 502 | `external_service_error` | OSRM or Nominatim failed or timed out | |

## GET /api/v1/routes/map/

Same inputs as query parameters (`start`, `finish`, `initial_fuel_gallons`). Returns an HTML page with the route and the fuel stops on a Leaflet map. Errors return the same status codes with an HTML message.

## External calls per request

- `"City, ST"` start and finish: 0 geocoding calls (offline Gazetteer).
- Other text: up to 2 Nominatim calls, cached.
- Routing: exactly 1 OSRM call.
