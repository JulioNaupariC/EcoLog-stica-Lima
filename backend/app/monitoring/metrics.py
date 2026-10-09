"""Bounded, process-local counters and histograms; no request or SQL payloads."""

from collections import defaultdict
from threading import Lock
from time import time

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)


def labels(names: tuple[str, ...], values: tuple[str, ...]) -> str:
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

    return (
        "{"
        + ",".join(f'{name}="{escape(value)}"' for name, value in zip(names, values))
        + "}"
    )


class Metrics:
    def __init__(self) -> None:
        self.lock = Lock()
        self.started = time()
        self.counters: dict[tuple[str, tuple[str, ...]], int] = defaultdict(int)
        self.active: dict[tuple[str, str], int] = defaultdict(int)
        self.histograms: dict[
            tuple[str, tuple[str, ...]], tuple[list[int], float, int]
        ] = {}
        self.db_up: int | None = None
        self.db_checked = 0.0

    def increment(self, name: str, key: tuple[str, ...]) -> None:
        with self.lock:
            self.counters[name, key] += 1

    def inflight(self, key: tuple[str, str], change: int) -> None:
        with self.lock:
            self.active[key] += change
            self.counters.setdefault(("ecolog_http_5xx_total", key), 0)

    def observe(self, name: str, key: tuple[str, ...], seconds: float) -> None:
        with self.lock:
            buckets, total, count = self.histograms.get(
                (name, key), ([0] * len(BUCKETS), 0.0, 0)
            )
            for index, limit in enumerate(BUCKETS):
                buckets[index] += int(seconds <= limit)
            self.histograms[name, key] = buckets, total + seconds, count + 1

    def database_probe(self, available: bool, seconds: float) -> None:
        self.increment(
            "ecolog_database_probes_total", ("success" if available else "error",)
        )
        self.observe("ecolog_database_probe_duration_seconds", (), seconds)
        with self.lock:
            self.db_up = int(available)
            self.db_checked = time()

    def render(self) -> str:
        dimensions = {
            "ecolog_http_requests_total": ("method", "route", "status"),
            "ecolog_http_5xx_total": ("method", "route"),
            "ecolog_http_exceptions_total": ("method", "route"),
            "ecolog_database_operations_total": ("engine", "operation", "outcome"),
            "ecolog_database_probes_total": ("outcome",),
            "ecolog_http_request_duration_seconds": ("method", "route", "status"),
            "ecolog_database_operation_duration_seconds": ("engine", "operation"),
            "ecolog_database_probe_duration_seconds": (),
        }
        lines = [
            f"ecolog_process_start_time_seconds {self.started}",
            "# TYPE ecolog_http_requests_in_flight gauge",
        ]
        with self.lock:
            for key, value in sorted(self.active.items()):
                lines.append(
                    "ecolog_http_requests_in_flight"
                    + labels(("method", "route"), key)
                    + f" {value}"
                )
            for name, names in dimensions.items():
                histogram = name.endswith("_seconds")
                lines.append(f"# TYPE {name} {'histogram' if histogram else 'counter'}")
                if histogram:
                    for (family, key), (buckets, total, count) in sorted(
                        self.histograms.items()
                    ):
                        if family != name:
                            continue
                        for limit, value in zip(BUCKETS, buckets):
                            lines.append(
                                name
                                + "_bucket"
                                + labels(names + ("le",), key + (str(limit),))
                                + f" {value}"
                            )
                        lines.append(
                            name
                            + "_bucket"
                            + labels(names + ("le",), key + ("+Inf",))
                            + f" {count}"
                        )
                        lines.append(name + "_sum" + labels(names, key) + f" {total}")
                        lines.append(name + "_count" + labels(names, key) + f" {count}")
                else:
                    for (family, key), count in sorted(self.counters.items()):
                        if family == name:
                            lines.append(name + labels(names, key) + f" {count}")
            # Absence of an observation must never mean available.
            lines.append("# TYPE ecolog_database_up gauge")
            if self.db_up is not None:
                lines.append(f"ecolog_database_up {self.db_up}")
            lines.append(
                f"ecolog_database_last_probe_timestamp_seconds {self.db_checked}"
            )
        return "\n".join(lines) + "\n"
