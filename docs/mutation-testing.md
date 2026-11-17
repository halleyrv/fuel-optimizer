# Mutation Testing

Scope: `fuel_route/domain/` only (configured in `pyproject.toml` under `[tool.mutmut]`).
The domain is small, critical and its tests run without Django or the database.

```bash
rm -rf mutants          # mutmut caches by source; clear it after changing tests
uv run mutmut run
uv run mutmut results   # lists surviving mutants
uv run mutmut show <id> # shows the mutation
```

## Latest run

224 mutants: 219 killed, 2 detected by timeout (the mutation makes the station loop never end), 3 surviving (all equivalent, listed below).

## Accepted equivalent mutants

A mutant is equivalent when it changes the code but cannot change any result.

| Mutant | Mutation | Why it is equivalent |
|--------|----------|----------------------|
| `optimizer.x_plan_fuel__mutmut_24` | `s.mile <= route_miles` → `<` | A station exactly at the destination is never needed: nothing is bought once the destination is reached. |
| `optimizer.x__next_stop__mutmut_33`, `_35` | `min(in_range, key=price)` → `min(in_range)` (nearest station) | When no cheaper station is in range the tank is filled at the current (cheapest) station. Driving to the nearest station instead never forces a purchase there: the next cheaper station is already reachable on that full tank. Both variants are the textbook greedy; the exhaustive DP cross-check passes for both. |
