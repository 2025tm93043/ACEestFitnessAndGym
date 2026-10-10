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

## [2.2.1]
- Per-client weekly adherence line chart: `GET /clients/<name>/progress/chart.svg`.

## [2.2.4]
- Program catalogue expanded to four programs: FL 3-day, FL 5-day, MG PPL, Beginner (`FL`/`MG` kept as aliases).
- Client profile gains height, target weight, target adherence; all optional.
- Client summary block: program notes, goals, weeks logged, average adherence, last body metrics.
- Workout logging with optional exercise (`POST|GET /clients/<name>/workouts`).
- Body metrics (weight/waist/bodyfat) + weight trend chart (`/clients/<name>/metrics...`).
- BMI & risk info: `GET /clients/<name>/bmi`.
- Database schema is migrated in place with `ALTER TABLE` (the desktop app dropped the old table).

## [3.0.1]
- Maintenance release. The 3.0.1 source is byte-identical to 2.2.4 (no functional change); version bump only.

## [3.1.2]
- Role-based login: `POST /login` returns a signed bearer token, `GET /me`; every other endpoint now
  requires `Authorization: Bearer <token>` (disable with `REQUIRE_AUTH=False` for local experiments).
  Default user `admin` (password from `ACEEST_ADMIN_PASSWORD`, default `admin`, stored hashed).
- Membership expiry date on clients.
- "Generate AI Program": `POST /clients/<name>/ai-program` (beginner / intermediate / advanced).
- PDF client report: `GET /clients/<name>/report.pdf` (fpdf2).

## [3.2.4]
- Membership billing: `membership_status` + `membership_end` (replaces `membership_expiry`, which stays
  accepted as an alias and is migrated automatically); `GET /clients/<name>/membership` with renewal date.
- Template-based "Generate AI Program": `POST /clients/<name>/generate-program` stores the chosen program.
- PDF report now lists every client field (id, calories, targets, membership).
- New workout type: Cardio.
