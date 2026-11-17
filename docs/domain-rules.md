# Domain Rules

## 1. Vehicle Constraints

- Maximum driving range: **500 miles**.
- Fuel efficiency: **10 miles per gallon (MPG)**.
- Implied maximum tank capacity: **50 gallons**.
- Initial fuel: see "Assumption: initial fuel" below.
- Fuel consumption is calculated as distance / MPG.

The 50-gallon capacity is an assumption derived from the supplied range and fuel efficiency.

### Assumption: initial fuel

The assignment does not say how much fuel the vehicle has when it departs. We assume **the trip includes the departure fill-up**: by default the vehicle has 0 gallons and buys its first fuel at a station near the origin, so the reported cost covers all the fuel the trip consumes ("total money spent on fuel").

- Stations within the first 15 miles of the route (the origin window) can be used with an empty tank. The fuel for the miles driven before reaching that station is bought there too, so total consumption stays exactly distance / MPG. Range checks always use each station's real position.
- The optimizer decides how much to buy at departure; it does not have to fill the tank.
- Clients that already carry fuel send `initial_fuel_gallons` (0 to 50). That fuel is not charged.
- With an empty tank and no station inside the origin window, the route is reported as infeasible and the client is asked to provide `initial_fuel_gallons`.

## 2. Station Data and Geocoding

The supplied CSV has no coordinates. Addresses are highway references (`I-44, EXIT 283 & US-69`); only 8 of 8,151 rows are postal addresses, so street-level geocoding is not viable.

- Stations are geocoded once, at import time, never during API requests.
- Locations are the internal point of the station's city, matched offline by city + state against the US Census Gazetteer: incorporated places first, then county subdivisions (New England towns, townships). Matching ignores case, punctuation, spacing and St/Ste/Ft/Mt abbreviations.
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

1. At each station, identify the nearest subsequent station with a lower fuel price within a full tank's range (500 miles).
2. If a cheaper station is reachable, purchase only enough fuel to reach it.
3. If no cheaper station is reachable, purchase enough fuel to fill the tank, up to its capacity.
4. If the destination is within a full tank's range and no cheaper station comes first, purchase only the amount needed to complete the trip.
5. Never exceed tank capacity or purchase negative quantities.
6. After filling the tank because no cheaper station is in range, continue to the cheapest station in range.

The algorithm is verified against an exhaustive dynamic-programming search on 200 random routes (`tests/domain/test_optimizer.py`).

### Known trade-off: number of stops

The plan minimizes fuel cost only, so it can include small top-ups at nearby stations (for example 0.9 gallons, then 4 gallons one mile later). This is cost-optimal but not how a driver would refuel. A minimum purchase or a per-stop cost (driver time) would fix it, but either one breaks the greedy optimality guarantee; the correct solution is dynamic programming over stations and fuel levels. For this assessment we keep the provably optimal greedy and report the trade-off openly.

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