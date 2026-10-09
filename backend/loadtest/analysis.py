"""Deterministic calculations, independent of the load generator."""

import math
import random
from collections import Counter
from datetime import datetime

HOURLY = (20, 30, 45, 65, 80, 90, 100, 110, 100, 90, 80, 70, 50, 30, 20, 15, 5)


def schedule(seed: int) -> list[dict]:
    rng = random.Random(seed)
    return sorted(
        (
            {"hour": hour + 5, "day_seconds": hour * 3600 + rng.random() * 3600}
            for hour, count in enumerate(HOURLY)
            for _ in range(count)
        ),
        key=lambda item: item["day_seconds"],
    )


def percentile(values: list[float], fraction: float = 0.95) -> float | None:
    if not values:
        return None
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    return sorted(values)[math.ceil(fraction * len(values)) - 1]


def summarize(attempts: list[dict], persisted: dict[str, tuple[str, str]]) -> dict:
    statuses = Counter(str(row["status"]) for row in attempts)
    responses = sum(row["status"] is not None for row in attempts)
    errors = sum(
        row["status"] is not None and 500 <= row["status"] < 600 for row in attempts
    )
    seen = set()
    valid = []
    discrepancies = 0
    for row in attempts:
        identifier = row.get("pedido_id")
        if row["valid"]:
            if identifier in seen or persisted.get(identifier) != (
                row["cliente_id"],
                row["reference"],
            ):
                discrepancies += 1
            else:
                seen.add(identifier)
                valid.append(row["seconds"])
    invalid = sum(
        not row["valid"]
        and not (row["status"] is not None and 500 <= row["status"] < 600)
        for row in attempts
    )
    p95 = percentile(valid)
    rate = 100 * errors / responses if responses else None
    return {
        "attempts": len(attempts),
        "http_responses": responses,
        "http_statuses": dict(statuses),
        "http_5xx": errors,
        "http_5xx_percent": rate,
        "without_response": len(attempts) - responses,
        "functional_or_transport_errors": invalid,
        "persistence_discrepancies": discrepancies,
        "unique_valid_persisted": len(valid),
        "p95_valid_seconds": p95,
        "p95_responded_seconds": percentile(
            [row["seconds"] for row in attempts if row["status"] is not None]
        ),
        "p95_threshold_pass": p95 is not None and p95 <= 2,
        "http_5xx_threshold_pass": rate is not None and rate < 1,
    }


def concurrency_summary(samples: list[dict], stable_seconds: int) -> dict:
    # Missing or slow scrapes never count as evidence of concurrency.
    slots: dict[int, int] = {}
    for row in samples:
        slot = math.floor(row["stable_offset"])
        if 0 <= slot < stable_seconds and row.get("scrape_seconds", 6) <= 5:
            if row.get("inflight") is not None:
                slots[slot] = row["inflight"]
    reached = sum(value >= 100 for value in slots.values())
    return {
        "expected_seconds": stable_seconds,
        "observed_seconds": len(slots),
        "missing_seconds": stable_seconds - len(slots),
        "minimum": min(slots.values()) if slots else None,
        "maximum": max(slots.values()) if slots else None,
        "seconds_at_least_100": reached,
        "percent_seconds_at_least_100": 100 * reached / stable_seconds,
        "sustained_100_pass": reached == stable_seconds,
    }


def availability_slots(observations: list[dict], interval: float = 1) -> dict:
    """Deduplicate catch-up probes; gaps never become available slots."""
    if interval <= 0:
        raise ValueError("interval must be positive")
    if not observations:
        return {
            "expected_slots": 0,
            "observed_slots": 0,
            "available_slots": 0,
            "unavailable_slots": 0,
            "missing_slots": 0,
            "duplicate_samples": 0,
            "conservative_available_percent": None,
            "observation_coverage_percent": None,
        }
    origin = datetime.fromisoformat(observations[0]["timestamp"])
    slots: dict[int, bool] = {}
    for row in observations:
        elapsed = (datetime.fromisoformat(row["timestamp"]) - origin).total_seconds()
        slot = math.floor(elapsed / interval + 0.5)
        if slot < 0:
            raise ValueError("observation precedes origin")
        slots[slot] = slots.get(slot, True) and row["state"] == "AVAILABLE"
    expected = max(slots) + 1
    available = sum(slots.values())
    return {
        "expected_slots": expected,
        "observed_slots": len(slots),
        "available_slots": available,
        "unavailable_slots": len(slots) - available,
        "missing_slots": expected - len(slots),
        "duplicate_samples": len(observations) - len(slots),
        "conservative_available_percent": 100 * available / expected,
        "observation_coverage_percent": 100 * len(slots) / expected,
    }
