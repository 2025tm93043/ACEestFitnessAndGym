
## Assignment 2 - CI/CD to Kubernetes

The same code base (tags `v1.0` … `v3.2.4`) is delivered through a full pipeline:

```
GitHub ─► Jenkins (SCM polling) ─► lint ─► pytest + coverage ─► SonarQube + quality gate
        ─► docker build ─► pytest inside the container ─► Docker Hub (<user>/aceest-fitness:<version>)
        ─► build artifacts ─► Kubernetes (Minikube): rolling | blue-green | canary | shadow | A/B
```

| Item | Where |
|---|---|
| Pipeline definition | `Jenkinsfile` |
| SonarQube config / local server | `sonar-project.properties`, `infra/sonarqube/docker-compose.yml` |
| Container image (multi-stage, non-root) | `Dockerfile` |
| Publish every version to Docker Hub | `scripts/push-all-versions.sh` |
| Kubernetes manifests | `k8s/` (`rolling-update`, `blue-green`, `canary`, `shadow`, `ab-testing`) |
| Deploy / switch / rollback helpers | `scripts/` |
| Step-by-step setup and demo guide | [`docs/RUNBOOK.md`](docs/RUNBOOK.md) |
| Report | [`docs/REPORT.md`](docs/REPORT.md) |

### Deployment strategies (namespace `aceest`)

| Strategy | Port | How it works | Rollback |
|---|---|---|---|
| Rolling update | 30081 | `RollingUpdate`, `maxUnavailable: 0`, readiness probe | `scripts/rolling-update.sh rollback` (automatic if the rollout fails) |
| Blue-Green | 30082 | two Deployments, Service selector switched | `scripts/bluegreen-switch.sh blue` |
| Canary | 30083 | 1 canary + 4 stable pods behind one Service (~20 %) | `scripts/canary.sh abort` |
| Shadow | 30084 | nginx `mirror` copies traffic to the new version, response discarded | remove the shadow Deployment |
| A/B testing | 30085 | nginx `split_clients` 50/50 + `X-Variant` header / cookie override | remove variant B |

Quick start: `export DOCKERHUB_USER=<user>; scripts/k8s-deploy.sh all` (see the runbook for prerequisites).
