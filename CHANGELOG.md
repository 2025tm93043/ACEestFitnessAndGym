# Changelog

All notable changes per application version (ported from the original ACEest desktop releases).

## [1.0]
- Program catalogue: Fat Loss (FL), Muscle Gain (MG), Beginner (BG) with weekly workout chart and diet plan.
- Site metrics: capacity, area, break-even members.
- Endpoints: `/`, `/health`, `/programs`, `/programs/<code>`, `/site-metrics`.

## [1.1]
- Client profile: name, age, weight, program, weekly adherence (validated).
- Calorie estimation (weight x program factor): `GET /programs/<code>/calories?weight=`.
- `POST /clients` validates and acknowledges a client (not yet persisted).
- Program texts refreshed (Breakfast/Lunch/Dinner layout).

## [1.1.2]
- In-memory client list with coach notes (`GET /clients`).
- CSV export (`GET /clients/export.csv`).
- Progress chart: JSON data (`/clients/chart-data`) and SVG (`/clients/chart.svg`) - a
  dependency-free replacement for the matplotlib canvas.

## [2.0.1]
- SQLite persistence (`aceest_fitness.db`, override with `ACEEST_DB`): `clients` and `progress` tables.
- `POST /clients` now upserts by unique name; `GET /clients/<name>` loads a client.
- Weekly progress log: `POST|GET /clients/<name>/progress`.
- CSV export and progress chart now read from the database (adherence comes from the progress log).
- Notes / per-client adherence fields removed from the client record (as in the desktop release).

## [2.1.2]
- Maintenance release. The 2.1.2 source is byte-identical to 2.0.1 (no functional change); version bump only.
