# AGENTS.md — EcoLogística Lima

## 1. Propósito

Este repositorio corresponde al proyecto académico **EcoLogística Lima**,
un optimizador de rutas sostenibles para DistriRápido S.A.C.

Todo trabajo realizado por agentes de IA debe respetar la documentación
existente del proyecto y limitarse estrictamente al alcance del ticket Jira
asignado.

---

## 2. Fuente de verdad

Antes de modificar código, revisar como mínimo:

- `README.md`
- `docs/01 Inicio/06. Requisitos funcionales V_1_0_0.md`
- `docs/01 Inicio/07. Requisitos no funcionales V_1_1_0.md`
- `docs/01 Inicio/09. Reglas de negocio V_1_0_0.md`
- `docs/01 Inicio/10. Stack tecnológico V_1_0_0.md`
- `docs/01 Inicio/11. Base de datos V_1_0_0.md`
- `docs/01 Inicio/12. Modelo C4 V_1_0_0.md`
- `docs/02 Planificación/01 Transformando a ágil V_1_0_0.md`
- `docs/02 Planificación/02 Artefactos Jira V_1_0_0.md`

Jira define el alcance y estado operativo del trabajo.

GitHub define el estado del código.

---

## 3. Arquitectura tecnológica

### Backend

- Python
- FastAPI
- PostgreSQL
- PostGIS
- SQLAlchemy
- Alembic
- Pydantic
- Pytest

### Frontend

- React
- TypeScript
- Vite

### Infraestructura

- Docker
- Docker Compose
- GitHub Actions

### Optimización

- Worker Python desacoplado del API
- Redis como mecanismo de cola/cache cuando corresponda
- VRPTW / Green VRP

---

## 4. Reglas de trabajo

Nunca trabajar directamente sobre `main`.

Cada ticket Jira debe desarrollarse en una rama independiente.

Formato recomendado:

`feat/ECL-<id>-descripcion`

Ejemplo:

`feat/ECL-27-fastapi-postgis-bootstrap`

Una rama debe corresponder a una unidad de trabajo claramente identificable.

No ampliar el alcance del ticket sin autorización.

No modificar requisitos, planificación ni reglas de negocio para adaptar el
proyecto al código.

El código debe adaptarse a la documentación aprobada.

---

## 5. Seguridad

Nunca almacenar en el repositorio:

- contraseñas;
- tokens;
- API keys;
- secretos;
- credenciales de base de datos reales;
- archivos `.env` con valores sensibles.

Usar variables de entorno y proporcionar únicamente ejemplos seguros como:

`.env.example`

Todo endpoint debe considerar validación de entrada y control de acceso cuando
corresponda.

---

## 6. Calidad

Todo cambio debe intentar cumplir el Definition of Done del proyecto:

- cobertura de pruebas unitarias >= 80% para el incremento afectado;
- pruebas automatizadas en verde;
- análisis estático/SAST sin vulnerabilidades críticas abiertas;
- Peer Review antes de integrar en `main`;
- documentación técnica actualizada cuando corresponda;
- OpenAPI/Swagger actualizado cuando cambie la API;
- criterios de aceptación del ticket satisfechos.

---

## 7. Convenciones de código

### Python

- seguir PEP 8;
- usar type hints;
- evitar funciones excesivamente grandes;
- separar dominio, infraestructura y API;
- usar nombres claros y explícitos;
- no colocar lógica de negocio compleja dentro de routers FastAPI.

### TypeScript

- evitar `any` salvo justificación;
- usar componentes pequeños;
- separar UI, servicios y lógica de dominio;
- definir tipos/interfaces explícitos.

---

## 8. Estructura objetivo

La estructura base prevista es:

```text
EcoLog-stica-Lima/
├── AGENTS.md
├── README.md
├── backend/
├── frontend/
├── optimization/
├── infrastructure/
├── docs/
└── .github/