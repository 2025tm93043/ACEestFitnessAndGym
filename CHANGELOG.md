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
