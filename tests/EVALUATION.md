# Evaluar al modelo con los casos de prueba

`test_cli.py` comprueba que la **capa determinista** funciona y que los estados de referencia (`golden-state.json`) cumplen las reglas.

Esta guía sirve para medir algo distinto: si **el modelo** interpreta bien las transcripciones. Para eso se genera un estado nuevo con el agente y se califica contra `expected.json`.

## Procedimiento por caso

1. Instala SprintScribe en un workspace de prueba:
   ```bash
   python3 install.py --scope workspace --target /ruta/workspace-prueba
   ```
2. Copia `tests/fixtures/config.json` a `/ruta/workspace-prueba/.sprintscribe/config.json`. Contiene el roster y los proyectos de los casos.
3. **Solo para el caso 10:** primero procesa `previous-state.json` con `merge`, para que exista el ledger previo:
   ```bash
   python3 .github/skills/sprintscribe/scripts/sprintscribe.py merge tests/cases/10-second-meeting/previous-state.json
   ```
4. En Copilot Chat, con el agente **sprintscribe**:
   > Procesa la reunión de `tests/cases/04-cancel-and-replace/transcript.md`

   **Caso 11:** dile además que use `boards-snapshot.json` como snapshot de Boards.
5. Califica el estado que produjo el agente:
   ```bash
   python3 .github/skills/sprintscribe/scripts/sprintscribe.py check-expectations documentacion/_inbox/<meeting-id>/meeting-state.json tests/cases/04-cancel-and-replace/expected.json
   ```
   El comando termina con código 0 solo si se cumplen todas las expectativas.
6. Compara además los documentos generados con los de `golden-state.json`, renderizados con `render --out`, para revisar a ojo la calidad de las descripciones, del objetivo y de la hoja de ruta.

## Formato de `expected.json`

| Clave | Significado |
|---|---|
| `tasks[]` | Debe existir una tarea cuyo título y descripción cumplan todas las expresiones de `match`. Opcionalmente se exige `status_in`, `owner` (`null` = sin responsable), `project` y `work_item_id` |
| `forbidden[]` | No debe existir ninguna tarea que cumpla `match` con un estado de `status_in` |
| `ready_count` | Rango de tareas listas: `confirmed`, `modified` o `blocked` |
| `projects` | Conjunto exacto de IDs de proyecto |
| `reconciliation[]` | Debe existir una entrada de log con esa `action`, opcionalmente sobre una tarea que cumpla `task_match` |
| `decisions[]` | Debe existir una decisión de ese `kind` cuyo texto cumpla `match` |
| `open_questions_min`, `open_questions_max`, `contradictions_min` | Cantidades |
| `ops[]`, `forbid_ops[]`, `no_applied_ops` | Plan de operaciones, después de ejecutar `ops-plan` |

Las expresiones se comparan sin tildes ni mayúsculas; `|` funciona como alternativa.

## Criterio de aprobación sugerido

- **Bloqueantes:** los casos 03, 04, 08, 10 y 11 deben pasar al 100 %. Son los de reconciliación, compromisos e integración.
- **Resto:** en los demás casos se acepta, como máximo, una expectativa de redacción fallida si la revisión manual confirma que la tarea es correcta. Por ejemplo, un título que no contiene la palabra esperada.
