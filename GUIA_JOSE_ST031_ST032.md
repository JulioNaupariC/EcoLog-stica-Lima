# José — cierre de ST-031 y ST-032

Son dos ramas independientes basadas en `origin/main` (8035345).
Los cambios y commits están preparados localmente. No ejecutar `git add .` ni
copiar archivos completos de otra rama para integrarlas. GitHub Actions y la
revisión del equipo se comprueban al abrir los PR; no se han ejecutado en remoto
para estos commits locales.

## Subir las ramas

Desde la raíz del repositorio:

```powershell
git status
git push -u origin fix/ECL-57-st031-accesibilidad
git push -u origin fix/ECL-58-st032-offline
```

Estos comandos suben ambas ramas aunque estés situado en una sola.
Crear dos PR con **base: main**, uno por cada rama. No usar force push.
Si `main` avanzó y GitHub detecta conflictos, integrar sus cambios en la rama
afectada conservando ambas funcionalidades; no aceptar un archivo entero sin revisión.

## PR de ST-031

Título:

```text
fix(ECL-57): completar responsive y accesibilidad ST-031
```

Descripción:

```markdown
## Resultado
Corrige el foco visible de la experiencia del conductor, añade salto al contenido
y evita desbordamiento de acciones a 360 px. El indicador de foco azul tiene
contraste 6.70:1 sobre blanco. Mantiene controles utilizables con teclado.

## Validación
- Chrome 155.0.8059.40 y Firefox 157.0: 360, 768 y 1280 px sin scroll horizontal.
- Tab, foco y Enter en el salto al contenido; etiquetas y espaciado de texto.
- axe-core 4.10.3: cero infracciones en los estados comprobados.
- 441 pruebas frontend; TypeScript, ESLint y build aprobados.
- Script, checklist, resultados y 14 capturas en frontend/VALIDACION_ST031.md
  y frontend/evidencias/ECL-57/.

## Alcance de la evidencia
La validación de interfaz usa API simulada; no certifica todas las pantallas del
producto ni sustituye pruebas con lectores de pantalla o usuarios reales.
Revisar los checks de este PR y solicitar revisión antes de integrar.
```

## PR de ST-032

Título:

```text
fix(ECL-58): completar itinerario offline y sincronización ST-032
```

Descripción:

```markdown
## Resultado
Después de consultar una ruta autenticada, el conductor puede recargarla sin red
en la misma pestaña. Los reportes permanecen pendientes y se sincronizan
automáticamente al recuperar conexión, conservando su UUID hasta confirmar
persistencia. La pantalla y el snapshot reflejan el ACK del servidor.

Incluye shell público versionado, recuperación de identidad limitada al vencimiento
de sesión, reintentos con espera, coordinación Web Locks y dirección/ventana del
pedido vinculado. Mantiene autorización e idempotencia en el backend.

## Validación
- 10 ciclos por navegador en Chrome y Firefox: offline, recarga, reconexión y ACK.
- API FastAPI y PostgreSQL/PostGIS reales; 20 operaciones = 20 reportes persistidos.
- Respuesta perdida después de persistir, reenvíos idempotentes y API no disponible.
- Aislamiento tras logout; otro conductor 404 y operador 403.
- 471 pruebas frontend, 560 backend y 2 de integración aprobadas.
- Cobertura de líneas frontend 97.23%; cobertura backend 93.17%.
- TypeScript, ESLint, Ruff y build aprobados.
- Scripts, XML, registros SQL/HTTP y ocho capturas en frontend/VALIDACION_ST032.md
  y frontend/evidencias/ECL-58/.

## Despliegue y límites
Aplicar Alembic 0009_driver_stop_order antes del frontend. El productor confiable
de asignaciones debe pasar pedido_id auténtico; los vínculos históricos vacíos
no se completan con datos ficticios. El optimizador completo está fuera del ticket.
Offline requiere carga inicial online y build de producción; no crea sesiones
nuevas sin red. IndexedDB guarda dirección/referencia/ventana sin cifrado y con
TTL 24 h; la cola pendiente se conserva con advertencia al cerrar sesión.
No se acredita un SLA ni pruebas con dispositivos físicos.
Revisar los checks de este PR y solicitar revisión antes de integrar.
```

## Preparación del ambiente para ST-032

Con `DATABASE_URL` configurada para el ambiente correspondiente, desde la raíz:

```powershell
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
cd ../frontend
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:coverage
npm.cmd run build
```

Configurar `VITE_API_BASE_URL` auténtica antes de compilar. Servir `dist/` sobre
HTTPS o localhost. Para la prueba aislada reproducible, seguir
`frontend/VALIDACION_ST032.md` en la rama ST-032; no apuntarla a la base compartida.
Los resultados/checklist ST-031 están en su propia rama.
