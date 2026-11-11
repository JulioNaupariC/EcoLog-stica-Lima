## Ticket Jira

<!-- Enlace al ticket ECL-XX -->

## Objetivo

<!-- Que problema resuelve este PR. Maximo 3 oraciones. -->

## Cambios

<!-- Lista de cambios realizados -->

-
-
-

## Validaciones y evidencia

<!-- Que se ejecuto y que resultado se obtuvo. Permite "No aplica" con justificacion. -->

| Validacion | Resultado | Evidencia |
|---|---|---|
| Tests unitarios | [ ] Pasan / [ ] No aplica (justificacion) | |
| Tests de integracion | [ ] Pasan / [ ] No aplica (justificacion) | |
| Lint y formateo | [ ] En verde / [ ] No aplica (justificacion) | |
| Type-check | [ ] En verde / [ ] No aplica (justificacion) | |
| CodeQL | [ ] Ejecucion completada / [ ] No aplica (justificacion) | |

Nota: una ejecucion exitosa de CodeQL confirma que el analisis se completo. La revision de alertas se realiza en la pestana Security > Code scanning alerts.

## Revisión

<!-- Cada revisor registra su aprobación en un comentario de revisión de GitHub e indica qué comprobó: pruebas, alcance y evidencias; anota también los acuerdos o decisiones. El autor enlaza aquí el comentario y resume los acuerdos. Una aprobación sin comentario debe completarse antes del merge. -->

| Revisor / área | Qué comprobó (pruebas, alcance, evidencias) | Acuerdos / decisiones | Enlace a la aprobación comentada |
|---|---|---|---|
| | | | |

## Corte de alcance — A12 / ECL-91

<!-- Junto a la revisión comentada de A10 / ECL-89. Completar antes del merge y actualizar si cambia el diff o se cumplen 24 horas. -->

Si el PR supera **10 archivos sin contar evidencias** o lleva **más de 24 horas abierto**, el autor entrega en este PR el incremento ya validado, corta el alcance restante y abre/enlaza un ticket para ese resto. El revisor solicita el corte si el autor no lo hace; Giancarlo aplica esta regla al revisar `frontend/`.

Se cuentan los archivos del diff completo contra la base, incluidos documentación, pruebas, configuración y renombrados (un renombrado cuenta una vez). Solo se excluyen archivos de evidencia identificados y enumerados; un script, prueba o cambio funcional no se excluye por llamarlo evidencia. El tiempo corre desde la apertura, incluido Draft, hasta el merge o hasta ahora si sigue abierto; nuevos commits no lo reinician. Exactamente 10 archivos o 24 horas no superan el límite.

| Archivos totales | Evidencias excluidas (rutas) | Archivos computables | Horas abierto / fecha de corte | ¿Supera algún límite? |
|---|---|---|---|---|
| | | | | |

- Incremento validado que se entrega aquí:
- Trabajo retirado y ticket de seguimiento (enlace, alcance, responsable y criterio de aceptación):
- Justificación del corte y decisión del revisor (enlace al comentario de revisión):

- [ ] Si supera el límite, el resto está separado y trazado a su ticket; si no lo supera, se anotó «No aplica» con el conteo y la edad.
- [ ] Si supera el límite sin justificación, se dividió antes del merge. Una justificación no sustituye el ticket del resto ni las validaciones y revisiones exigidas.

## Riesgos

<!-- Riesgos conocidos o "No aplica" con justificacion -->

-
-

## Checklist de seguridad y revision

- [ ] No se anaden secretos ni credenciales
- [ ] No se introducen dependencias nuevas sin justificacion
- [ ] Se actualizo documentacion si aplica
- [ ] Se actualizo OpenAPI/Swagger si cambio la API
- [ ] Criterios de aceptacion del ticket satisfechos
- [ ] Se revisaron las alertas de CodeQL (no basta con job verde)
