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
- S12 (user, 2026-11-17, future refactor): "Después refactorizá plan_fuel en optimizer.py con guard clauses: sacá el origen del loop, extraé _next_stop y _buy, sin interfaces ni Strategy. Mantené los tests en verde (incluido el de la búsqueda exhaustiva) y hacé un commit separado para cada cosa."
- S13 (user, 2026-11-17): "dale, documentalo así y seguí con T5" — keep the cost-optimal greedy; document the many-small-stops trade-off and the DP + per-stop cost alternative.

## Tasks

- [x] T0 docs: fix CLAUDE.md, domain-rules geocoding/duplicates, architecture.md — inline — 43a8c6e
- [x] T1 S6 S8: scaffold (Django 6.1, DRF, PostGIS, Docker) + station import with Gazetteer geocoding — inline — see commit `feat(stations)`
- [ ] T2 S6: Nominatim fallback for unmatched cities, cached in `data/geocode_cache.json` — inline
- [x] T3 S3 S4 S10 S11: fuel optimizer (pure domain, TDD) — inline — branch feat/fuel-optimizer
- [x] T4 S5 S7 S9: OSRM adapter, start/finish resolution, PostGIS corridor query — inline — branch feat/route-planning (2d3209f, f91d624, 1618472, refactor + feat(trip))
- [x] T5 S1 S2 S4: API endpoint, `docs/api-contract.md`, map view — inline — branch feat/api (feat(api), perf(routing))
- [ ] T6: README, Loom script — inline
- [ ] T7 S12: refactor `plan_fuel` with guard clauses (origin out of the loop, extract `_next_stop` and `_buy`), no interfaces or Strategy; tests green incl. DP cross-check and mutmut; one commit per step — inline, after T6

## Log

- L1 (user, 2026-11-16): "dale, arrancá con la geocodificación" + pasted decisions 1–7 from another assistant (see S6–S10).
- L2: CSV profile: 8,151 rows, 620 Canadian, 8 postal addresses, 678 duplicate IDs (597 with different prices, all same address). Gazetteer first-pass match 94% of US rows.
- L3: Open point: decision 5 says "abastecerse para llegar a la estación más lejana alcanzable"; domain-rules says fill the tank. Kept domain-rules (filling at the cheapest station in range is never worse).
- L4: Initial fuel resolved as S11 (documented in domain-rules "Assumption: initial fuel").
- L5: T1 done. Gazetteer places + county subdivisions resolve 6,447 of 6,626 US stations (97.3%); 179 stations / 135 cities unresolved (unincorporated communities). Real import: 30 s in Docker. GIST index on location verified. Tests: 24 passed (`docker compose run --rm web pytest`). Integration test written together with the command (RED not observed separately).
- L6: Native review of 1aab741 (lenses risk + reliability): approved and acknowledged. Non-blocking follow-ups: R1 insecure dev defaults in settings.py; R1 open API permissions; R3-001 station_repository; R3-002/R3-003 import_stations command (args/defaults and replacing data); R3-004 gazetteer parsing. Address during T2/T5.
- L7: T3 done. `fuel_route/domain/optimizer.py`; 11 tests incl. exhaustive DP cross-check on 200 random routes (141 feasible, 126 multi-stop) — all match. RED observed (module missing) before implementation.
- L8: Antigravity review (agy -p --mode plan, docs/review-guidelines.md) of main..feat/fuel-optimizer: 4 findings, all confirmed and fixed with RED tests: origin-window range bug (blocker), import wiping data on empty result (blocker), domain-rules 4.1 wording (advisory), __MACOSX zip entries (advisory). 42 tests pass. Note: headless agy denies shell commands; pass a pre-generated diff via --add-dir.
- L9: Mutation testing (mutmut 3.8.1, domain only): first run 189/207 killed; after new tests 204/207, 3 equivalent documented in docs/mutation-testing.md. Rule added to AGENTS.md. 47 tests pass.
- L10: T4 done. OSRM verified live: NoRoute returns HTTP 400 with JSON body (handled). Corridor NY→LA: 349 stations in 0.43 s. End to end NY→LA: 2,810 mi, 281 gal, $857.34, 19 stops, 3.2 s, 1 OSRM call. Dataset limitation: only 16 CA rows (Imperial Valley), last station before LA is Las Vegas area (~235 mi, within range). mutmut 220/223 (3 documented equivalents). 66 tests pass.
- L11: Open question for the user: the optimal plan has many tiny purchases (0.9 gal, 1.1 gal) and 19 stops; cost-optimal but impractical. Options: a minimum purchase or a per-stop cost. Not implemented without a decision.
- L12: L11 resolved by S13 (documented in domain-rules "Known trade-off: number of stops").
- L13: T5 done. POST /api/v1/routes/optimize/ + GET /api/v1/routes/map/ (Leaflet). Live: NY→LA 200, 61 KB, 3.6 s cold, 0.73 s cached; 404 and 400 verified live. "Atlantis, ZZ" resolves via Nominatim to Atlantis, FL (real city). 81 tests pass.
- L14: Antigravity review #2 (2f05265..cf83a32): 2 findings. Blocker "ST_LineLocatePoint NULL on zero-length route" DISMISSED: live start=finish (Effingham, IL) returns 200, and PostGIS returns 0 (not NULL) for a zero-length line. Advisory "Nominatim payload KeyError -> 500" CONFIRMED and fixed with RED test. 83 tests pass.
- L15: User: "estándar ... apidocs así se hace siempre en todos los proyectos senior" → Swagger UI at /api/docs/ (drf-spectacular 0.30.0, verified in Context7). Schema validated with --fail-on-warn; drift tests compare real responses to documented serializers. api-contract.md reduced to non-schema conventions. 87 tests pass.
