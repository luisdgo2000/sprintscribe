# Documentación estratégica por proyecto

Después de las tareas se construye una síntesis estratégica por proyecto. No es un acta literal ni una transcripción abreviada: explica qué se busca conseguir, quién participa, qué se acordó y cómo sigue el trabajo.

Todo esto se escribe en `meeting-state.json`; `render` produce los documentos.

## Documento A · Objetivo del sprint (`projects[].sprint_objective`)

| Campo | Contenido |
|---|---|
| `statement` | El objetivo principal |
| `expected_result` | Resultado concreto que se pretende alcanzar |
| `business_need` | Necesidad de negocio que justifica el esfuerzo |
| `deliverables` | Principales entregables, solo de tareas vigentes |
| `owners`, `participants` | Responsables principales y participantes involucrados |
| `scope`, `exclusions` | Alcance relevante y exclusiones explícitas. Las tareas canceladas o diferidas suelen ser exclusiones |
| `period` | Sprint o período **solo si se identificó** |
| `certainty` | Normalmente `inferred`; `explicit` si el PO lo formuló |
| `candidates` | Si no hay un objetivo único: los objetivos candidatos y su respaldo, con `certainty: "pending"` |

**Fórmula guía (no es una plantilla rígida):**

> "Lograr [resultado esperado] para [proceso, usuario o necesidad], mediante [entregable o cambio principal], con el fin de [valor esperado]."

**Cómo inferirlo:**

- Parte de las tareas **confirmadas**, de las prioridades discutidas y del resultado que espera el PO.
- **No repitas los nombres de las tareas.** Explica el propósito que comparten. `validate` rechaza un objetivo idéntico al título de una tarea.
- **No inventes** fechas de sprint, fechas de entrega ni objetivos empresariales que no se hayan mencionado o validado.

## Documento B · Hoja de ruta (`projects[].roadmap`)

Es breve, ordenada y accionable. Cada paso lleva:

| Campo | Contenido |
|---|---|
| `order` | Posición, **según las dependencias y el flujo lógico**, no según el orden en que se mencionó |
| `step`, `purpose` | Paso o entregable, y para qué sirve |
| `kind` | `agreed`, si salió de la reunión, o `recommended`, si es una sugerencia tuya |
| `owner` | Si se conoce |
| `task_refs` | Tareas relacionadas, **nunca canceladas** |
| `depends_on` | Números de orden de pasos **anteriores** (`validate` lo exige) |
| `duration.range`, `duration.basis`, `duration.confidence` | Estimación temporal inferida, su fundamento y su confianza |
| `risks` | Riesgos, bloqueos o decisiones pendientes |

**Reglas:**

- **La duración de una etapa no es el esfuerzo de una tarea.** Considera la secuencia, las dependencias, las validaciones, la disponibilidad de terceros y los posibles bloqueos.
- **Sin fechas confirmadas**, usa rangos relativos ("1-2 semanas") y explica brevemente en qué te basas.
- **Distingue con claridad** lo acordado de lo recomendado. Un paso recomendado nunca es un compromiso oficial.
- **Si hay decisiones pendientes que condicionan el plan**, crea un paso recomendado para resolverlas (por ejemplo, "Definir responsable", "Cotizar la nueva API").

## Documento C · Acuerdos, decisiones y pendientes (`decisions`, `open_questions`, `contradictions`)

Registra **solo** lo relevante para ejecutar el proyecto, con su `kind`:

| `kind` | Sección |
|---|---|
| `decision` | Decisiones confirmadas |
| `change` | Cambios respecto de acuerdos anteriores. Usa `supersedes` si reemplaza otra decisión |
| `responsibility` | Responsabilidades asignadas o reasignadas |
| `commitment`, `dependency` | Compromisos y dependencias |
| `blocker`, `risk` | Bloqueos y riesgos |
| `po_validation` | Decisiones que requieren validación del PO |
| `external_action` | Acciones de personas o equipos externos |
| `open_question` | Dudas abiertas (o usa `open_questions[]` si bloquean tareas concretas) |

**Cada decisión lleva:**

- `context`: por qué importa y qué impacto tiene;
- `decided_by` y `executed_by`, por separado. No atribuyas la ejecución a quien habló o propuso;
- `task_refs` y `evidence`.

## Coherencia entre documentos

- Las tareas, los acuerdos y la hoja de ruta no se contradicen.
- Lo que está cancelado no aparece como entregable ni en la hoja de ruta.
- Una decisión `change` explica cada `cancelled`, `modified` o `reassigned` del log.
- `validate` comprueba una parte de esto. El resto (que el objetivo tenga sentido respecto de las tareas y que los responsables coincidan) lo revisas tú en la fase 7.
