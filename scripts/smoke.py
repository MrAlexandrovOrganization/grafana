#!/usr/bin/env python3
"""Check the running central service without printing response bodies."""
import json
from pathlib import Path
import time
import urllib.request

project = Path(__file__).resolve().parents[1].name
endpoint = {"prometheus": "http://127.0.0.1:9090/-/ready",
            "loki": "http://127.0.0.1:3100/ready",
            "grafana": "http://127.0.0.1:3000/api/health"}[project]
for attempt in range(24):
    try:
        with urllib.request.urlopen(endpoint, timeout=5) as response:
            body = response.read(4096)
            if response.status == 200 and (project != "grafana" or json.loads(body).get("database") == "ok"):
                print(project + " readiness verified")
                break
    except (OSError, ValueError):
        pass
    time.sleep(5)
else:
    raise SystemExit(project + " readiness failed")
