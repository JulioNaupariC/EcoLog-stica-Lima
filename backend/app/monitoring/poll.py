"""External availability observation: python -m app.monitoring.poll --samples 1."""

import argparse
import json
from datetime import datetime, timezone
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


def check(url: str) -> dict[str, object]:
    started = monotonic()
    status = None
    result = None
    try:
        with urlopen(url, timeout=5) as response:
            status = response.status
            result = json.loads(response.read(4096))
        ok = status == 200 and isinstance(result, dict) and result.get("status") == "ok"
        if url.endswith("/health/ready"):
            ok = ok and result.get("database") == "up"
    except HTTPError as error:
        status = error.code
        ok = False
    except (URLError, TimeoutError, OSError, ValueError):
        ok = False
    elapsed = monotonic() - started
    return {
        "http_status": status,
        "latency_seconds": elapsed,
        "available": ok and elapsed <= 5,
    }


def sample(base_url: str) -> dict[str, object]:
    timestamp = datetime.now(timezone.utc).isoformat()
    api = check(base_url + "/health")
    database = check(base_url + "/health/ready")
    return {
        "timestamp": timestamp,
        "api": api,
        "database": database,
        "state": "AVAILABLE"
        if api["available"] and database["available"]
        else "UNAVAILABLE",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--samples", type=int, default=0, help="0: continuous")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
        or args.interval <= 0
        or args.samples < 0
    ):
        parser.error("Use an HTTP(S) origin without credentials and positive interval")
    count = 0
    deadline = monotonic()
    try:
        while args.samples == 0 or count < args.samples:
            print(json.dumps(sample(url)), flush=True)
            count += 1
            if args.samples and count >= args.samples:
                break
            deadline += args.interval
            sleep(max(0, deadline - monotonic()))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
