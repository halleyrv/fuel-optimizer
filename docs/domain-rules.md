# Domain Rules

## 1. Vehicle Constraints

- Maximum driving range: **500 miles**.
- Fuel efficiency: **10 miles per gallon (MPG)**.
- Implied maximum tank capacity: **50 gallons**.
- Assume the vehicle starts with a full tank unless explicitly configured otherwise.
- Fuel consumption is calculated as distance / MPG.

The 50-gallon capacity is an assumption derived from the supplied range and fuel efficiency.

## 2. Station Data and Geocoding

The supplied CSV has no coordinates. Addresses are highway references (`I-44, EXIT 283 & US-69`); only 8 of 8,151 rows are postal addresses, so street-level geocoding is not viable.

- Stations are geocoded once, at import time, never during API requests.
- Locations are the internal point of the station's city (US Census Gazetteer, offline) matched by city + state.
- Cities missing from the Gazetteer are resolved once via Nominatim; results are cached in `data/geocode_cache.json` so imports stay offline and reproducible.
- Every location is stored with `location_precision = "city"` and a `location_radius_m` (equivalent radius of the city's land area). These are approximations and must never be presented as exact station locations.
- Rows outside the USA (Canadian provinces) are excluded.
- Rows whose city cannot be resolved are excluded, and the import reports each exclusion reason.
- Rows sharing an OPIS Truckstop ID are the same physical station (verified: same address, city and state). They are consolidated into one station whose price is the median of its rows, rounded to 4 decimals. The CSV has no timestamps, so no row can be preferred as the latest.

## 3. Route and Fuel Stations

- The route is calculated using OSRM.
- Fuel stations must be located within a configurable corridor around the route.
- Because locations are city-level, a station's tolerance is the base corridor plus its `location_radius_m` (capped).
- Each station must have valid geographic coordinates and a valid fuel price.
- Stations are ordered by their projected distance along the route.
- Unresolved or invalid stations must not be considered.

Station proximity is an approximation of accessibility. The initial implementation does not calculate individual road detours to each station.

## 4. Fuel Optimization

The objective is to minimize total fuel purchase cost while ensuring the vehicle can reach the destination.

Use a greedy refueling strategy:

1. At each reachable station, identify the nearest subsequent station with a lower fuel price that can be reached with the available fuel.
2. If a cheaper station is reachable, purchase only enough fuel to reach it.
3. If no cheaper station is reachable, purchase enough fuel to fill the tank, up to its capacity.
4. If the destination is reachable with the available fuel, purchase only the amount needed to complete the trip.
5. Never exceed tank capacity or purchase negative quantities.

The optimizer must account for initial fuel, station positions, fuel prices, and destination distance.

## 5. Cost and Consumption

- Total distance is expressed in miles.
- Fuel quantities are expressed in gallons.
- Fuel prices are expressed in USD per gallon.
- Fuel consumed = total route distance / MPG.
- Purchase cost = gallons purchased × station price.
- Initial fuel is not counted as a purchase expense.
- Remaining fuel must be reported.

## 6. Failure Conditions

The application must clearly report when:

- No valid route can be calculated.
- No feasible sequence of fuel stops can reach the destination.
- No suitable fuel stations are available along the route.
- Required station data is invalid or unavailable.

Do not return an apparently successful optimization when the destination cannot be reached.