# SprintScribe

SprintScribe convierte transcripciones de reuniones de refinamiento, sprint planning y seguimiento en:

1. **Tareas para Azure Boards**, que son el primer entregable. Cada una lleva título accionable, descripción autosuficiente, **exactamente un** criterio de aceptación, responsable, esfuerzo inferido y evidencia.
2. **Documentación estratégica por proyecto**: objetivo del sprint, hoja de ruta, acuerdos y decisiones, y registro de reconciliación.

No es un resumidor. Reconstruye **lo que realmente se decidió**: si en el minuto 12 el PO cancela una tarea dicha en el minuto 0 y la reemplaza por otra, la tarea original no se sube, la nueva sí, y el cambio queda trazado. Hace lo mismo entre reuniones.

---

## Arquitectura

**Una skill portable, un agente orquestador fino y una CLI determinista.** No es un sistema multiagente.

```
 transcripción ─┐
 config/ledger ─┼─► Agente Copilot ──► (aplica la skill) ──► meeting-state.json ──► CLI sprintscribe.py
 snapshot Boards┘     (orquesta, compuertas)                    (única salida del LLM)    validate · ops-plan
                                                                                          render · merge · export
                                                                                                 │
                                       docs por proyecto (01–04) ◄────────────────────────────────┤
                                       ledger acumulado por proyecto ◄────────────────────────────┤
                                       tasks.csv para el Excel/uploader ◄─────────────────────────┘
```

**Por qué esta arquitectura** (investigación de octubre de 2026):

- **GitHub Copilot** admite *Agent Skills* (el estándar abierto agentskills.io: `SKILL.md` más `scripts/`, `references/` y `assets/`) en VS Code, en la CLI y en el coding agent. También admite *custom agents* (`*.agent.md`) con herramientas restringidas, terminal (`execute`), MCP y *handoffs*.
  - El conocimiento vive en la skill, así que se reutiliza en cualquier cliente compatible.
  - El agente solo orquesta y aplica las compuertas.
- Un agente **no puede declarar skills**: las skills se descubren solas. Por eso el agente se instala con las rutas absolutas de la skill y de la CLI ya resueltas.
- **La lógica verificable no depende del modelo.** El LLM solo escribe `meeting-state.json`, un JSON con esquema. Validar, deduplicar, renderizar y llevar el historial lo hace un script, de forma reproducible y probada. Así tareas, acuerdos y hoja de ruta no se contradicen, y la validación es automática.
- **Azure Boards se toca solo con herramientas reales**:
  - el Azure DevOps MCP Server oficial (`microsoft/azure-devops-mcp`), en solo lectura por defecto; o
  - el uploader Python del equipo, pendiente de configurar.

  Sin canal no hay escritura: el modo es Draft y queda un plan de operaciones pendiente.
- **Databricks Genie Code** también admite Agent Skills (`/Users/<usuario>/.assistant/skills/`). La misma carpeta `skills/sprintscribe` sirve allí en modo Draft. Esta entrega está enfocada en Copilot.

---

## Estructura del repositorio

```
skills/sprintscribe/            ← la skill (portable; es lo que se instala)
  SKILL.md                        flujo, reglas no negociables, contrato de salida
  references/                     interpretación, reconciliación, proyectos, tareas, documentos, Boards
  assets/schema/                  meeting-state.schema.json, config.schema.json
  assets/templates/               plantillas Markdown de los documentos 01–04
  assets/examples/                ejemplo de referencia (tareas 1–4)
  scripts/sprintscribe.py         CLI (Python 3.9+, solo biblioteca estándar)
adapters/copilot/               ← convenciones propias de GitHub Copilot
  agents/sprintscribe.agent.md    agente orquestador (plantilla con rutas que resuelve el instalador)
  prompts/procesar-reunion.prompt.md
  mcp.example.json                Azure DevOps MCP en solo lectura
config/sprintscribe.config.example.json
install.py                      instalador por usuario o por workspace
tests/                          12 casos con transcripción, expectativas y estado de referencia, más test_cli.py
```

---

## Requisitos

- Python 3.9 o superior. No hace falta instalar paquetes.
- VS Code con GitHub Copilot en **modo agente** (o la Copilot CLI) y permiso para ejecutar comandos en la terminal.
- Opcional: el Azure DevOps MCP Server.
  - Requiere que la organización habilite la política *MCP servers in Copilot*.
  - El servidor remoto usa Microsoft Entra ID.

---

## Instalación

Hay dos modalidades y se pueden combinar.

**1. Por usuario.** Disponible en todos los workspaces de este equipo:

```bash
python3 install.py --scope user
```

Instala:

- `~/.copilot/skills/sprintscribe/`;
- `~/.copilot/agents/sprintscribe.agent.md`, con la ruta absoluta de la CLI y del Python de este equipo;
- `~/.sprintscribe/config.json`, solo si no existe.

**2. Por workspace.** Recomendada para equipos: va en el repositorio de documentación y se versiona con él.

```bash
python3 install.py --scope workspace --target /ruta/al/repo-de-documentacion --with-mcp
```

Instala `.github/skills/`, `.github/agents/`, `.github/prompts/`, `.sprintscribe/config.json` y, si se pide, `.vscode/mcp.json` en solo lectura. Las rutas son relativas, así que funciona en cualquier equipo que clone el repositorio.

**Comportamiento del instalador:**

- **Reinstalar** actualiza la skill y el agente, y **nunca** sobrescribe la configuración.
- **Archivos ajenos:** no reemplaza archivos que no instaló SprintScribe (salvo con `--force`).
- **`--dry-run`** muestra lo que haría sin escribir nada.
- **`--python <comando>`** fija el intérprete, por ejemplo `py -3` en Windows.

---

## Configuración

La CLI combina estas capas, de menor a mayor prioridad:

1. Los valores por defecto.
2. `~/.sprintscribe/config.json` (o `$SPRINTSCRIBE_HOME/config.json`).
3. `.sprintscribe/config.json`: el primero que encuentre subiendo desde la carpeta actual.

`--config <archivo>` reemplaza todas las capas.

| Clave | Uso |
|---|---|
| `docs_root`, `inbox_dir` | Dónde se escriben los documentos y el estado de trabajo |
| `po` | El Product Owner (por defecto Brian) y sus alias, incluidos los errores de transcripción |
| `roster[]` | Personas: nombre, alias, rol y UPN opcional |
| `projects[]` | `id` (carpeta), `key` (prefijo de IDs, p. ej. `PCL`), nombre, alias y documentación |
| `effort_convention` | `ranges` por defecto. `story_points` solo si el equipo tiene esa convención |
| `boards.mode`, `boards.channel` | `draft` o `sync`, y `none`, `mcp` o `uploader` |
| `boards.state_mapping` | Estado lógico → estado real de **tu** proceso, p. ej. `{"cancelled": "Removed"}` |
| `boards.work_item_types` | Tipo lógico → tipo real, p. ej. `{"task": "Task", "story": "User Story"}` |
| `boards.dedup` | Umbrales de similitud para detectar duplicados |
| `uploader.status` | `pending` hasta configurar la versión real del programa |

**Nunca se guardan credenciales en la configuración.** Los tokens viven en variables de entorno o en el inicio de sesión del cliente MCP.

---

## Uso

### Con el agente (lo habitual)

En Copilot Chat elige el agente **sprintscribe** y escribe:

> Procesa la reunión de `reuniones/2026-10-09-refinamiento.md`

O usa el prompt `/procesar-reunion`, disponible en la instalación por workspace.

El agente sigue estas fases: inspeccionar (`context`), comprender, reconciliar, escribir el estado, validar, plan de operaciones, render, merge y export.

Responde primero con la tabla de tareas, después con los cambios y las rutas, el estado de Boards y las pocas ambigüedades que bloquean trabajo.

### Con la CLI directamente

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py context
```

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py validate documentacion/_inbox/<reunion>/meeting-state.json
```

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py ops-plan documentacion/_inbox/<reunion>/meeting-state.json --snapshot boards.json
```

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py render documentacion/_inbox/<reunion>/meeting-state.json
```

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py merge documentacion/_inbox/<reunion>/meeting-state.json
```

```bash
python3 skills/sprintscribe/scripts/sprintscribe.py export documentacion/_inbox/<reunion>/meeting-state.json --format csv --out tasks.csv
```

### Salidas

```
documentacion/
  _inbox/<meeting-id>/meeting-state.json          estado completo (lo escribe el agente)
  <proyecto>/<fecha>/01-azure-boards-tasks.md      tareas listas, no listas, descartadas y plan de operaciones
  <proyecto>/<fecha>/02-sprint-objective-and-roadmap.md
  <proyecto>/<fecha>/03-agreements-and-decisions.md
  <proyecto>/<fecha>/04-reconciliation-log.md
  <proyecto>/<fecha>/meeting-state.json            estado filtrado del proyecto
  <proyecto>/_state/project-state.json             ledger acumulado entre reuniones
  _pendiente-de-asignar/<fecha>/                   tareas cuyo proyecto no se pudo resolver
```

La documentación de una reunión nunca sobrescribe la de otra: si la carpeta ya existe, se usa `-v2`, `-v3`, etc. Volver a renderizar la **misma** reunión actualiza su carpeta.

---

## Modos de ejecución

| Modo | Condición | Resultado |
|---|---|---|
| **Draft** (por defecto) | Sin canal, `boards.mode = "draft"` o sin autorización | Tareas, documentos y `ops_plan` pendiente. **Nada se escribe en Boards** |
| **Sync** | `boards.mode = "sync"`, canal disponible **y** confirmación explícita en el chat | Aplica solo las operaciones inequívocas; las ambiguas quedan en revisión; se registra el resultado real de cada una |

**Garantías del plan de operaciones:**

- **Nunca borra:** cancelar es cambiar de estado (según `state_mapping`).
- **No toca un work item cuya identidad no esté verificada:** una coincidencia por título va a revisión.
- **No crea duplicados:** si la tarea ya existe en el snapshot, propone actualizarla o no hacer nada.
- `validate` rechaza cualquier operación marcada como aplicada en modo Draft o sin la respuesta real de la herramienta.

---

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

**Qué cubren (42 pruebas):**

- Los 12 casos de calidad: cada estado de referencia pasa `validate` y sus expectativas.
- Los rechazos de `validate`:
  - tarea cancelada en la hoja de ruta o reactivada;
  - varios criterios de aceptación;
  - Story Points sin convención;
  - títulos genéricos;
  - contradicciones;
  - operaciones simuladas.
- La deduplicación contra Boards.
- El render determinista y sin sobrescritura.
- El ledger entre reuniones.
- La configuración por capas.
- El empaquetado: la especificación de Agent Skills y la versión.

Para evaluar al **modelo** con las transcripciones reales de los casos, ver [tests/EVALUATION.md](tests/EVALUATION.md).

| # | Caso | Qué verifica |
|---|---|---|
| 01 | Un proyecto, tareas explícitas | Responsables y tareas completas |
| 02 | Varios proyectos | Separación por proyecto, acción externa, contradicción no bloqueante |
| 03 | Modificación al final | La corrección tardía prevalece |
| 04 | Cancelar y sustituir | El ejemplo obligatorio de las tareas 1–4 |
| 05 | Cambio de responsable | Reasignación trazada |
| 06 | Menciones similares | Dos "validar" con objetivos distintos |
| 07 | Sin responsable | No se inventa el owner y se pregunta |
| 08 | Compromisos frente a posibilidades | Las ideas no se suben |
| 09 | Referencias ambiguas y errores de voz | Alias corregido; "lo otro" queda pendiente |
| 10 | Segunda reunión | Diferida, completada y nueva; la tarea no mencionada se conserva |
| 11 | Ya existe en Boards | Sin duplicados; la cancelada sin ID va a revisión |
| 12 | Sin integración | Draft, plan pendiente, nada reportado como sincronizado |

---

## Pendiente de configurar

**Excel y uploader Python del equipo.**

La versión del programa que hay en este equipo (`tareas-sprint-azure-boards`, plantilla 2.0) no es la que se usa en producción: tiene otro menú y no incluye los catálogos de caso de uso, épica, feature y story. Para habilitar el flujo automático:

1. `refresh_metadata` (opción 3 del programa real).
2. Llenar el Excel desde los catálogos.
3. `simulate` (opción 2).
4. Revisión y confirmación.
5. `publish` (opción 1).

Hace falta la versión real del programa:

- la ruta del script y del Excel;
- las opciones del menú o sus *flags* de línea de comandos;
- las hojas, columnas y catálogos del Excel;
- el formato de salida de la simulación.

El contrato ya está preparado: `export` genera las tareas con caso de uso, épica, feature, story, esfuerzo y sprint como pistas de texto; `config.uploader` recibirá el perfil; y el agente ya describe el flujo por nombre de acción.

**Azure DevOps MCP.**

- Requiere la política de MCP en Copilot y que la organización de Azure DevOps esté respaldada por Entra.
- Sin eso, la deduplicación contra Boards se hace con un snapshot exportado o queda pendiente.

---

## Limitaciones conocidas

- **La calidad de la interpretación depende del modelo.** La CLI garantiza la estructura y la coherencia, pero no puede verificar que una cita sea fiel. `check-expectations` y los casos de prueba sirven para medirla.
- **La deduplicación es por similitud de título.** Los títulos muy distintos para el mismo trabajo no se detectan; por eso todo lo dudoso va a revisión.
- **Ledgers:** se guardan por proyecto en archivos JSON. Si varias personas procesan reuniones del mismo proyecto en paralelo, conviene versionar `documentacion/` en git.
- **Tipos y estados de Boards:** dependen de tu proceso. Configura `work_item_types` y `state_mapping`; mientras falten, las operaciones afectadas quedan en revisión.
- **Prompts de usuario:** la instalación por usuario no instala el prompt `/procesar-reunion`, porque VS Code guarda esos prompts en el perfil. Invoca el agente directamente.
