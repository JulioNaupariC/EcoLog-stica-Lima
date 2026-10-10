from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.repositories.driver_reports import DriverReportStorageError
from app.services.driver_reports import DriverReportService


def test_delivery_uses_only_assigned_order_operational_fields():
    now = datetime.now(timezone.utc)
    session = Mock()
    session.get.return_value = SimpleNamespace(
        direccion="Synthetic address",
        referencia=None,
        ventana_inicio=now,
        ventana_fin=now + timedelta(hours=1),
        cliente_id=uuid4(),
        nombre="Never exported",
        telefono="Never exported",
    )
    result = DriverReportService._delivery(session, uuid4())
    assert result.model_dump() == {
        "address": "Synthetic address",
        "reference": None,
        "window_start": now,
        "window_end": now + timedelta(hours=1),
    }


def test_legacy_assignment_does_not_invent_delivery_data():
    session = Mock()
    assert DriverReportService._delivery(session, None) is None
    session.get.assert_not_called()


def test_missing_assigned_order_is_not_silently_replaced():
    session = Mock()
    session.get.return_value = None
    with pytest.raises(DriverReportStorageError):
        DriverReportService._delivery(session, uuid4())
