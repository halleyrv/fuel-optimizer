# AGENTS.md

Shared instructions for every coding agent (Claude Code, Codex, Antigravity).

## Project

Fuel Route Optimizer — Django REST API for optimizing fuel purchases along US road trips.

## Tech Stack

- Python 3.14
- Django (latest compatible stable version)
- Django REST Framework
- PostgreSQL + PostGIS
- GeoDjango
- OSRM
- GeoJSON
- pytest
- Docker Compose

## Architecture

Use pragmatic Hexagonal Architecture with tactical DDD and SOLID principles.

Separate:

- Domain
- Application
- Infrastructure
- API interfaces

Business logic must remain independent of Django, databases and external APIs.

Avoid unnecessary abstractions and overengineering.

## Project Documentation

Read the relevant documentation before implementing a task:

- `docs/assignment.md`: original assessment requirements.
- `docs/architecture.md`: architecture and dependency rules.
- `docs/domain-rules.md`: business rules and optimization algorithm.
- `docs/api-contract.md`: API specifications.
- `odd/tasks/fuel-route-optimizer.md`: current development tasks and decisions log.
- `docs/review-guidelines.md`: how to review a change (read it when acting as reviewer).

Do not load unrelated documentation unnecessarily.

## Engineering Rules

- Use type hints.
- Follow SOLID pragmatically.
- Keep functions focused.
- Use Decimal for monetary calculations.
- Use GeoDjango and PostGIS for spatial operations.
- Use spatial indexes.
- Handle external API failures and timeouts.
- Never invent geographic coordinates.
- Never commit credentials or secrets.
- Write automated tests for every relevant feature.
- Do not introduce unnecessary dependencies.

## Development Workflow

Before implementing:

1. Inspect existing code and relevant documentation.
2. Explain the implementation approach.
3. Identify risks and assumptions.

After implementing:

1. Run relevant tests.
2. Fix failures.
3. Summarize changed files.
4. Explain architectural decisions.

Work incrementally. Do not implement multiple unrelated tasks at once.

Preserve existing architectural decisions unless a change is explicitly justified.

## Development Practices

- Follow Test-Driven Development (TDD).

- Write a failing test before implementing new business behavior.

- Implement the minimum code required to pass the test.

- Refactor while keeping all tests green.

- Prioritize unit tests for domain logic.

- Before closing a feature that changes `fuel_route/domain`, run mutation testing: `rm -rf mutants && uv run mutmut run`, then `uv run mutmut results`. Every surviving mutant gets a test, or is listed as equivalent in `docs/mutation-testing.md` with the reason.

- Run relevant tests after every implementation phase.

- Apply SOLID principles pragmatically.

## Priority

Correctness > Maintainability > Performance > Complexity.

Build a reliable, testable and demonstrable solution within the assessment deadline.