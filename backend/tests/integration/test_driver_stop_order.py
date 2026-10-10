from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from alembic import command
from app.db.session import session_factory
from app.models import Cliente, Pedido
from app.repositories.usuarios import UsuarioRepository
from app.services.credenciales import CredentialService
from app.services.driver_reports import DriverReportService

pytestmark = pytest.mark.integration


def test_assignment_links_existing_order_and_exports_operational_details(
    migration_database,
):
    engine, config = migration_database
    command.upgrade(config, "head")
    factory = session_factory(engine)
    with factory.begin() as session:
        user = CredentialService(UsuarioRepository(session)).create(
            "offline-driver@example.test", "synthetic-password-only", "CONDUCTOR"
        )
        owner = user.usuario_id
        customer = Cliente(nombre="Not exposed to driver")
        session.add(customer)
        session.flush()
        now = datetime.now(timezone.utc)
        order = Pedido(
            cliente_id=customer.cliente_id,
            direccion="Synthetic location",
            referencia="Synthetic gate",
            peso_kg=Decimal("1.00"),
            volumen_m3=Decimal("0.01"),
            ventana_inicio=now,
            ventana_fin=now + timedelta(hours=1),
            prioridad="ESTANDAR",
            tipo_producto="GENERAL",
        )
        session.add(order)
        session.flush()
        pedido_id = order.pedido_id
    service = DriverReportService(factory)
    service.provision_assignment(
        stop_id=uuid4(), owner_id=owner, position=1, pedido_id=pedido_id
    )
    result = service.list_assignments(owner)
    assert result[0].delivery.address == "Synthetic location"
    assert result[0].delivery.reference == "Synthetic gate"
    assert result[0].delivery.window_start == now
    assert service.list_assignments(uuid4()) == []
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert "uq_driver_stop_pedido" in {
            c["name"]
            for c in inspector.get_unique_constraints("driver_stop_assignment")
        }
        assert "fk_driver_stop_pedido" in {
            c["name"] for c in inspector.get_foreign_keys("driver_stop_assignment")
        }
