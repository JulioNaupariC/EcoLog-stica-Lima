"""ECL-95 (ST-046): fixed catalogues of the route model.

Shared by the SQLAlchemy models and the Alembic migration so the CHECK
constraints and the ST-045 contract (``app.schemas.rutas``) use the same
values. Changing a catalogue needs a new migration.
"""

ESTADOS_OPTIMIZACION = ("EN_PROCESO", "COMPLETADA", "FALLIDA")
ESTADOS_RUTA = ("PLANIFICADA", "EN_CURSO", "CERRADA")
ESTADOS_PARADA = ("PENDIENTE", "ATENDIDA", "NO_ATENDIDA")
# RN-009. JORNADA_INVIABLE is admitted by the ratified US-006 BDD (decision 5)
# for when ST-047 can verify the cause; RESTRICCION_VIAL is deferred.
MOTIVOS_NO_ASIGNADO = (
    "SIN_UBICACION",
    "EXCEDE_CAPACIDAD",
    "VENTANA_INVIABLE",
    "SIN_VEHICULO",
    "JORNADA_INVIABLE",
)
MOTIVOS_SIN_CONDUCTOR = ("SIN_CONDUCTOR_ELEGIBLE",)
ERROR_MAX = 300
PARAMETROS_VERSION_MAX = 40
