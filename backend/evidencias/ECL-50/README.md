# Evidencia local de ST-024 / ECL-50

Ejecución final del 09/10/2026, America/Lima. Entorno, casos, resultados y
comandos descritos en [VALIDACION_ST024.md](../../VALIDACION_ST024.md) y en la
[guía para José](../../../GUIA_JOSE_ST024.md).

| Archivo | Contenido |
|---|---|
| [backend-unit.xml](backend-unit.xml) | 520 pruebas unitarias backend |
| [conductores-unit.xml](conductores-unit.xml) | 99 pruebas unitarias de conductores |
| [conductores-coverage.xml](conductores-coverage.xml) | Cobertura unitaria de conductores |
| [backend-coverage.xml](backend-coverage.xml) | Cobertura unitaria backend global |
| [backend-integration.xml](backend-integration.xml) | 116 pruebas PostgreSQL/PostGIS, incluidas 10 de conductores |
| [frontend.xml](frontend.xml) | 369 pruebas frontend |

Son copias de los reportes generados por pytest/pytest-cov/Vitest. Se retiraron
el hostname y las rutas absolutas del equipo; los casos, conteos, resultados y
duraciones se conservan. Los fallos esperados de las pruebas anidadas de
seguridad del fixture se comprueban dentro de sus casos y no son fallos de
esta ejecución final.

La evidencia remota de GitHub Actions se genera al subir la rama y debe
referenciarse en Jira junto con el commit y el PR. Estos archivos acreditan
la ejecución local; no sustituyen los artefactos remotos.
