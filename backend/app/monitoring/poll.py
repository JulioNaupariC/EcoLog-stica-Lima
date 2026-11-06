"""External availability observation: python -m app.monitoring.poll --samples 1."""

import argparse
import json
import os
from datetime import datetime, timezone
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

# ECL-66 / A01:2025 (SSRF): the probe only reaches the local API by default.
# Another monitored origin must be listed explicitly by the operator.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
ALLOWED_HOSTS_ENV = "MONITOR_ALLOWED_HOSTS"
INTERRUPTED = 130


def allowed_hosts() -> frozenset[str]:
    extra = os.environ.get(ALLOWED_HOSTS_ENV, "")
    return LOOPBACK_HOSTS | {
        host.strip().lower() for host in extra.split(",") if host.strip()
    }


SCHEMES = ("http", "https")
DEFAULT_PORTS = {"http": 80, "https": 443}


def safe_origin(url: str) -> str | None:
    """ECL-84 / S8703: rebuild the origin from trusted values only.

    The scheme comes from ``SCHEMES``, the host from the allowlist itself and
    the port is an integer, so no character typed after ``--url`` reaches
    ``urlopen``. Returns ``None`` for anything that is not a bare HTTP(S)
    origin of an allowed host.
    """
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or not parsed.hostname
    ):
        return None
    scheme = next((s for s in SCHEMES if s == parsed.scheme), None)
    host = next(
        (h for h in sorted(allowed_hosts()) if h == parsed.hostname.lower()), None
    )
    if scheme is None or host is None:
        return None
    netloc = f"[{host}]" if ":" in host else host
    port_number = int(port) if port is not None else DEFAULT_PORTS[scheme]
    return f"{scheme}://{netloc}:{port_number}"


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
    if args.interval <= 0 or args.samples < 0:
        parser.error("Use a positive interval and a non-negative sample count")
    url = safe_origin(args.url.rstrip("/"))
    if url is None:
        parser.error(
            "Use an HTTP(S) origin without credentials or path whose host is "
            f"allowed (list it in {ALLOWED_HOSTS_ENV})"
        )
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
        return INTERRUPTED
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
