#!/usr/bin/env python3
"""Check sustained readiness without printing response bodies."""

import json
from pathlib import Path
import time
import urllib.request


def verify(project, *, attempts=24, interval=5, request=None, sleep=None):
    request = request or urllib.request.urlopen
    sleep = sleep or time.sleep
    endpoint = {
        "prometheus": "http://127.0.0.1:9090/-/ready",
        "loki": "http://127.0.0.1:3100/ready",
        "grafana": "http://127.0.0.1:3000/api/health",
    }[project]
    consecutive = 0
    for attempt in range(attempts):
        try:
            with request(endpoint, timeout=5) as response:
                body = response.read(4096)
                ready = response.status == 200 and (
                    project != "grafana" or json.loads(body).get("database") == "ok"
                )
            consecutive = consecutive + 1 if ready else 0
            if consecutive >= 3:
                print(project + " sustained readiness verified")
                return
        except (OSError, ValueError):
            consecutive = 0
        if attempt + 1 < attempts:
            sleep(interval)
    raise SystemExit(project + " readiness failed")


if __name__ == "__main__":
    verify(Path(__file__).resolve().parents[1].name)
