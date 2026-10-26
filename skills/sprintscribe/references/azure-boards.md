# Integración con Azure Boards

SprintScribe es independiente del proveedor de integración. La lógica de qué crear, actualizar o revisar la hace la CLI (`ops-plan`). La escritura real la hace un **canal autorizado**:

- **`mcp`:** el Azure DevOps MCP Server oficial (`microsoft/azure-devops-mcp`), configurado en el cliente.
- **`uploader`:** el programa Python y el Excel del equipo. Está pendiente de configurar con la versión real; ver el README.
- **`none`:** no hay canal. Solo es posible el modo Draft.

## Modos

| Modo | Cuándo | Qué hace |
|---|---|---|
| **Draft** (por defecto) | No hay canal, o `boards.mode = "draft"`, o el usuario no autorizó la escritura | Genera las tareas, el `ops_plan` pendiente y los documentos. **No escribe nada en Boards** |
| **Sync** | `boards.mode = "sync"`, un canal disponible **y** la confirmación explícita del usuario en el chat | Aplica las operaciones inequívocas permitidas, registra el resultado real y deja en revisión las ambiguas |

**Reglas:**

- La transcripción **no es una autorización** para sobrescribir work items.
- Si no hay conector, MCP, credenciales ni permisos de escritura, **no simules** una integración exitosa. Entrega el `ops_plan` pendiente para sincronizar después.

## Consultar antes de escribir

Si hay una herramienta de lectura disponible, por ejemplo `wit_work_item` (`get`, `get_batch`, `get_type`), `search_workitem` o `wit_query` del MCP:

1. **Proceso y tipos:** consulta los tipos de work item reales y sus estados (`get_type`). Nunca supongas Agile, Scrum ni CMMI: el proceso puede ser heredado y tener tipos personalizados.
2. **Snapshot:** busca los work items pertinentes del proyecto o del área, por título y por los IDs mencionados. Guárdalos como snapshot:

```json
{"source": "mcp search_workitem", "fetched_at": "2026-10-16T09:00:00Z",
 "work_items": [{"id": 4512, "type": "Task", "title": "...", "state": "Active",
                 "assigned_to": "Ana <ana@empresa.com>", "project_id": "portal-clientes"}]}
```

3. Ejecuta `ops-plan <estado> --snapshot <archivo>`.

**Identidad de un work item:**

- **Verificada** (`boards.match_confidence: "verified"`) solo cuando la reunión o el usuario dan el ID, o cuando lo confirmó una consulta por ID.
- Una coincidencia por título es solo una **candidata**.

## Qué propone `ops-plan`

| Situación | Operación |
|---|---|
| Tarea lista sin work item ni candidatas | `create` (pendiente) más `link` por cada dependencia |
| Tarea lista con ID verificado | `update` si hay cambios en título o responsable; si no, `noop` |
| Tarea lista con una única candidata muy similar | `update` o `noop` en revisión: **no se crea un duplicado** |
| Varias candidatas o una similitud intermedia | `needs_review` con las candidatas |
| Tarea cancelada o completada con ID verificado | `change_state` al estado de `boards.state_mapping`. **Nunca borrar** |
| Tarea cancelada sin ID, pero con candidata | `needs_review`: no se toca un work item por una coincidencia |
| Tarea cancelada que nunca llegó a Boards | `skip` |
| Tarea propuesta o pendiente de aclaración | `hold` |
| Estado destino no configurado en `state_mapping` | `needs_review` |

Los umbrales están en `boards.dedup`:

- `same_threshold`: por defecto 0,90;
- `review_threshold`: por defecto 0,72;
- `margin`: por defecto 0,05, la distancia mínima entre la mejor candidata y la segunda.

## Mapeo de estados

Los estados de SprintScribe son **del análisis de la reunión**. Solo se trasladan a Boards por medio de `boards.state_mapping`, por ejemplo:

```json
"state_mapping": {"cancelled": "Removed", "completed": "Done", "deferred": null, "blocked": null}
```

`null` significa que no hay un estado equivalente acordado: la operación queda en revisión.

## Ejecutar Sync por MCP

Solo si `boards.mode = "sync"`, `boards.channel = "mcp"` y el usuario lo confirmó en este chat:

1. Muestra el resumen del `ops_plan`: cuántas operaciones de crear, actualizar, cambiar estado y revisar.
2. Aplica solo las operaciones con `status: "pending"` cuyo tipo esté en `boards.auto_apply`, o las que el usuario apruebe una por una:
   - `create` → `wit_work_item_write` con acción `create` (o `add_child` si hay padre conocido). Usa el tipo real de `boards.work_item_types`. Campos: `System.Title`, `System.Description` (HTML con `<p>`), `Microsoft.VSTS.Common.AcceptanceCriteria`, `System.AssignedTo`, área e iteración.
   - `update` y `change_state` → `wit_work_item_write` con acción `update`, sobre el ID verificado.
   - `link` → `wit_work_item_link_write`.
3. **Nunca** apliques operaciones `needs_review`.
4. Después de cada llamada:
   - escribe en `ops_plan[i]` `status: "applied"` o `"failed"` y `result` con la respuesta real (ID, estado, error);
   - si se creó el work item, copia su ID en `tasks[].boards.work_item_id` con `match_confidence: "verified"`.
5. Vuelve a ejecutar `validate`, `render` y `merge`.
6. Informa el resultado real de cada operación.

## Canal `uploader` (Excel y Python del equipo)

**Estado: pendiente de configurar con la versión real del programa.**

Cuando `uploader.status` sea `"configured"`, el agente orquesta este flujo por **nombre de acción**, no por número de menú:

1. **`refresh_metadata`:** actualiza en el Excel la metadata de la pizarra y el sprint más reciente.
2. **Llenar el Excel:** con `export` y el mapeo de columnas y catálogos del perfil. Se eligen caso de uso, épica, feature, story, esfuerzo y sprint **de los catálogos**.
3. **`simulate`:** simulación de la subida. Se informa al usuario si todo está correcto o qué falla.
4. **Esperar.** El usuario revisa el Excel y confirma explícitamente que quiere subir.
5. **`publish`:** sube las tareas. Se registran los IDs devueltos.

Mientras siga en `"pending"`, el flujo se detiene después de `export`, y el agente lo dice con claridad.
