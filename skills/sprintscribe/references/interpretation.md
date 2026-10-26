# Interpretación de la conversación

## Contenido

1. Identificar a los participantes
2. El rol del PO
3. Quién propone, quién decide y quién ejecuta
4. Clasificar cada afirmación
5. Hechos e inferencias
6. Transcripciones automáticas

## 1. Identificar a los participantes

Usa, en este orden:

1. **Etiquetas de hablante** de la transcripción ("Brian:", "Hablante 2:").
2. **El roster de la configuración:** nombres, alias y roles.
3. **Pistas internas de la conversación:**
   - alguien nombra a otro ("Dale Sofi");
   - alguien se presenta ("como PO les cuento");
   - un rol se deduce de lo que la persona hace.

Registra a cada participante en `meeting.participants` con `identity_confidence`:

- `high`: la etiqueta es el nombre o coincide sin ambigüedad con el roster.
- `medium`: se deduce del contexto, con una pista directa.
- `low`: no hay base suficiente.

Mantén la etiqueta original, por ejemplo "Hablante 3".

**Si la confianza es `low`, no atribuyas palabras, decisiones ni responsabilidades a esa persona como hechos.** Registra la evidencia con la etiqueta original y, si afecta al trabajo, agrega una pregunta abierta.

## 2. El rol del PO

El PO está definido en `po` de la configuración; por defecto es Brian. Normalmente:

- explica los proyectos y define necesidades;
- aclara prioridades;
- comunica decisiones.

Pero:

- **No todo lo que dice el PO es una decisión definitiva.** Distingue cuando piensa en voz alta ("tal vez…", "habría que ver…") de cuando instruye ("necesito que…", "esto va sí o sí").
- **No todo el trabajo es del PO.** Que el PO explique una tarea no lo convierte en su responsable.
- Una decisión del PO puede quedar condicionada: "primero quiero los costos". En ese caso es `pending` y va a `po_validation`.

## 3. Quién propone, quién decide y quién ejecuta

Son tres campos distintos en cada tarea y decisión:

| Campo | Pregunta | Ejemplo |
|---|---|---|
| `proposed_by` | ¿Quién planteó la idea? | Ana: "¿y si mandamos la factura por WhatsApp?" |
| `decided_by` | ¿Quién la confirmó o la descartó? | Brian: "eso lo vemos otro día" |
| `owner` | ¿Quién ejecutará el trabajo? | "Carlos, agrega el captcha" → Carlos |

**Cómo identificar al responsable (`owner`):**

- **`explicit`:** alguien recibe la tarea por nombre ("Ana, necesito que…") o la acepta ("yo lo agarro").
- **`inferred`:** la instrucción se dirige a una persona y el contexto la vincula claramente. Ejemplo: "Carlos, la migración ya no va; en su lugar necesitamos X" → Carlos, inferido.
- **`null` con certeza `pending`:** nadie la tomó ("veamos después quién lo toma"). No la asignes a quien habló ni a quien "suele" hacer ese trabajo.

Una tarea tiene **un solo responsable**: Azure Boards acepta una única identidad en Assigned To. Si se nombran varias personas:

- asigna al ejecutor principal y menciona a los demás en la descripción; o
- divide la tarea si los entregables son distintos.

## 4. Clasificar cada afirmación

| Clase | Señales típicas | Cómo se registra |
|---|---|---|
| Compromiso | "me comprometo", "lo dejo listo el viernes", "va", "yo lo hago" | Tarea `confirmed` y decisión `commitment` |
| Acuerdo o decisión | instrucción del PO, consenso explícito, "queda así" | Tarea `confirmed` y decisión `decision` |
| Propuesta | "podríamos", "propongo", "¿y si…?" | Tarea `proposed` (certeza `pending`), o nada si es trivial |
| Duda | preguntas sin respuesta | `open_questions`, solo si bloquea trabajo |
| Exploración | "tal vez", "habría que ver", "lo vemos otro día" | Tarea `proposed` o decisión `po_validation` pendiente |
| Descarte | "ya no va", "olvídalo", "eso no" | Tarea `cancelled` más una entrada en `reconciliation_log` |
| Información | contexto, estado actual | Se usa en descripciones; no genera elementos |

Una tarea `confirmed` necesita al menos una evidencia de compromiso o de decisión. La mera mención de un trabajo no basta.

## 5. Hechos e inferencias

Usa siempre el campo `certainty`:

- `explicit`: alguien lo dijo y se puede citar.
- `inferred`: se deduce del contexto, con respaldo concreto. Ejemplo: el objetivo del sprint construido a partir de las tareas confirmadas.
- `recommended`: es una propuesta tuya, por ejemplo un paso de la hoja de ruta que nadie acordó.
- `pending`: falta confirmación.

**Jerarquía de evidencia:**

1. Un acuerdo explícito pesa más que una interpretación semántica.
2. El contexto completo pesa más que una frase aislada.
3. La documentación vigente y los work items verificados sirven para resolver nombres, referencias y responsables.
4. La ausencia de información no es evidencia de una decisión.

## 6. Transcripciones automáticas

Los errores de reconocimiento de voz son normales: "data leik" por "Data Lake", "Brayan" por "Brian", "po" por "PO".

- Corrígelos cuando un alias de la configuración o el contexto lo respalde, y deja constancia en `resolution_basis` o en la descripción.
- No corrijas nombres propios desconocidos inventando uno; deja el término original.
- Ignora muletillas y repeticiones, pero no ignores una corrección que venga en medio de ellas.
