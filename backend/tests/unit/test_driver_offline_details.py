from datetime import datetime, timedelta, timezone
from struct import pack
from unittest.mock import Mock
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKBElement
from sqlalchemy.exc import SQLAlchemyError

from app.models.pedido import Pedido
from app.repositories.driver_reports import DriverReportStorageError
from app.services.driver_reports import DriverReportService


def test_delivery_uses_only_assigned_order_operational_fields():
    now = datetime.now(timezone.utc)
    session = Mock()
    session.get.return_value = Pedido(
        direccion="Synthetic address",
        referencia=None,
        ventana_inicio=now,
        ventana_fin=now + timedelta(hours=1),
        ubicacion=WKBElement(pack("<BIdd", 1, 1, -77.0428, -12.0464), srid=4326),
        cliente_id=uuid4(),
    )
    session.execute.return_value.one.return_value = (-12.0464, -77.0428)
    pedido_id = uuid4()
    result = DriverReportService._delivery(session, pedido_id)
    session.get.assert_called_once_with(Pedido, pedido_id)
    assert result.model_dump() == {
        "address": "Synthetic address",
        "reference": None,
        "window_start": now,
        "window_end": now + timedelta(hours=1),
        "latitud": -12.0464,
        "longitud": -77.0428,
    }


def test_legacy_assignment_does_not_invent_delivery_data():
    session = Mock()
    assert DriverReportService._delivery(session, None) is None
    session.get.assert_not_called()


def test_order_with_reference_only_does_not_invent_coordinates():
    now = datetime.now(timezone.utc)
    session = Mock()
    session.get.return_value = Pedido(
        direccion="Synthetic address",
        referencia="Synthetic reference",
        ventana_inicio=now,
        ventana_fin=now + timedelta(hours=1),
        ubicacion=None,
    )
    result = DriverReportService._delivery(session, uuid4())
    assert result.latitud is None
    assert result.longitud is None
    session.execute.assert_not_called()


def test_spatial_projection_failure_is_sanitized():
    session = Mock()
    session.get.return_value = Pedido(
        ubicacion=WKBElement(pack("<BIdd", 1, 1, -77.0428, -12.0464), srid=4326)
    )
    session.execute.side_effect = SQLAlchemyError("private spatial storage details")
    with pytest.raises(DriverReportStorageError, match="Assigned order unavailable"):
        DriverReportService._delivery(session, uuid4())


def test_missing_assigned_order_is_not_silently_replaced():
    session = Mock()
    session.get.return_value = None
    with pytest.raises(DriverReportStorageError):
        DriverReportService._delivery(session, uuid4())
