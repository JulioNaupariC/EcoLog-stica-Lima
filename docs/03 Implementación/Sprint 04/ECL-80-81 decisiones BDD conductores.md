# ECL-80/ECL-81 — Decisiones de control de cambios para conductores

- [← Volver al índice del Sprint 4](README.md)

## Registro de decisiones

**Fecha:** 10/11/2026.

**Decidieron conjuntamente:** Frank Roy Yupanqui Acevedo y Julio Armando
Naupari Camarena.
**Alcance:** ECL-80 y ECL-81, extensión del Sprint 4. Las decisiones actualizan
la especificación; no significan que el código haya cambiado ni que se haya
validado en este trabajo.

| Ticket | Decisión | Motivo |
|---|---|---|
| [ECL-80](https://continental-team-il84x39k.atlassian.net/browse/ECL-80) | Descartar D8 — consulta anonimizada de conductores para Auditor — y retirar su caso condicional de la BDD de ST-021. No se define ni implementa una proyección adicional para este alcance. | No hay una necesidad aprobada ni una definición de conteos que permita especificar esa consulta. D8 era una extensión condicional. Esto no modifica la matriz global de usuarios. |
| [ECL-81](https://continental-team-il84x39k.atlassian.net/browse/ECL-81) | Una licencia vencida no impide guardar el perfil: lo deja no asignable hasta su renovación. | US-003 limita la restricción a la asignación; conservar el perfil evita perder el registro del conductor. |
| [ECL-81](https://continental-team-il84x39k.atlassian.net/browse/ECL-81) | Exigir que `licencia_numero` tenga de 1 a 20 caracteres ASCII alfanuméricos o guion, después de recortar espacios y normalizar a mayúsculas. | Validar el formato acordado, sin atribuirlo a una norma externa. |

## Documentos y estado de implementación

- [RF-003 V_1_2_0](../../01%20Inicio/06.%20Requisitos%20funcionales%20V_1_2_0.md)
  registra las decisiones de ECL-81 y conserva
  [RF V_1_1_0](../../01%20Inicio/06.%20Requisitos%20funcionales%20V_1_1_0.md)
  como versión histórica.
- [BDD de conductores ECL-47/ST-021 V_1_2_0](../../02%20Planificación/BDD/ECL-47-ST-021-conductores.md)
  retira el escenario D8 y describe las decisiones, su evidencia y los límites.
- El código vigente permite guardar perfiles con licencia vencida, pero aún no
  valida el patrón ASCII de `licencia_numero`. Su implementación requiere un
  ticket de código separado; no se dispone de una clave para registrarlo aquí.
- No se modificó código ni se ejecutaron pruebas de implementación para estas
  decisiones documentales.

[← Volver al README principal](../../../README.md)
