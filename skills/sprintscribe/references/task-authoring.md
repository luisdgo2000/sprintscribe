# Redacción de tareas para Azure Boards

Las tareas son el **primer entregable**. Cada tarea con estado `confirmed`, `modified` o `blocked` debe poder ejecutarla su responsable sin releer la reunión.

## Título

- **Breve (de 5 a 12 palabras), accionable**, empieza con un verbo y describe el **resultado concreto**.
- ✅ "Exponer endpoint de descarga de facturas en PDF"
- ✅ "Evitar cuentas duplicadas normalizando el correo en el registro"
- ❌ "Revisar tema", "Trabajar en mejora", "Hacer ajustes", "Validar eso". `validate` rechaza los títulos genéricos o de menos de 3 palabras.
- Si una tarea `modified` cambió de alcance, el título refleja la versión **vigente**.

## Descripción

Incluye, en prosa y con el nivel de detalle que el trabajo requiera:

1. **Problema o necesidad** que origina la tarea (el "por qué").
2. **Objetivo específico** que se busca alcanzar.
3. **Trabajo que hay que realizar**, solo lo que respalda la conversación o el contexto validado.
4. **Contexto técnico o funcional** relevante: sistemas mencionados, decisiones previas.
5. **Restricciones, dependencias y consideraciones:** a quién se le debe entregar algo, qué falta.
6. **Relación con otras tareas** cuando corresponda: "Depende de PCL-T1", "Sustituye a PCL-T2".

**No inventes** implementaciones, tablas, campos, sistemas, entregables ni comportamientos sin sustento. Si un detalle técnico no se dijo, no lo pongas. Si es necesario para ejecutar la tarea, conviértelo en pregunta.

## Criterio de aceptación: exactamente uno

- **Una sola oración o un solo enunciado**, concreto y **verificable de forma objetiva**, directamente ligado al resultado de la tarea.
- **Si hay varias condiciones necesarias, consolídalas en un único criterio coherente:**
  - ✅ "Un cliente autenticado obtiene el PDF de una factura propia desde el endpoint y recibe un rechazo al pedir una factura de otro cliente."
  - ❌ "- Devuelve el PDF\n- Valida permisos". `validate` rechaza las listas y los textos de varias líneas.
- **Evita los criterios no verificables:** "funciona bien", "queda optimizado".
- Las tareas `proposed`, `needs_clarification` y `deferred` pueden no tener criterio de aceptación.

## Responsable, prioridad y tipo

- **`owner`:** según [interpretation.md](interpretation.md). Si nadie la tomó, usa `null`; nunca inventes un responsable.
- **`priority`:** solo si se mencionó ("esto es lo primero", "sí o sí este sprint") o si lo exige la convención del equipo. En otro caso, `null`. Si la infieres, usa `priority_certainty: "inferred"`.
- **`work_item_type`:** es un tipo **lógico** (`task`, `story`, `bug`, `research`…). El tipo real de Boards lo resuelve `boards.work_item_types` de la configuración o el perfil del uploader. No escribas tipos de un proceso que no conoces.
- **`hierarchy_hint`:** caso de uso, épica, feature y story **en texto**, cuando la conversación o la documentación los nombran. Sirven para elegir de los catálogos del Excel o de Boards. Nunca pongas IDs inventados.

## Esfuerzo inferido

Estímalo a partir de la complejidad, el alcance, las dependencias, el trabajo técnico descrito y los antecedentes.

- **Si `effort_convention.mode` es `ranges` (por defecto):**
  - `range` temporal para **una** tarea: "4-8 h", "1-2 d", "3-5 d";
  - `level` (`low`, `medium` o `high`);
  - `confidence` (`low`, `medium` o `high`);
  - `rationale` breve, que nombre la incertidumbre cuando la confianza sea baja.
- **No asignes Story Points** salvo que `effort_convention.mode = "story_points"`. Úsalos solo con la escala del equipo y guárdalos en `native_value`.
- **Evita la falsa precisión:** con poca información, usa un rango amplio y confianza `low`.
- Si un participante dio su propia estimación ("calculo un par de días"), úsala como base y cítala.
- **El esfuerzo de una tarea no es la duración de una etapa de la hoja de ruta.** Esta última incluye esperas, validaciones y dependencias.

## Evidencia

`evidence` es obligatoria en toda tarea:

- una o más citas breves y fieles, con `speaker` y `timestamp` cuando existan;
- en tareas modificadas o sustituidas, incluye la cita original y la de la corrección.

## Lista de control por tarea

- [ ] Pertenece al proyecto correcto o está en `PENDING`.
- [ ] Título accionable con el resultado concreto.
- [ ] Descripción autosuficiente y sin inventos.
- [ ] Exactamente un criterio de aceptación verificable.
- [ ] Responsable respaldado por el contexto, o `null`.
- [ ] Esfuerzo con rango, nivel, confianza y fundamento.
- [ ] Evidencia citada.
- [ ] Relaciones (`depends_on`, `supersedes`…) coherentes.
