#!/usr/bin/env python3
"""Download the SonarQube result for the project and save it as a report.

Usage:
    SONAR_HOST_URL=http://host:9000 SONAR_AUTH_TOKEN=xxx \
        python scripts/sonar_report.py [out_dir]

Writes <out_dir>/sonarqube-report.json and <out_dir>/sonarqube-report.md
(default out_dir=reports).
Standard library only, so it runs on any Jenkins agent.
"""
import base64
import json
import os
import sys
import urllib.parse
import urllib.request

PROJECT_KEY = os.environ.get("SONAR_PROJECT_KEY", "aceest-fitness")
METRICS = [
    "alert_status", "bugs", "vulnerabilities", "security_hotspots", "code_smells",
    "coverage", "duplicated_lines_density", "ncloc", "reliability_rating",
    "security_rating", "sqale_rating",
]


def get(host, token, path, **params):
    url = f"{host.rstrip('/')}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url)
    auth = base64.b64encode(f"{token}:".encode()).decode()
    request.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect(host, token, project=PROJECT_KEY):
    measures = get(host, token, "/api/measures/component",
                   component=project, metricKeys=",".join(METRICS))
    gate = get(host, token, "/api/qualitygates/project_status", projectKey=project)
    values = {m["metric"]: m.get("value") for m in measures["component"]["measures"]}
    return {"project": project, "quality_gate": gate["projectStatus"], "measures": values}


def to_markdown(report):
    status = report["quality_gate"]["status"]
    lines = [f"# SonarQube report - {report['project']}", "",
             f"**Quality gate: {status}**", "",
             "| Metric | Value |", "|---|---|"]
    for key in METRICS:
        lines.append(f"| {key} | {report['measures'].get(key, 'n/a')} |")
    conditions = report["quality_gate"].get("conditions", [])
    if conditions:
        lines += ["", "## Gate conditions", "",
                  "| Metric | Status | Actual | Threshold |", "|---|---|---|---|"]
        for c in conditions:
            lines.append(f"| {c['metricKey']} | {c['status']} | {c.get('actualValue', '')} "
                         f"| {c.get('errorThreshold', '')} |")
    return "\n".join(lines) + "\n"


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else "reports"
    host = os.environ["SONAR_HOST_URL"]
    token = os.environ["SONAR_AUTH_TOKEN"]
    report = collect(host, token)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "sonarqube-report.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    with open(os.path.join(out_dir, "sonarqube-report.md"), "w", encoding="utf-8") as handle:
        handle.write(to_markdown(report))
    print(f"SonarQube quality gate: {report['quality_gate']['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
