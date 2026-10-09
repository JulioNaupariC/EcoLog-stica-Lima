"""Guard acceptance against falsely green load reports."""

from collections import Counter

import pytest

from loadtest.analysis import (
    HOURLY,
    availability_slots,
    concurrency_summary,
    percentile,
    schedule,
    summarize,
)


def attempt(status=201, valid=True, identifier="order", seconds=1):
    return {
        "status": status,
        "valid": valid,
        "pedido_id": identifier,
        "seconds": seconds,
        "cliente_id": "client",
        "reference": "reference",
    }


def test_seeded_daily_profile_exact_counts_and_hours():
    rows = schedule(35061)
    assert len(rows) == 1000
    assert rows == schedule(35061)
    assert rows != schedule(1)
    assert Counter(row["hour"] for row in rows) == dict(enumerate(HOURLY, 5))
    assert all(
        (row["hour"] - 5) * 3600 <= row["day_seconds"] < (row["hour"] - 4) * 3600
        for row in rows
    )
    assert rows == sorted(rows, key=lambda row: row["day_seconds"])


def test_p95_nearest_rank_and_empty_population():
    assert percentile(list(range(1, 101))) == 95
    assert percentile([2, 1]) == 2
    assert percentile([]) is None
    assert percentile([1, 2], 1) == 2
    with pytest.raises(ValueError):
        percentile([1], 0)


def test_5xx_denominator_includes_4xx_but_excludes_transport():
    rows = [attempt(), attempt(503, False), attempt(403, False), attempt(None, False)]
    result = summarize(rows, {"order": ("client", "reference")})
    assert result["http_responses"] == 3
    assert result["http_5xx_percent"] == pytest.approx(100 / 3)
    assert result["without_response"] == 1
    assert result["functional_or_transport_errors"] == 2
    assert result["unique_valid_persisted"] == 1
    assert result["http_5xx_threshold_pass"] is False


@pytest.mark.parametrize(
    "persisted",
    [
        {},
        {"order": ("other", "reference")},
        {"order": ("client", "other")},
    ],
)
def test_201_requires_matching_persisted_identity(persisted):
    result = summarize([attempt()], persisted)
    assert result["persistence_discrepancies"] == 1
    assert result["p95_valid_seconds"] is None
    assert not result["p95_threshold_pass"]


def test_duplicate_uuid_is_not_counted_twice():
    result = summarize([attempt(), attempt()], {"order": ("client", "reference")})
    assert result["unique_valid_persisted"] == 1
    assert result["persistence_discrepancies"] == 1


@pytest.mark.parametrize("latency,passed", [(2, True), (2.0001, False)])
def test_p95_boundary(latency, passed):
    result = summarize([attempt(seconds=latency)], {"order": ("client", "reference")})
    assert result["p95_threshold_pass"] is passed


def test_one_percent_5xx_is_failure_and_zero_traffic_not_success():
    result = summarize([attempt(503, False)] + [attempt(400, False)] * 99, {})
    assert result["http_5xx_percent"] == 1
    assert not result["http_5xx_threshold_pass"]
    assert summarize([], {})["http_5xx_percent"] is None
    assert not summarize([], {})["http_5xx_threshold_pass"]


def test_fast_error_not_part_of_valid_p95():
    result = summarize(
        [attempt(seconds=3), attempt(503, False, seconds=0.01)],
        {"order": ("client", "reference")},
    )
    assert result["p95_valid_seconds"] == 3


def sample(offset, inflight=100, seconds=0.1):
    return {"stable_offset": offset, "inflight": inflight, "scrape_seconds": seconds}


def test_concurrency_complete_series_passes():
    result = concurrency_summary([sample(i) for i in range(10)], 10)
    assert result["sustained_100_pass"]
    assert result["minimum"] == 100


@pytest.mark.parametrize(
    "samples",
    [
        [sample(0)],
        [sample(0), sample(1, 99)],
        [sample(0), sample(1, None)],
        [sample(0), sample(1, 100, 6)],
        [sample(-1), sample(0), sample(2)],
        [sample(0), sample(0.2)],
        [],
    ],
)
def test_missing_low_slow_duplicate_or_out_of_window_samples_cannot_pass(samples):
    assert not concurrency_summary(samples, 2)["sustained_100_pass"]


def observation(second, state="AVAILABLE"):
    return {"timestamp": f"2026-10-09T09:00:{second:02}+00:00", "state": state}


def test_availability_deduplicates_catch_up_and_keeps_missing_slots():
    result = availability_slots(
        [observation(0), observation(2), observation(2), observation(3)]
    )
    assert result["expected_slots"] == 4
    assert result["observed_slots"] == 3
    assert result["duplicate_samples"] == 1
    assert result["missing_slots"] == 1
    assert result["conservative_available_percent"] == 75


def test_any_failed_probe_in_same_slot_is_conservatively_unavailable():
    result = availability_slots(
        [observation(0), observation(0, "UNAVAILABLE"), observation(1)]
    )
    assert result["available_slots"] == result["unavailable_slots"] == 1
    assert result["conservative_available_percent"] == 50


def test_empty_availability_is_not_one_hundred_percent():
    assert availability_slots([])["conservative_available_percent"] is None
    with pytest.raises(ValueError):
        availability_slots([], 0)


def test_availability_rejects_time_before_origin():
    with pytest.raises(ValueError):
        availability_slots([observation(2), observation(1)])
