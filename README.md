# ACEest Fitness & Gym - CI/CD Project

Flask web service for **ACEest Fitness & Gym**, built for *Introduction to DevOps - Assignment 1*.
The application evolved through ten desktop releases (1.0 -> 3.2.4); each release was ported to a Flask
API and committed in order, so `git log` / the tags below show the full history.

| Concern | Tooling |
|---|---|
| Application | Python 3.12, Flask, SQLite, fpdf2 |
| Tests / lint | Pytest, flake8 |
| Container | Docker (multi-stage, non-root, gunicorn) |
| CI | GitHub Actions (`.github/workflows/main.yml`) |
| Build server | Jenkins (`Jenkinsfile`) |

## Project layout

```
app.py            Flask app factory + routes          clients.py   validation & persistence helpers
programs.py       program catalogue, calorie factors   workouts.py  workouts / metrics / BMI
db.py             SQLite schema + migrations           auth.py      signed bearer tokens
charts.py         dependency-free SVG charts           reports.py   PDF client report
ai_program.py     random workout generator             version.py   current version string
tests/            Pytest suite (one file per release)
Dockerfile        base -> test -> runtime stages       Jenkinsfile  Jenkins pipeline
```

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python app.py                      # http://localhost:5000
```

Try it:

```bash
curl localhost:5000/health
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
        -d '{"username":"admin","password":"admin"}' | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -X POST localhost:5000/clients -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"name":"Arun","program":"FL","height":175,"weight":80}'
curl -H "Authorization: Bearer $TOKEN" localhost:5000/clients/Arun
```

Configuration (environment variables):

| Variable | Default | Purpose |
|---|---|---|
| `ACEEST_DB` | `aceest_fitness.db` | SQLite file |
| `ACEEST_SECRET_KEY` | `dev-only-change-me` | token signing key - **change in production** |
| `ACEEST_ADMIN_PASSWORD` | `admin` | password of the seeded `admin` user - **change in production** |

## Running the tests manually

```bash
pip install -r requirements-dev.txt
pytest                 # whole suite
pytest -k membership   # a subset
flake8 .               # lint
```

Inside Docker (exactly what CI runs):

```bash
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

## Docker

```bash
docker build -t aceest-fitness .                      # default target = runtime
docker run -d -p 5000:5000 -v aceest-data:/data aceest-fitness
curl localhost:5000/health
```

The Dockerfile has three stages: `base` (runtime deps), `test` (adds pytest/flake8 + tests) and `runtime`
(slim image, non-root user `appuser`, gunicorn, `HEALTHCHECK`, data volume at `/data`). Test tooling never
reaches the production image.

## CI/CD overview

### GitHub Actions (`.github/workflows/main.yml`)
Triggered on every **push** and **pull_request**.

1. **Build & Lint** - install dependencies, `python -m compileall` (syntax errors), `flake8`.
2. **Docker image & Pytest** (needs stage 1) - build the runtime image, build the `test` target, run Pytest
   *inside the container*, then smoke-test the runtime image by calling `/health`.

### Jenkins (`Jenkinsfile`)
A declarative pipeline that gives a second, independent validation in a controlled build environment:
clean workspace -> checkout from GitHub -> create venv & install -> lint -> Pytest (JUnit report published)
-> `docker build` (runtime + test targets) -> run tests in the container -> cleanup.

Jenkins setup:
1. Install Jenkins with the *Git*, *Pipeline* and *JUnit* plugins; the agent needs `git`, `python3-venv`, `docker`
   (add the `jenkins` user to the `docker` group).
2. *New Item -> Pipeline*; Definition **Pipeline script from SCM**, SCM **Git**, your repo URL, branch `*/main`,
   script path `Jenkinsfile`.
3. Trigger: add a GitHub webhook (`http://<jenkins>/github-webhook/`) with *GitHub hook trigger*, or rely on the
   built-in `pollSCM` fallback.
4. *Build Now* - the build must finish green with the test report attached.

## API summary

| Release | Endpoints |
|---|---|
| 1.0 | `GET /`, `/health`, `/programs`, `/programs/<code>`, `/site-metrics` |
| 1.1 | `GET /programs/<code>/calories?weight=`, `POST /clients` (validation) |
| 1.1.2 | `GET /clients`, `/clients/export.csv`, `/clients/chart-data`, `/clients/chart.svg` |
| 2.0.1 | SQLite: `GET /clients/<name>`, `POST|GET /clients/<name>/progress` |
| 2.2.1 | `GET /clients/<name>/progress/chart.svg` |
| 2.2.4 | `POST|GET /clients/<name>/workouts`, `/metrics`, `/metrics/weight-chart.svg`, `GET /clients/<name>/bmi` |
| 3.1.2 | `POST /login`, `GET /me`, `POST /clients/<name>/ai-program`, `GET /clients/<name>/report.pdf` |
| 3.2.4 | `GET /clients/<name>/membership`, `POST /clients/<name>/generate-program` |

Full per-release notes: [CHANGELOG.md](CHANGELOG.md).

## Git workflow

* `main` is always releasable; every release was developed on `feature/vX.Y.Z`, merged with `--no-ff`
  and tagged `vX.Y.Z`.
* Commit messages follow Conventional Commits (`feat:`, `ci:`, `docs:`, `chore:`).
* `2.1.2` and `3.0.1` are byte-identical to `2.0.1` and `2.2.4` in the original source, so those two
  releases are version-bump commits only.

## Notes on the port from the desktop app

* Tkinter windows became JSON endpoints; matplotlib charts became dependency-free SVG endpoints
  (keeps the Docker image small).
* The login window became token authentication; passwords are hashed (the desktop app stored plain text).
* The desktop app dropped and recreated the `clients` table when the schema changed; this service migrates
  existing databases in place instead.
