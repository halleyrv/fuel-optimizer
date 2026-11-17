# Review Guidelines

For any agent reviewing a change in this repository (Codex, Antigravity, Claude or a human).
Review the diff you are given against the sources of truth below. Do not edit code; report findings.

## Sources of truth

1. `docs/assignment.md`: the original requirements.
2. `docs/domain-rules.md`: business rules, documented assumptions and the optimization algorithm.
3. `docs/architecture.md`: layers and dependency rules.

If the code and these documents disagree, that is a finding. If two documents disagree, report it too.

## What to check

- **Requirements:** every requirement the change touches is met (route, fuel stops, 500-mile range, 10 MPG, total cost, at most 3 external routing/geocoding calls per request).
- **Correctness:** wrong results, broken edge cases, crashes. Each finding needs a concrete input that triggers it.
- **Money and units:** prices and costs use `Decimal`; miles, gallons and USD are not mixed up; coordinates are (longitude, latitude) in PostGIS/GeoJSON.
- **Data integrity:** no invented coordinates; excluded stations are reported, never silently dropped; imports cannot wipe data on failure.
- **External calls:** timeouts and error handling on OSRM and Nominatim; failures surface as clear API errors.
- **Architecture:** `fuel_route/domain` imports nothing from Django, the database or HTTP clients.
- **Tests:** each business rule has a test through the public interface; tests are deterministic and do not call real external APIs.

## Do not report

These are deliberate, documented decisions:

- City-level station locations (`location_precision = "city"`) and the corridor tolerance based on city radius.
- Duplicate OPIS IDs consolidated at the median price.
- Initial fuel assumption: empty tank by default, departure fill-up within the origin window.
- Development-only settings: `DEBUG=1` and fallback credentials in `docker-compose.yml`, `runserver`, and no API authentication (the assignment requires none).
- Style preferences without a functional impact.

## Output format

Return a list, most severe first. One entry per finding:

```
- severity: blocker | advisory
  location: path/to/file.py:42
  finding: one sentence stating the defect
  scenario: concrete input or state -> wrong output or crash
  suggestion: smallest fix
```

- **blocker:** violates a requirement or a domain rule, or produces a wrong result with realistic input.
- **advisory:** everything else worth fixing later.

If there are no findings, say so explicitly. Do not pad the list.
