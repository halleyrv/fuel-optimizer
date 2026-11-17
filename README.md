# Fuel Route Optimizer

A Django REST API that takes a start and finish anywhere in the USA and returns the driving route, the cheapest places to refuel along it (500-mile range, 10 MPG) and the total fuel cost, plus a map of the trip.

```
New York, NY → Los Angeles, CA: 2,810 mi · 19 stops · 281 gal · $857.34 · 1 routing call
```

## Quick start

Requires Docker.

```bash
docker compose up --build -d                                         # API + PostGIS, runs migrations
docker compose run --rm web python manage.py import_stations         # load the fuel price CSV (~30 s, offline)
curl -X POST http://localhost:8000/api/v1/routes/optimize/ \
  -H 'Content-Type: application/json' \
  -d '{"start": "Chicago, IL", "finish": "Denver, CO"}'
```

Then open:

| URL | What |
|-----|------|
| `http://localhost:8000/api/docs/` | Swagger UI: every field and error code, with "Try it out" |
| `http://localhost:8000/api/v1/routes/map/?start=Chicago%2C+IL&finish=Denver%2C+CO` | The plan on a map (the `map_url` in every response) |
| `http://localhost:8000/api/schema/` | OpenAPI 3 schema, importable into Postman |

Optional: put any variable from [Configuration](#configuration) in a `.env` file. Without it, local development defaults apply.

## API at a glance

`POST /api/v1/routes/optimize/`

| Field | Required | Notes |
|-------|----------|-------|
| `start`, `finish` | yes | `"City, ST"` resolves offline; any other text (address, landmark) uses Nominatim |
| `initial_fuel_gallons` | no | 0–50, default 0 (see assumptions) |

The response has `route` (distance, duration, GeoJSON line), `fuel_stops` (station, mile, price, gallons, cost), `summary` (`total_fuel_cost` and totals) and `map_url`.

Real results from the supplied data:

| Trip | Distance | Stops | Gallons bought | Fuel cost |
|------|----------|-------|----------------|-----------|
| Dallas, TX → Houston, TX | 238 mi | 2 | 23.8 | $65.82 |
| Chicago, IL → Denver, CO | 1,003 mi | 9 | 100.3 | $300.84 |
| Chicago → Denver, departing with 25 gal | 1,003 mi | 6 | 75.3 | $220.87 |
| New York, NY → Los Angeles, CA | 2,810 mi | 19 | 281.1 | $857.34 |

Errors always return `{"error": "<code>", "detail": "..."}`: `invalid_request` (400), `location_not_found` (404), `route_not_found` / `no_station_near_origin` / `gap_exceeds_range` (422), `external_service_error` (502). Details in [`docs/api-contract.md`](docs/api-contract.md) and Swagger.

## How it works

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant API as Django API
    participant G as Census Gazetteer (offline)
    participant N as Nominatim
    participant O as OSRM
    participant DB as PostGIS
    participant F as Fuel optimizer (domain)

    C->>API: POST /api/v1/routes/optimize/ {start, finish}
    API->>G: resolve "City, ST"
    opt other text, or city not found
        API->>N: search (cached)
    end
    alt trip already routed
        API->>API: route from cache (no external call)
    else first time
        API->>O: one route request
        O-->>API: distance, duration, GeoJSON line
    end
    API->>DB: stations within the corridor (GIST index)
    DB-->>API: stations with their mile along the route
    API->>F: plan_fuel(distance, stations, initial fuel)
    F-->>API: stops, gallons, cost
    API-->>C: route, fuel_stops, summary, map_url
```

1. **Stations are geocoded once, at import.** The CSV has no coordinates and 7,464 of 8,151 addresses are highway exits (`I-44, EXIT 283`), so each station is placed at its city's center using the US Census Gazetteer (offline, public domain). 6,447 of 6,626 US stations resolve (97.3%).
2. **One routing call per request.** OSRM's public server returns the full route geometry; repeated trips come from a 24 h cache with no call at all.
3. **Corridor search in PostGIS.** A station qualifies within 5 km of the route plus its city's radius (capped at 10 km), using the spatial index. `ST_LineLocatePoint` gives its mile along the route.
4. **Greedy optimizer.** At each station: buy just enough to reach the next cheaper station within range; if there is none, fill the tank and continue to the cheapest station in range. This is provably optimal for a single route, and it is verified against an exhaustive dynamic-programming search on 200 random routes.

## Project structure

Pragmatic hexagonal architecture ([`docs/architecture.md`](docs/architecture.md)):

```
fuel_route/
├── domain/            # pure Python: fuel optimizer, station and geocoding rules
├── application/       # use cases: import_stations, plan_trip (+ Protocol ports)
├── infrastructure/    # adapters: Census Gazetteer, Nominatim, OSRM, PostGIS, CSV
├── api/               # DRF view, OpenAPI serializers, map page
├── management/        # import_stations command
└── templates/         # map page (Leaflet)
config/                # Django settings and URLs
docs/                  # assignment, domain rules, architecture, API contract, reviews
data/                  # fuel price CSV + Census Gazetteer files
tests/                 # domain, application, infrastructure, integration (PostGIS), api
```

Dependencies point inward: `api` and `infrastructure` → `application` → `domain`. The domain imports nothing from Django, the database or HTTP clients.

## Assumptions and trade-offs

The assignment leaves these open; each is a deliberate, documented decision ([`docs/domain-rules.md`](docs/domain-rules.md)).

| Topic | Decision | Why |
|-------|----------|-----|
| Initial fuel | 0 by default; the trip includes the departure fill-up at a station in the first 15 miles. Send `initial_fuel_gallons` to override. | "Total money spent on fuel" should cover the whole trip. A full free tank would make any trip under 500 miles cost $0. |
| Station location | City center, flagged `location_precision: "city"` | Highway-exit addresses cannot be street-geocoded. Coordinates are approximate, never invented. |
| Duplicate stations | 678 OPIS IDs appear more than once (same address); one station at the median price | The CSV has no timestamps, so no row can be preferred as the latest. |
| Number of stops | Cost-optimal plans can include small top-ups (e.g. 0.9 gal) | A minimum purchase or per-stop cost breaks the greedy guarantee. The right fix is dynamic programming with a per-stop cost; out of scope here. |
| Data coverage | The CSV has only 16 California rows (Imperial Valley) and 620 Canadian rows (excluded) | Routes into Los Angeles refuel in Nevada; the last stretch (~235 mi) is within range. |
| Mile along the route | Approximate (line fraction measured in degrees) | Good enough for city-level station positions. |

## Quality checks

| Check | Command | Result |
|-------|---------|--------|
| Tests (domain, adapters, PostGIS, API) | `docker compose run --rm web pytest` | 87 passing |
| Mutation testing (domain) | `rm -rf mutants && uv run mutmut run` | 220 of 223 mutants killed; 3 equivalent, documented in [`docs/mutation-testing.md`](docs/mutation-testing.md) |
| OpenAPI schema | `docker compose run --rm web python manage.py spectacular --validate --fail-on-warn` | valid, no warnings (also run in tests) |
| External review | Antigravity, against [`docs/review-guidelines.md`](docs/review-guidelines.md) | 2 rounds; findings verified before fixing, 1 false positive dismissed with evidence |

## Local development only

These settings are intentional for running the assessment locally, not for production:

- `DEBUG=1`, fallback database credentials and `runserver` in `docker-compose.yml`. Outside debug, `DJANGO_SECRET_KEY` is required and the app refuses to start without it.
- No authentication on the API, because the assignment requires none.
- Public OSRM and Nominatim servers. Both are rate-limited, so production should self-host them or use a paid provider.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_DEBUG` | 1 in Docker Compose, 0 otherwise | Debug mode |
| `DJANGO_SECRET_KEY` | dev-only key in debug | Required when debug is off |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Accepted hosts |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | local-only values | Database credentials |
| `CORRIDOR_BASE_METERS` | 5000 | Distance from the route a station may be |
| `CORRIDOR_RADIUS_CAP_METERS` | 10000 | Maximum extra tolerance from a station's city radius |
| `OSRM_URL` | public OSRM server | Routing provider |
| `NOMINATIM_URL` | public Nominatim server | Geocoding fallback |
| `EXTERNAL_TIMEOUT_SECONDS` | 10 | Timeout for external calls |
