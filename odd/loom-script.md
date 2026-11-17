# Loom Script (5 minutes max)

Before recording:

- [ ] `docker compose up -d` is running and stations are imported.
- [ ] Warm the route cache: run the three Postman requests once (cold coast-to-coast takes ~3.6 s, cached ~0.7 s).
- [ ] Postman collection ready: import `http://localhost:8000/api/schema/`, or create three requests by hand.
- [ ] Tabs open: Postman, Swagger (`/api/docs/`), the map page, VS Code on `fuel_route/`.

## 0:00 – 0:30 · What it does

> "This is a Django REST API that takes a start and finish in the USA and returns the route, the cheapest places to refuel with a 500-mile range at 10 MPG, the total fuel cost, and a map. It makes one routing call per request."

## 0:30 – 2:00 · Demo in Postman

1. **Chicago, IL → Denver, CO** (`POST /api/v1/routes/optimize/`).
   Point at `summary.total_fuel_cost` ($300.84), `fuel_stops` (mile, price, gallons, cost) and `route.geometry`.
2. **Open `map_url`** in the browser: the route, a marker per stop, and the table.
3. **Same trip with `"initial_fuel_gallons": 25`**: the cost drops to $220.87 with 6 stops.
   > "The assignment does not say how much fuel the truck starts with, so by default the trip includes the departure fill-up, and the client can override it."
4. **New York, NY → Los Angeles, CA**: 2,810 miles, $857.34, under a second when cached.
5. **One error**: `"start": "Qwxzvbnmkjh Plkjhgf"` returns 404 `location_not_found`. Mention that every error has a stable code.
6. Flash **Swagger** at `/api/docs/` for 5 seconds: "Every field and error is documented here."

## 2:00 – 4:00 · Code walkthrough

Keep each stop under 30 seconds. Show the file, say one sentence, move on.

1. **The data problem** (`docs/domain-rules.md`, section 2):
   > "The CSV has no coordinates and the addresses are highway exits, so I geocode each station once at import, offline, to its city using the US Census Gazetteer. 97% of US stations resolve, and every location is flagged as city-level, never presented as exact."
2. **Layers** (`fuel_route/`): domain, application, infrastructure, api.
   > "The optimizer is pure Python with Decimal money; it knows nothing about Django, PostGIS or OSRM."
3. **The optimizer** (`fuel_route/domain/optimizer.py`):
   > "At each station: buy just enough to reach the next cheaper station in range; if there is none, fill up. That is the classic greedy, and it is optimal for a single route."
   Then show `test_greedy_matches_the_exact_optimum_on_random_routes`:
   > "I verified it against an exhaustive dynamic-programming search on 200 random routes."
4. **The use case** (`fuel_route/application/plan_trip.py`): resolve, one OSRM call, PostGIS corridor, optimizer.
5. **PostGIS corridor** (`fuel_route/infrastructure/station_repository.py`): the spatial index, the per-station tolerance, `ST_LineLocatePoint` for the mile.

## 4:00 – 4:45 · Quality and trade-offs

> "Beyond the 87 tests, I ran mutation testing on the domain (220 of 223 mutants killed, the rest documented as equivalent) and had an external model review each feature against written guidelines; I verified every finding before fixing it."

> "One honest trade-off: the plan is cost-optimal, so it can include small top-ups at nearby stations. In production I'd add a per-stop cost and solve it with dynamic programming."

## 4:45 – 5:00 · Close

> "Everything runs with `docker compose up`, the README has the quick start, and the assumptions are documented. Thanks for watching."

## If something fails while recording

- OSRM slow or down: use a trip already in the cache (the three above).
- Map page blank: check the network tab for the Leaflet CDN; the JSON response is enough to show the stops.
