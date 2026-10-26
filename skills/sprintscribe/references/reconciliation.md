# Motor de reconstrucción y corrección de decisiones

## Contenido

1. Principio
2. Algoritmo
3. Ejemplo de referencia: tareas 1–4
4. Reglas de reconciliación
5. Referencias indirectas
6. Nueva tarea, modificación, división, combinación o sustitución
7. Reconciliación entre reuniones
8. Contradicciones

## 1. Principio

El resultado no es una lista de frases: es el **estado final** de cada tarea y de cada acuerdo al terminar la conversación (y, si hay ledger, al terminar la secuencia de reuniones), más el **rastro** de cómo se llegó a él.

Las correcciones pueden aparecer muchos minutos después de la instrucción original. Por eso se lee todo antes de decidir nada.

## 2. Algoritmo

1. **Primera pasada: inventario.** Recorre la transcripción y anota cada mención de trabajo con su marca de tiempo, quién habla, qué se pide, a quién y con qué certeza. Todavía no son tareas.
2. **Agrupar menciones de un mismo trabajo:**
   - mismo objetivo y mismo entregable → misma tarea, aunque cambie la redacción;
   - objetivos diferentes → tareas diferentes, aunque compartan verbo ("validar") o tema.
3. **Ordenar cronológicamente** las menciones de cada tarea y aplicar las transiciones: proponer, confirmar, modificar, reasignar, cancelar, sustituir, diferir, bloquear, completar.
4. **Estado final.** El último cambio explícito que se refiere claramente a esa tarea determina el estado y el contenido vigente: título, descripción, responsable y criterio de aceptación.
5. **Rastro:**
   - cada transición relevante → una entrada en `reconciliation_log`, con `from`, `to`, `reason` y `cause_decision`;
   - el cambio también va en `tasks[].history`;
   - las decisiones que lo motivan → `decisions`, con `kind: "change"` cuando cambian algo anterior.
6. **Verificación cruzada:**
   - ninguna tarea `cancelled` aparece en la hoja de ruta, en los entregables del objetivo ni como dependencia de una tarea activa;
   - toda tarea que sigue vigente está presente.

## 3. Ejemplo de referencia: tareas 1–4

> Brian: "Necesitamos que Ana desarrolle la tarea 1, que Carlos haga la tarea 2 y que Ana también se encargue de la tarea 3."
> *(minutos después, tras discutir un problema)*
> Brian: "Carlos, la tarea 2 ya no la vamos a hacer. En su lugar necesitamos una tarea 4 para resolver el problema que acabamos de comentar."

| Tarea | Estado final | Responsable | Relaciones |
|---|---|---|---|
| T1 | `confirmed` | Ana (`explicit`) | — |
| T2 | `cancelled` | Carlos | `superseded_by: T4` |
| T3 | `confirmed` | Ana (`explicit`) | — |
| T4 | `confirmed` | Carlos (`inferred`: la instrucción se dirige a él) | `supersedes: [T2]` |

**Registros obligatorios:**

- `reconciliation_log`:
  - `superseded` para T2, con `from: confirmed`, `to: cancelled` y el motivo;
  - `added` para T4, con la misma decisión causante.
- `decisions`: una decisión `change` con `task_refs: [T2, T4]`.
- **Descripción de T4:** el problema discutido, reconstruido desde la parte anterior de la conversación ("el problema que acabamos de comentar"), más la mención de que sustituye a T2.
- **Si T2 ya existe en Boards** con un ID verificado: `ops-plan` propone `change_state` al estado configurado para `cancelled`. **Nunca** se elimina. Si el ID no está verificado, la operación queda en `needs_review`.

T1 y T3 no se tocan: una decisión nueva no sobrescribe acuerdos no relacionados.

El ejemplo concreto está en `assets/examples/`.

## 4. Reglas de reconciliación

- **Prevalece lo posterior y explícito** cuando se refiere claramente a la misma tarea o decisión.
- **Una pregunta o una posibilidad no es un compromiso.** "¿Y si lo hacemos semanal?" no modifica nada hasta que alguien lo confirma.
- **No confundas dos tareas similares** si sus objetivos son diferentes. Ejemplo: "validar la calidad de los datos" (reglas técnicas) frente a "validar el reporte con negocio" (aprobación funcional).
- **No elimines tareas descartadas del registro**: quedan con estado `cancelled`.
- **Conserva la trazabilidad** entre la decisión original y su versión final: evidencia de ambas, `history` y `reconciliation_log`.
- **Ante dos instrucciones contradictorias sin resolución**, registra una `contradiction` y deja la tarea en `needs_clarification`. Excepción: si la contradicción no impide ejecutarla, por ejemplo una fecha distinta para un trabajo que igual se hace ya, marca `"blocking": false`. No elijas un ganador por tu cuenta.
- **Una tarea `modified` contiene ya el contenido vigente.** La versión anterior queda en `history` y en `reconciliation_log`, no en el título.

## 5. Referencias indirectas

Resuelve "eso", "lo anterior", "lo que dijo Sofi", "la persona que lo lleva", "cambiemos lo que habíamos dicho" o "lo de la API" así:

1. Busca hacia atrás el último referente compatible en tema y en interlocutor.
2. Si hay un único candidato razonable, resuélvelo y cita ambas partes en `evidence`.
3. Si hay varios candidatos o ninguno, no adivines: crea la tarea o la decisión en `needs_clarification` con una `open_question` que nombre los candidatos.

"La persona que lo lleva" solo se resuelve si el responsable de ese trabajo consta en la reunión, en el ledger o en Boards.

## 6. Nueva tarea, modificación, división, combinación o sustitución

| Situación | Señal | Registro |
|---|---|---|
| Nueva | Trabajo no mencionado antes | Tarea nueva y `added` |
| Modificación | Mismo objetivo, cambia el cómo, el cuándo o el alcance ("que sea cada hora") | Misma tarea `modified` y `modified` |
| Reasignación | Mismo trabajo, otra persona | Misma tarea, `owner` nuevo y `reassigned` |
| División | Un trabajo pasa a ser dos o más entregables | La original se cancela (`cancelled`) y las nuevas llevan `split_from`; o bien la original se mantiene y la nueva lleva `split_from`, si una parte sigue igual |
| Combinación | Dos trabajos pasan a ser uno | Las absorbidas llevan `merged_into` y estado `cancelled`; la resultante sigue vigente |
| Sustitución | "En lugar de X, hagamos Y" | X `cancelled` con `superseded_by: Y`; Y con `supersedes: [X]`; entradas `superseded` y `added` |
| Diferimiento | "Pasa al siguiente sprint" | `deferred` y `deferred` |
| Finalización | "Ya quedó", con evidencia | `completed` y `completed` |

## 7. Reconciliación entre reuniones

Con un ledger previo (lo muestra `context`):

1. **Reutiliza el ID** cuando la reunión habla de una tarea existente. Busca por título, objetivo, responsable y work item.
2. **Aplica las transiciones** sobre su último estado conocido y regístralas: `history` con `meeting_id`, y `reconciliation_log`.
3. **Incluye en el estado nuevo solo las tareas que la reunión menciona o afecta.** `merge` conserva las demás sin cambios en el ledger.
4. **Ante una tarea del ledger con un título parecido pero un objetivo distinto**, crea una tarea nueva con otro ID; no reutilices el ID.
5. `meeting.previous_meetings` lista las reuniones del ledger que tomaste en cuenta.

## 8. Contradicciones

Usa `contradictions[]` cuando dos afirmaciones incompatibles sobre lo mismo no tienen resolución en la conversación. Cada contradicción lleva:

- un `text` claro;
- las `statements` con su evidencia (al menos dos);
- las `task_refs` afectadas;
- `resolution: null` y `blocking` (`true` por defecto).

Si se resolvió más adelante, no es una contradicción: es una modificación.
