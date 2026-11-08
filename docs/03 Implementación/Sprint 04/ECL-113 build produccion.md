# ECL-113 - Build de produccion

## Objetivo

Servir el frontend React/Vite mediante un build optimizado, con compresion HTTP y politicas de cache.

## Configuracion ANTES

- Commit de referencia: consultar el commit de corte de ECL-108.
- Dockerfile de desarrollo: ejecuta npm run dev.
- Servidor: Vite en el puerto 5173.
- No existe una configuracion independiente de Nginx.

## Configuracion DESPUES

- frontend/Dockerfile.prod: build de Vite y servidor Nginx.
- frontend/nginx.prod.conf: Gzip y politicas de cache.
- compose.prod.yaml: configuracion complementaria de produccion.
- Se conserva el entorno de desarrollo original.

## Ejecucion prevista

Desarrollo:
docker compose -f compose.yaml up --build

Produccion:
docker compose -f compose.yaml -f compose.prod.yaml up --build

Ambos modos se sirven en http://127.0.0.1:5173.

La URL de FastAPI se incorpora durante el build:
VITE_API_BASE_URL=http://127.0.0.1:8000

## Cache

- Assets con hash: public, max-age=31536000, immutable.
- index.html: no-cache.
- sw.js y offline-shell.json: no-cache.
- Manifiestos: no-cache.

## Modo offline

El comando npm run build ejecuta build-offline.mjs y genera los archivos necesarios para el modo sin conexion.

Pendiente: verificar el modo offline del conductor con Nginx.

## Medicion Green IT

La medicion ANTES de ECL-108 utilizo Vite en desarrollo.

El DESPUES de ECL-115 utilizara el build de produccion.

Se trata de un cambio de protocolo que debe declararse expresamente al comparar resultados.

No se reportan mejoras de rendimiento ni reducciones energeticas sin mediciones reproducibles.

## Validacion

- Build local de React/Vite: correcto.
- Prueba del contenedor Nginx: pendiente.
- Content-Encoding HTTP: pendiente.
- Cabeceras Cache-Control: pendiente.
- Prueba offline del conductor: pendiente.
- Brotli: no implementado; Gzip configurado.
- CI: pendiente de ejecucion en PR.

## Trazabilidad

Ticket: ECL-113
Responsable: JulioNaupariC
Revisor: JoseDelgadillo277

[Volver al indice del Sprint 4](README.md)
[Volver al README principal](../../../README.md)
