# Fuel Route Optimizer

Objective: Django API returning a route, optimal fuel stops and total fuel cost (Spotter assessment).
Branch: `feat/station-import` (one branch per stage). Delivery: ask-on-risk. Test runner: `docker compose run --rm web pytest`.

## Specs

- S1 (assignment): "Build an API that takes inputs of start and finish location both within the USA"
- S2 (assignment): "Return a map of the route along with optimal location to fuel up along the route -- optimal mostly means cost effective based on fuel prices"
- S3 (assignment): "Assume the vehicle has a maximum range of 500 miles so multiple fuel ups might need to be displayed on the route"
- S4 (assignment): "Also return the total money spent on fuel assuming the vehicle achieves 10 miles per gallon"
- S5 (assignment): "The API shouldn't need to call the free map/routing API you found too much. One call to the map/route API is ideal, two or three is acceptable"
- S6 (decision 1): "Utilizar el Census Gazetteer offline para resolver ciudad + estado." / "Guardar `location_precision = "city"`" / "Resolver los aproximadamente 270 registros restantes mediante Nominatim durante la importación." / "Excluir los registros que no puedan resolverse razonablemente, dejando registro del motivo." / "No geocodificar estaciones durante las peticiones de la API."
- S7 (decision 2): "Adaptar la tolerancia según `location_precision`." / "Evitar presentar las estaciones aproximadas como ubicaciones exactas."
- S8 (decision 3): "Identificar duplicados exactos y consolidarlos." / "Evaluar la mediana cuando se confirme que corresponden a la misma estación física." Verified: all 597 multi-price IDs share address, city and state → median.
- S9 (decision 4): "Utilizar el mismo Gazetteer offline para resolver ciudades y estados." / "Si no se encuentran, utilizar Nominatim como fallback con caché." / "No superar las 3 llamadas externas por petición."
- S10 (decision 5): "Mantener la regla actual de `domain-rules.md`: buscar la siguiente estación alcanzable con un precio inferior." / "Respetar siempre las 500 millas de autonomía."
- S11 (user, 2026-11-16): initial fuel. User: "sí, me cierra, arrancá con el optimizador y Y si es necesario documentarlo en algún lado, un supuesto esto también para poder explicarlo." Agreed model: default 0 gallons, departure fill-up at stations within the first 15 miles; optional `initial_fuel_gallons` (0–50) not charged; no station near origin → infeasible.

## Tasks

- [x] T0 docs: fix CLAUDE.md, domain-rules geocoding/duplicates, architecture.md — inline — 43a8c6e
- [x] T1 S6 S8: scaffold (Django 6.1, DRF, PostGIS, Docker) + station import with Gazetteer geocoding — inline — see commit `feat(stations)`
- [ ] T2 S6: Nominatim fallback for unmatched cities, cached in `data/geocode_cache.json` — inline
- [x] T3 S3 S4 S10 S11: fuel optimizer (pure domain, TDD) — inline — branch feat/fuel-optimizer
- [ ] T4 S5 S7 S9: OSRM adapter, start/finish resolution, PostGIS corridor query — inline
- [ ] T5 S1 S2 S4: API endpoint, `docs/api-contract.md`, map view — inline
- [ ] T6: README, Loom script — inline

## Log

- L1 (user, 2026-11-16): "dale, arrancá con la geocodificación" + pasted decisions 1–7 from another assistant (see S6–S10).
- L2: CSV profile: 8,151 rows, 620 Canadian, 8 postal addresses, 678 duplicate IDs (597 with different prices, all same address). Gazetteer first-pass match 94% of US rows.
- L3: Open point: decision 5 says "abastecerse para llegar a la estación más lejana alcanzable"; domain-rules says fill the tank. Kept domain-rules (filling at the cheapest station in range is never worse).
- L4: Initial fuel resolved as S11 (documented in domain-rules "Assumption: initial fuel").
- L5: T1 done. Gazetteer places + county subdivisions resolve 6,447 of 6,626 US stations (97.3%); 179 stations / 135 cities unresolved (unincorporated communities). Real import: 30 s in Docker. GIST index on location verified. Tests: 24 passed (`docker compose run --rm web pytest`). Integration test written together with the command (RED not observed separately).
- L6: Native review of 1aab741 (lenses risk + reliability): approved and acknowledged. Non-blocking follow-ups: R1 insecure dev defaults in settings.py; R1 open API permissions; R3-001 station_repository; R3-002/R3-003 import_stations command (args/defaults and replacing data); R3-004 gazetteer parsing. Address during T2/T5.
- L7: T3 done. `fuel_route/domain/optimizer.py`; 11 tests incl. exhaustive DP cross-check on 200 random routes (141 feasible, 126 multi-stop) — all match. RED observed (module missing) before implementation.
