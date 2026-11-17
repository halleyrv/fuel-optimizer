# API Contract

The endpoints, fields and error codes are documented with OpenAPI 3 (drf-spectacular):

- Swagger UI: `http://localhost:8000/api/docs/`
- Schema: `http://localhost:8000/api/schema/` (importable into Postman)

The schema is the source of truth. `tests/api/test_docs.py` validates it without warnings and checks that real responses match it. This file only covers what the schema cannot express.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/routes/optimize/` | Route, cheapest fuel stops, total fuel cost and a `map_url`. |
| GET | `/api/v1/routes/map/` | HTML map of the same plan (`start`, `finish`, `initial_fuel_gallons` as query parameters). Documented in the schema with `text/html` responses; open it in a browser to see the map. |

## Conventions

- Coordinates follow GeoJSON order: `[longitude, latitude]`.
- `location_precision: "city"`: station positions are their city's center, never the exact pump.
- The route geometry is simplified (~50 m tolerance) to keep a coast-to-coast response near 60 KB.
- Rounding: miles and minutes 1 decimal, gallons 2, prices 3, money 2. Totals are computed with `Decimal` before rounding.
- `total_fuel_cost` covers purchases only; `initial_fuel_gallons` is not charged.
- Every error body has `error` (stable code) and `detail` (human message), including framework errors such as malformed JSON.

## External calls per request

- `"City, ST"` start and finish: 0 geocoding calls (offline Census Gazetteer).
- Any other text: up to 2 Nominatim calls, cached.
- Routing: at most 1 OSRM call; a repeated trip is served from the route cache (24 h) with none.
