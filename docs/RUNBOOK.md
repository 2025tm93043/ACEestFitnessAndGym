# Assignment 2 runbook - from your current repo to a running Kubernetes cluster

This file is the single, ordered checklist. Do the parts in order; every part ends with a **✅ Check**.

```
 git push ──► GitHub ──► Jenkins (polls every 2 min)
                           │ 1 checkout + lint + pytest (+coverage)
                           │ 2 SonarQube analysis ──► Quality Gate (pipeline stops if it fails)
                           │ 3 docker build + pytest INSIDE the container
                           │ 4 push image  <user>/aceest-fitness:<version>  ──► Docker Hub
                           │ 5 archive build artifacts (tar.gz, coverage, Sonar report)
                           └ 6 optional: kubectl set image  ──► Minikube
 Minikube: rolling update | blue-green | canary | shadow | A/B  (all pull from Docker Hub)
```

| Part | What | Time |
|---|---|---|
| 0 | Copy the files in, check the machine | 10 min |
| 1 | Install Docker, Minikube, kubectl | 30 min |
| 2 | Set up SonarQube | 20 min |
| 3 | Docker Hub: account, token, push every version | 30 min |
| 4 | Jenkins: plugins, credentials, new pipeline | 45 min |
| 5 | Deploy and demonstrate the 5 strategies | 60 min |
| 6 | Expose the endpoint URLs | 15 min |
| 7 | Commit the work (one branch per part) | 20 min |
| 8 | Evidence + report | 60 min |

Your Jenkins server and your Minikube machine may be different computers. The only hard rule:
**Jenkins must be able to reach SonarQube**, and (only if you use the optional Jenkins deploy stage) **the
Kubernetes API**. Everything else can be done by hand from the machine that runs Minikube.

---

## Part 0 - Prepare (no code or tag changes)

Your application code, tests and git tags stay exactly as they are. Nothing in this package edits a `.py`
file of the application or creates a tag. (Your repo has tags `v1.0, v1.1, v1.1.2, v2.0.1, v2.2.1, v2.2.4,
v3.0.1, v3.1.2, v3.2.4`; `2.1.2` was never tagged and is byte-identical to `2.0.1`, so it simply gets no
separate image.)

```bash
cd ACEestFitnessAndGym
git checkout main && git pull
git tag | sort -V
```

Copy the new files from this package into your repo (same folder structure) **without committing yet**:
`sonar-project.properties, .coveragerc, requirements-dev.txt, Jenkinsfile, .dockerignore, .gitignore, infra/,
k8s/, scripts/, docs/`. Your `Dockerfile` is **not** touched. Only the `Jenkinsfile` is replaced (it is pipeline
configuration, not application code).

---

## Part 1 - Minikube from scratch (you are new to it)

**What is what.** *Docker* runs containers. *Kubernetes* decides where containers run, restarts them,
updates them and load-balances them. *Minikube* is a one-machine Kubernetes cluster for learning. *kubectl*
is the command you type to talk to the cluster.

Words you will see: **Pod** = one running container; **Deployment** = "keep N pods of image X running";
**Service** = a stable address (and load balancer) in front of pods; **Namespace** = a folder inside the
cluster (we use `aceest`); **NodePort** = a port opened on the cluster machine.

### 1.1 Check the machine

```bash
free -h            # SonarQube needs ~2.5 GB, Minikube ~3 GB: plan for 8 GB total if both run here
nproc              # at least 2 CPUs
df -h /            # at least 20 GB free
```

### 1.2 Install Docker (Rocky Linux / RHEL family; needs sudo)

```bash
sudo dnf install -y git curl gettext          # gettext provides 'envsubst', used by scripts/k8s-deploy.sh
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
newgrp docker                                  # or log out and back in
docker run --rm hello-world
```

Ubuntu/Debian: `sudo apt install -y docker.io docker-compose-v2 git curl gettext-base`.
No sudo on the lab machine? Ask for Docker access, or use Podman (`podman` is a drop-in replacement; see Part 4).

✅ **Check:** `docker run --rm hello-world` prints "Hello from Docker!".

### 1.3 Install kubectl and Minikube

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl && rm kubectl

curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
```

No sudo? `mkdir -p ~/bin && install kubectl minikube-linux-amd64 ~/bin/` (rename the minikube file to
`minikube`) and make sure `~/bin` is in your `PATH`.

### 1.4 Start the cluster

```bash
minikube start --driver=docker --cpus=2 --memory=3072
kubectl get nodes
kubectl get pods -A
```

Run this as a **normal user, not root** (Minikube refuses the docker driver as root).
First start downloads images, so allow a few minutes.

✅ **Check:** `kubectl get nodes` shows `minikube   Ready`.

### 1.5 Five commands you will use constantly

```bash
kubectl -n aceest get pods -o wide          # what is running and which node
kubectl -n aceest get deploy,svc            # deployments and services
kubectl -n aceest describe pod <name>       # why is a pod unhappy? read the "Events" at the bottom
kubectl -n aceest logs deploy/<name>        # application log
minikube ip                                 # address of the cluster (used with NodePorts, e.g. http://$(minikube ip):30081)
```

Stop / start later: `minikube stop` and `minikube start`. Delete everything: `minikube delete`.

---

## Part 2 - SonarQube

### 2.1 Start it (Docker Compose file is in `infra/sonarqube/`)

SonarQube embeds Elasticsearch, which refuses to start unless this kernel setting is raised:

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee /etc/sysctl.d/99-sonarqube.conf     # survives reboots
docker compose -f infra/sonarqube/docker-compose.yml up -d
docker compose -f infra/sonarqube/docker-compose.yml logs -f sonarqube       # wait for "SonarQube is operational", Ctrl+C
curl -s http://localhost:9000/api/system/status                                # {"status":"UP",...}
```

Open `http://<this-machine-ip>:9000` (port 9000 must be reachable from Jenkins and your browser).
Log in `admin` / `admin`, set a new password.

### 2.2 Create a token for Jenkins

SonarQube UI → top-right avatar → **My Account → Security → Generate Tokens** → name `jenkins`,
type **User Token** → **copy it now** (shown once).

### 2.3 Tell SonarQube to call Jenkins when analysis finishes (needed for the Quality Gate stage)

**Administration → Configuration → Webhooks → Create**: name `jenkins`,
URL `http://<jenkins-host>:8080/sonarqube-webhook/` (keep the trailing slash).

✅ **Check:** the SonarQube home page loads and you hold a token. (The project itself appears after the first
Jenkins analysis.)

*Optional dry run before touching Jenkins (any machine with Docker):*

```bash
docker run --rm -e SONAR_HOST_URL=http://<sonar-ip>:9000 -e SONAR_TOKEN=<token> \
  -v "$PWD:/usr/src" sonarsource/sonar-scanner-cli
```

---

## Part 3 - Docker Hub: every version of the application

1. Create an account at https://hub.docker.com.
2. **Account Settings → Personal access tokens → Generate** (Read & Write). Keep it.
3. Create a **public** repository named `aceest-fitness` (Repositories → Create).
4. Push all released versions (builds one image per git tag):

```bash
echo "<docker-hub-token>" | docker login -u <your-docker-hub-user> --password-stdin
export DOCKERHUB_USER=<your-docker-hub-user>
DRY_RUN=1 scripts/push-all-versions.sh        # preview the commands
scripts/push-all-versions.sh                   # builds + pushes one image per existing tag and :latest
```

Old tags that pre-date the Dockerfile are built with your current Dockerfile (copied in temporarily; your
repo is not modified), which works because every tag contains `app.py`, `requirements.txt` and the tests.

✅ **Check:** https://hub.docker.com/r/<user>/aceest-fitness/tags lists `1.0, 1.1, 1.1.2, 2.0.1, 2.2.1, 2.2.4,
3.0.1, 3.1.2, 3.2.4, latest` (one image per existing git tag). 📸 Screenshot this page (required: "your own docker image repo with all
versions").

Test one image locally: `docker run --rm -p 5000:5000 $DOCKERHUB_USER/aceest-fitness:3.2.4` then
`curl localhost:5000/health`.

---

## Part 4 - Jenkins

You already have a Jenkins server. Use **Manage Jenkins** for everything below.

### 4.1 Plugins (Manage Jenkins → Plugins → Available)

Install **SonarQube Scanner**. Make sure these exist (they come with "suggested plugins"): Pipeline, Git,
JUnit, Credentials Binding. Restart Jenkins if asked.

### 4.2 Credentials (Manage Jenkins → Credentials → System → Global → Add Credentials)

| Kind | ID (exactly) | Content |
|---|---|---|
| Secret text | `sonar-token` | the SonarQube token from 2.2 |
| Username with password | `dockerhub-creds` | Docker Hub username + **access token** as password |
| Secret file (optional, only for Jenkins deploy) | `kubeconfig` | output of `kubectl config view --raw --flatten > kubeconfig` |

### 4.3 SonarQube server (Manage Jenkins → System → SonarQube servers → Add)

Name **`sonarqube`** (exactly), Server URL `http://<sonar-host>:9000` (not `localhost` if Jenkins runs in a
container or on another machine), token = `sonar-token`.

### 4.4 Scanner tool (Manage Jenkins → Tools → SonarQube Scanner installations → Add)

Name **`SonarScanner`** (exactly), tick **Install automatically** (needs internet from Jenkins).

### 4.5 What the Jenkins machine needs

```bash
git --version ; python3 -m venv --help | head -1 ; docker --version
```

If `docker` fails with *permission denied on /var/run/docker.sock* (you met this in Assignment 1):

```bash
sudo usermod -aG docker jenkins && sudo systemctl restart jenkins          # Jenkins installed on the host
docker exec -u root jenkins chmod 666 /var/run/docker.sock                  # Jenkins in a container
```

**Podman instead of Docker?** Install podman on the agent and set `CONTAINER_CLI = 'podman'` in the
`Jenkinsfile` `environment` block (and `export CONTAINER_CLI=podman` for the scripts). The Dockerfile is
OCI-compatible; note Podman ignores the `HEALTHCHECK` line unless you build with `--format docker`.

### 4.6 The job

Keep your existing Pipeline job (Pipeline script from SCM, repo
`https://github.com/<you>/ACEestFitnessAndGym.git`, branch `*/main`, script path `Jenkinsfile`). The new
`Jenkinsfile` already contains `pollSCM('H/2 * * * *')`, so Jenkins checks GitHub every ~2 minutes and builds on
any new commit. After the first run a **Build with Parameters** button appears: `RUN_SONAR`, `PUSH_IMAGE`,
`DEPLOY`.

### 4.7 First run order (so the first builds are green)

1. Merge the Sonar branch and the Jenkinsfile branch (Part 7) - Jenkins builds automatically.
2. If SonarQube is not ready yet, run **Build with Parameters** with `RUN_SONAR` off, to prove everything else.
3. When SonarQube is ready, run again with `RUN_SONAR` on.

✅ **Check:** the Stage View shows Clean → Checkout → Setup → Lint → Unit Tests + Coverage → SonarQube Analysis →
Quality Gate → SonarQube Report → Docker Build → Tests in Container → Push to Docker Hub → Build Artifacts, all green;
the build page lists artifacts (`dist/aceest-fitness-<version>.tar.gz`, `reports/sonarqube-report.md`, …); the
image tag `<version>` appears on Docker Hub. 📸 Screenshots: Stage View, SonarQube dashboard (project
`aceest-fitness`, quality gate **Passed**), test result trend.

**If the Quality Gate fails** (it is a real gate): open the project in SonarQube → *Issues* / *Security Hotspots*.
Typical first-run findings in this code base are hard-coded default passwords (`admin`, the dev secret key) and
cognitive-complexity notes in `app.py`. Fix real issues in code; for hotspots that are intentional demo
defaults, open the hotspot → **Review** → *Safe* with a comment. Then re-run. Keep the failed and the fixed run
as evidence of the gate working.

---

## Part 5 - Deploy and demonstrate the strategies on Minikube

Two versions are used so the difference is visible: `V_OLD=2.2.4` (stable) and `V_NEW=3.2.4` (new).
`/health` answers `{"status":"ok","version":"<x>"}`, so the version tells you who answered.

```bash
export DOCKERHUB_USER=<your-docker-hub-user>
export V_OLD=2.2.4 V_NEW=3.2.4
export ACEEST_ADMIN_PASSWORD='choose-one'        # optional, goes into a Kubernetes Secret (never into git)
DRY_RUN=1 scripts/k8s-deploy.sh all | head -40   # preview the rendered YAML
scripts/k8s-deploy.sh all                         # or one at a time: rolling-update | blue-green | canary | shadow | ab-testing
kubectl -n aceest get pods -w                     # wait until all are 1/1 Running, Ctrl+C
```

Ports: rolling **30081**, blue-green **30082** (+ green preview **30086**), canary **30083**, shadow **30084**,
A/B **30085**. From the Minikube machine use `http://$(minikube ip):<port>`; Part 6 makes them reachable from
outside.

```bash
IP=$(minikube ip)
```

### 5.1 Rolling update (zero downtime + rollback)

4 pods of `V_OLD`, `maxUnavailable: 0`, `maxSurge: 1`: Kubernetes adds a new pod, waits for its readiness
probe, only then removes an old one.

```bash
scripts/test-endpoint.sh http://$IP:30081 10                       # all 2.2.4
# terminal 2: prove there is no downtime during the update
while true; do curl -s -o /dev/null -w "%{http_code} " http://$IP:30081/health; sleep 0.3; done
# terminal 1: upgrade, watch pods get replaced one by one
scripts/rolling-update.sh update 3.2.4
kubectl -n aceest get pods -w
scripts/test-endpoint.sh http://$IP:30081 10                       # all 3.2.4, terminal 2 only printed 200
scripts/rolling-update.sh rollback                                 # revert to the previous revision
scripts/rolling-update.sh status                                   # revision history
```

**Failure + automatic revert demo:** `scripts/rolling-update.sh update 9.9.9` (a tag that does not exist).
The new pod sits in `ImagePullBackOff`, the old pods keep serving (nothing was removed), the script times out
after 120 s and runs `kubectl rollout undo` by itself. 📸 Screenshot the output.

> Don't re-run `k8s-deploy.sh rolling-update` after an update: it re-applies the manifest and resets the image
> to `V_OLD` (the same applies to the blue-green and canary manifests).

### 5.2 Blue-Green

Blue (`V_OLD`) is live, green (`V_NEW`) is deployed next to it with its own preview port.

```bash
curl http://$IP:30082/health        # live  -> 2.2.4 (blue)
curl http://$IP:30086/health        # green preview -> 3.2.4  (test it BEFORE going live)
scripts/bluegreen-switch.sh green   # one-line cut-over: the Service selector now points at green
curl http://$IP:30082/health        # live  -> 3.2.4
scripts/bluegreen-switch.sh blue    # instant rollback
curl http://$IP:30082/health        # live  -> 2.2.4
```

### 5.3 Canary release

1 canary pod (`V_NEW`) + 4 stable pods (`V_OLD`) behind one Service → about 20 % of requests hit the canary.

```bash
scripts/test-endpoint.sh http://$IP:30083 50      # ≈ 40 x 2.2.4, ≈ 10 x 3.2.4
scripts/canary.sh weight 4                         # 4 canary + 4 stable → ≈ 50 %
scripts/test-endpoint.sh http://$IP:30083 50
scripts/canary.sh promote                          # looks good: stable takes V_NEW, canary removed
# or, if it looks bad:  scripts/canary.sh abort    # rollback: canary scaled to 0
```

### 5.4 Shadow deployment

An nginx router sends every request to the live version **and silently mirrors a copy to the shadow
version**; the shadow's response is thrown away, so users are unaffected.

```bash
curl -i http://$IP:30084/health                    # answered by live (2.2.4), header X-Served-By: live
curl -s -X POST http://$IP:30084/login -H 'Content-Type: application/json' \
     -d '{"username":"admin","password":"x"}'     # old live version has no /login → 404 to the user …
kubectl -n aceest logs deploy/aceest-shadow --tail=5   # … but the shadow (3.2.4) saw the mirrored request
```

### 5.5 A/B testing

Router splits users 50/50 by client (IP + browser) and keeps each user on the same variant; testers can force a
variant.

```bash
scripts/test-endpoint.sh http://$IP:30085 40 ua            # ≈ 20 x 2.2.4 (A), ≈ 20 x 3.2.4 (B)
scripts/test-endpoint.sh http://$IP:30085 5 hdr B           # header  X-Variant: B  → always 3.2.4
curl -s -b "variant=A" http://$IP:30085/health              # cookie forces variant A
curl -si http://$IP:30085/health | grep -i x-variant        # which group you were assigned
```

✅ **Check:** each of the five demos printed the expected versions. 📸 Take one screenshot per strategy
(commands + output) and one of `kubectl -n aceest get deploy,svc,pods`.

### 5.6 Optional: deploy from Jenkins

Needs `kubectl` on the Jenkins agent, the `kubeconfig` credential, and the Minikube API reachable from Jenkins.
Run the job with `DEPLOY=rolling-update`; the stage runs `kubectl set image`, waits for the rollout, and runs
`rollout undo` if it fails. If Jenkins cannot reach Minikube, skip this and use `scripts/rolling-update.sh`.

---

## Part 6 - Endpoint URLs for the submission

The assignment asks for the URL of your running cluster. On Linux with the docker driver the Minikube network
is private to the host, so forward the ports to the host:

```bash
scripts/expose.sh start                # prints the five URLs, e.g. http://10.3.27.9:8081 … :8085
sudo firewall-cmd --add-port=8081-8085/tcp --permanent && sudo firewall-cmd --reload   # Rocky/RHEL
curl http://<host-ip>:8083/health      # test from ANOTHER machine
scripts/expose.sh stop
```

If graders cannot reach your lab network, say so in the report and add the screenshots; as an optional extra, a
tunnel (`cloudflared tunnel --url http://localhost:8083` or `ngrok http 8083`) gives a temporary public URL.
The cluster must still be running when the work is evaluated.

---

## Part 7 - Commit the work (one branch + PR per part, descriptive messages)

```bash
git checkout main && git pull

git checkout -b ci/sonarqube
git add sonar-project.properties .coveragerc requirements-dev.txt .gitignore infra/ scripts/sonar_report.py
git commit -m "ci: add SonarQube config, coverage report and quality-gate report script"
git push -u origin ci/sonarqube                        # open PR, wait for GitHub Actions, merge

git checkout main && git pull && git checkout -b ci/jenkins-pipeline
git add Jenkinsfile .dockerignore
git commit -m "ci: Jenkins pipeline with SonarQube gate, Docker Hub push and build artifacts"
git push -u origin ci/jenkins-pipeline                 # PR + merge  (Jenkins builds it - do Part 4 first!)

git checkout main && git pull && git checkout -b ci/dockerhub-versions
git add scripts/push-all-versions.sh
git commit -m "ci: script to publish every released version to Docker Hub"
git push -u origin ci/dockerhub-versions               # PR + merge

git checkout main && git pull && git checkout -b infra/kubernetes
git add k8s/ scripts/k8s-deploy.sh scripts/rolling-update.sh scripts/bluegreen-switch.sh \
        scripts/canary.sh scripts/test-endpoint.sh scripts/expose.sh
git commit -m "infra: Kubernetes manifests and scripts for rolling, blue-green, canary, shadow and A/B"
git push -u origin infra/kubernetes                    # PR + merge

git checkout main && git pull && git checkout -b docs/assignment-2
cat docs/README-assignment2.md >> README.md
git add docs/ README.md
git commit -m "docs: Assignment 2 runbook, report and README section"
git push -u origin docs/assignment-2                   # PR + merge
```

Order matters: **configure Jenkins (Part 4) before merging the Jenkinsfile PR**, otherwise that first build
fails on the Sonar stage. A failed build followed by a fix is fine as evidence, but the *latest* builds must be
green when you submit.

---

## Part 8 - Evidence and report

Create `docs/evidence/` and commit: Jenkins Stage View + build history, SonarQube dashboard +
`sonarqube-report.md` (download from the build's Artifacts), Docker Hub tags page, one screenshot per strategy,
`kubectl get deploy,svc,pods`. Then fill in `docs/REPORT.md` (2-3 pages; export to Word/PDF:
`pandoc docs/REPORT.md -o ACEest-Assignment2-Report.docx`).

### Submission checklist (from the assignment)

- [ ] GitHub repo public, with Flask code + the existing version tags, `Jenkinsfile`, `Dockerfile`, `k8s/` manifests, tests
- [ ] SonarQube report (`docs/evidence/`) and quality-gate screenshot
- [ ] Jenkins: successful runs for the most recent commits
- [ ] Docker Hub repo with all versions (link)
- [ ] Endpoint URL(s) of the running cluster covering rolling, blue-green, canary, shadow, A/B (+ rollback shown)
- [ ] Report, 2-3 pages: architecture, challenges + mitigation, automation outcomes

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| SonarQube container exits, log mentions `max virtual memory areas` | run the `sysctl` in 2.1, then `docker compose ... up -d` again |
| Jenkins stage *Quality Gate* waits 10 min then fails | the Sonar webhook (2.3) is missing or the URL is wrong; test it from SonarQube → Webhooks → *last delivery* |
| `No such tool: SonarScanner` | tool name in 4.4 must be exactly `SonarScanner` |
| `No such server: sonarqube` | server name in 4.3 must be exactly `sonarqube` |
| `docker: permission denied` in Jenkins | step 4.5 |
| Pods `ImagePullBackOff` | wrong `DOCKERHUB_USER`, tag not pushed, or repo private; `kubectl -n aceest describe pod <pod>` shows the exact image |
| Pods `CreateContainerConfigError` | secret missing: `kubectl -n aceest get secret aceest-secrets` (script creates it) |
| `curl: connection refused` on `$(minikube ip):30081` | `minikube status`; with a non-Linux host use `minikube service aceest-rolling -n aceest --url` |
| `envsubst: command not found` | `sudo dnf install -y gettext` |
| Data differs between pods | each pod has its own SQLite file (`emptyDir`); fine for the demo, mention it in the report as a limitation (production would use a database service) |
| Start over cleanly | `kubectl delete namespace aceest` then redeploy |
