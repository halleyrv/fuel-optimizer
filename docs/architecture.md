# Architecture

Pragmatic hexagonal layout inside one Django app, `fuel_route`.

```
fuel_route/
  domain/          Pure Python: entities, rules, optimizer. No Django, no I/O.
  application/     Use cases. Orchestrate domain + ports (Protocols).
  infrastructure/  Adapters: Gazetteer file, Nominatim, OSRM, PostGIS queries.
  api/             DRF views and serializers.
  models.py        Django ORM models (persistence only).
  management/      CLI entry points (station import).
```

## Dependency rules

- `domain` imports nothing from the other layers or from Django.
- `application` imports `domain` and depends on ports declared as `typing.Protocol`.
- `infrastructure` and `api` implement or call `application`; they may use Django.
- Money and prices use `Decimal`.

## Data flow

1. Import (offline, once): CSV → normalize + consolidate duplicates → geocode by city/state → `FuelStation` rows with a PostGIS point.
2. Request: resolve start/finish → one OSRM call → PostGIS corridor query → optimizer → response.
